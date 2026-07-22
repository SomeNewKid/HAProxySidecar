# HAProxySidecar

HAProxySidecar is a Python command-line project for running an OpenAI Agents SDK
workload inside a hardened, disposable Docker sandbox with supporting sidecar
containers.

The current focus is an HAProxy sidecar that lets the MCP sidecar reach a
MariaDB database running on the Windows host, while keeping database connection
details out of the AI agent container.

The default topology combines:

- a sandboxed AI agent container
- a Squid proxy sidecar for controlled network egress
- an MCP server sidecar that exposes only declared tools/resources
- an HAProxy sidecar that proxies MariaDB TCP traffic to the host
- optional sidecars such as Jina Reader, code execution, and Ollama for other
  workloads
- a Docker internal network that lets containers communicate without exposing
  sidecars directly to the host

> [!WARNING]
> This is an experimental sandboxing and sidecar orchestration project. It is a
> learning and hardening exercise, not a finished security model.

## Current Workload

The sample workload demonstrates a hosted GPT model, MCP tool exposure, HAProxy,
and a host MariaDB database working together.

On each run, the sandbox agent:

1. Calls the MCP sidecar tool `get_active_items`.
2. The MCP sidecar connects to MariaDB through `haproxy-sidecar:3306`.
3. HAProxy proxies that TCP connection to `host.docker.internal:3306`.
4. The MCP tool queries `agent_allowed.items` for records where
   `status = 'active'`.
5. The GPT-backed agent generates a simple HTML document listing those active
   items.
6. The agent saves the document as `/sandbox-output/site/index.html`.
7. The agent saves and prints a short status message in
   `/sandbox-output/answer.txt`.

The agent uses the OpenAI Agents SDK with the default model configured in
`src/sandbox_agent/openai_agent.py`:

```text
gpt-4.1-mini
```

The model is expected to make its own tool calls. The earlier local Ollama
workaround, where Python pre-called tools and only asked the model to write
HTML, is no longer the default path.

## Run

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m sandbox_agent
```

The host-side command:

1. Loads `src/sandbox_agent/sandbox_spec.toml`.
2. Validates the requested capabilities and sidecar configuration.
3. Builds or reuses a hash-tagged Docker image for the agent container.
4. Builds or refreshes the MCP sidecar image when `mcp_client` is enabled.
5. Creates a per-run Docker internal network.
6. Starts Squid when `network` is declared.
7. Starts the code sidecar and Jina Reader sidecar when their capabilities are
   declared.
8. Starts HAProxy when `haproxy` is declared.
9. Starts the MCP sidecar and exposes only declared MCP tools/resources.
10. Runs the disposable agent container.
11. Persists run artifacts and removes disposable containers/network.

Run artifacts are written under:

```text
.docker_sandbox/runs/run-YYYY-mm-dd-HH-MM-SS/
```

## Sandbox Spec

The sandbox is driven by a declarative TOML file:

```toml
schema_version = 1
capabilities = [
  "network",
  "mcp_client",
  "openai_agents",
  "haproxy",
]

[squid_proxy]
allowed_domains = []
allowed_ip_addresses = []

[haproxy]
backend_host = "host.docker.internal"
ports = [
  3306,
]

[mcp_sidecar]
tools = [
  "get_html_element_name",
  "get_active_items",
]
resources = []
```

The design rule is that the sandbox starts minimal, and every softened boundary
must be declared. Unknown top-level keys, unknown table keys, and unsupported
capability values fail closed.

### HAProxy Spec

Declaring `"haproxy"` requires:

```toml
[haproxy]
backend_host = "host.docker.internal"
ports = [
  3306,
]
```

Rules:

- `haproxy` requires the `network` capability.
- `[haproxy]` is required when the `haproxy` capability is declared.
- `[haproxy]` is rejected unless the `haproxy` capability is declared.
- `backend_host` is optional and defaults to `host.docker.internal`.
- `ports` must be a non-empty list of unique TCP ports.
- HAProxy listens on each declared port and proxies to the same backend port.
- No HAProxy ports are published to the host.

The default HAProxy sidecar maps:

```text
haproxy-sidecar:3306 -> host.docker.internal:3306
```

The sidecar starts on Docker's `bridge` network so it can reach
`host.docker.internal`, then joins the sandbox internal network with alias
`haproxy-sidecar` so the MCP sidecar can reach it. This is necessary because the
sandbox network is created with `docker network create --internal`.

## Runtime Environment

The default workload needs these host environment variables:

```text
OPENAI_API_KEY=<OpenAI API key>
SANDBOX_TESTER_MARIADB_CREDENTIALS=<username,password>
```

`SANDBOX_TESTER_MARIADB_CREDENTIALS` is passed only to the MCP sidecar when
HAProxy is enabled. It must use a comma-separated value:

```text
sandbox_tester,password_goes_here
```

When HAProxy is enabled, the MCP sidecar receives:

```text
MARIADB_HOST=haproxy-sidecar
MARIADB_PORT=3306
MARIADB_DATABASE=agent_allowed
SANDBOX_TESTER_MARIADB_CREDENTIALS=<from host environment>
```

The AI agent container does not receive `MARIADB_HOST`, `MARIADB_PORT`,
`MARIADB_DATABASE`, or `SANDBOX_TESTER_MARIADB_CREDENTIALS`.

## Capabilities

Supported capabilities include:

- `network`: enables the Squid egress gateway and Docker internal networking.
- `mcp_client`: installs the Python MCP client package in the agent image and
  requires `network`.
- `openai`: installs the OpenAI Python SDK for direct client workloads.
- `openai_agents`: installs the OpenAI Agents SDK and requires `network`.
- `haproxy`: starts the HAProxy TCP proxy sidecar and requires `network`.
- `code_execution`: starts the code-execution sidecar for constrained Python
  script execution.
- `jina_reader`: starts the Jina Reader sidecar for readable page/document
  fetching.
- `ollama`: starts the Ollama sidecar and requires `network`; this capability
  remains in the codebase for future local-model options but is not part of the
  default spec.

Provider-backed capabilities can add provider domains and host environment
variables. With the default GPT-backed workload, the agent uses the hosted
OpenAI API and therefore needs `OPENAI_API_KEY`.

## Sidecars

### HAProxy

The HAProxy sidecar uses:

```text
haproxy:latest
```

For each run, the harness generates a run-local `haproxy.cfg` and mounts it
read-only at:

```text
/usr/local/etc/haproxy/haproxy.cfg
```

For the default spec, the generated config listens on container port `3306` and
forwards TCP traffic to `host.docker.internal:3306`.

HAProxy is intentionally not published to the host. In the current design,
reachability is restricted by:

- only giving the MCP sidecar the MariaDB environment variables
- not giving database environment variables to the AI agent container
- exposing database access only through declared MCP tools
- not publishing HAProxy ports

Later hardening could add source ACLs, iptables, separate Docker networks, or
more granular network segmentation.

### MCP Sidecar

When launched by the Docker harness, the MCP sidecar runs on the internal
network with alias `mcp-sidecar`, and the agent receives:

```text
MCP_SIDECAR_URL=http://mcp-sidecar:8000/mcp
```

The MCP sidecar reads an exposure file generated from `[mcp_sidecar]`. With no
declared tools or resources, it exposes nothing. Unknown exposure names fail
closed at server startup.

Implemented MCP tools include:

- `get_html_element_name`
- `get_active_items`
- `microsoft_docs_search`
- `microsoft_docs_fetch`
- `microsoft_code_sample_search`
- `jina_read_url`
- `run_python_script`

`get_active_items` connects to MariaDB using `pymysql` and runs:

```sql
SELECT id, item_key, title, status, notes, quantity, created_at, updated_at
FROM items
WHERE status = 'active'
ORDER BY id
```

The tool returns JSON text. Tool calls are audited in
`mcp-sidecar-tool-calls.jsonl`; credential values are not written to the audit
record.

Implemented MCP resources include:

- `answer_format`, exposed as
  `mcp-sidecar://instructions/answer-format.md`

### Squid Proxy

The Squid sidecar runs with network alias `egress-gateway` and listens on port
`3128`. Containers that need outbound network access receive:

```text
HTTP_PROXY=http://egress-gateway:3128
HTTPS_PROXY=http://egress-gateway:3128
```

`[squid_proxy]` controls the egress allowlist.

### Code Execution

The optional `code_execution` capability starts a local code-execution sidecar
with alias `code-sidecar`. The AI agent does not call it directly; instead,
`[mcp_sidecar].tools` must expose `run_python_script`, and the MCP sidecar
forwards script requests to:

```text
CODE_SIDECAR_URL=http://code-sidecar:8090
```

### Jina Reader

The optional `jina_reader` capability starts `ghcr.io/jina-ai/reader:oss` with
alias `jina-reader`. The MCP sidecar receives:

```text
JINA_READER_URL=http://jina-reader:8081
```

### Ollama

Ollama support remains available as an optional capability for future local
model experiments, but it is not used by the default HAProxy/MariaDB workload.

Declaring `"ollama"` requires:

```toml
[ollama_sidecar]
models = [
  "model-name:tag",
]
```

The Ollama image hash is separate from the agent image hash. Changing only the
normalized Ollama model list changes only the Ollama sidecar image name. Merely
reordering the same model list does not trigger a different Ollama image name.

Models are pulled during the Ollama image build, not at container runtime.

## Run Artifacts

A successful default run contains files similar to:

```text
.docker_sandbox/runs/run-YYYY-mm-dd-HH-MM-SS/
  Dockerfile
  answer.txt
  config.json
  gateway-logs.json
  gateway-start-results.json
  haproxy.cfg
  haproxy-sidecar-logs.json
  haproxy-sidecar-metadata.json
  haproxy-sidecar-start-results.json
  haproxy-sidecar-stderr.txt
  haproxy-sidecar-stdout.txt
  landlock-policy.json
  mcp-sidecar-exposure.json
  mcp-sidecar-logs.json
  mcp-sidecar-metadata.json
  mcp-sidecar-start-results.json
  mcp-sidecar-stderr.txt
  mcp-sidecar-stdout.txt
  mcp-sidecar-tool-calls.jsonl
  resolved-profile.json
  run-metadata.json
  sandbox-spec.json
  seccomp-profile.json
  site/index.html
  squid.conf
  stderr.txt
  stdout.txt
```

`answer.txt` contains the final status message saved by the agent. `stdout.txt`
contains the same message printed by the in-container process. `site/index.html`
contains the generated HTML document.

`mcp-sidecar-tool-calls.jsonl` is the MCP audit log. For the default workload,
it should include a successful `get_active_items` call returning the active
MariaDB items as JSON.

## Sandbox Probes

The copied SandboxTester probe suite can be run against the generated sandbox:

```powershell
.\.venv\Scripts\python.exe -m sandbox_agent --test-sandbox
```

To serialize probe evidence for troubleshooting:

```powershell
.\.venv\Scripts\python.exe -m sandbox_agent --test-sandbox --serialize-evidence
```

## Requirements

- Python 3.11.
- PowerShell on Windows.
- Docker Desktop with Linux containers enabled.
- MariaDB running on the host and reachable from Docker as
  `host.docker.internal:3306`.
- A database named `agent_allowed` with an `items` table compatible with the
  default `get_active_items` query.
- A MariaDB user whose credentials are available in
  `SANDBOX_TESTER_MARIADB_CREDENTIALS`.
- `OPENAI_API_KEY` for the default GPT-backed workload.
- Network access during image builds to download Python packages and Docker base
  images.

Docker image builds can take several minutes the first time an image is created.
The MCP sidecar image is refreshed during startup so dependency changes such as
`pymysql` are picked up.

## Setup

Create the virtual environment and install development dependencies:

```powershell
.\scripts\setup-dev.ps1
```

The setup script expects Python 3.11 at the path configured in
`scripts\setup-dev.ps1`.

## Development Checks

Run formatting, linting, type checking, and tests:

```powershell
.\scripts\check.ps1
```

This runs:

- `ruff format .`
- `ruff check .`
- `pyright`
- `pytest`

## Architecture

The project has five main packages:

- `sandbox_agent`: the in-container workload. It owns the OpenAI Agents SDK
  prompt, MCP client calls, HTML document generation, and artifact saving.
- `mcp_sidecar`: the MCP server container workload. It owns local MCP resources,
  local MCP tools, Microsoft Learn proxy tools, MariaDB access, Jina Reader
  client logic, code-execution client logic, streamable HTTP server setup, and
  sidecar audit logging.
- `code_sidecar`: the optional no-network code-execution sidecar.
- `docker_sandbox`: the host/container harness. It owns sandbox spec loading,
  Dockerfile generation, image creation, Docker local network creation, Squid
  setup, sidecar startup, readiness checks, disposable agent container
  execution, artifact persistence, and teardown.
- `sandbox_tester`: the copied probe suite used by `--test-sandbox`.

The command path deliberately differs by location:

- On the host, `python -m sandbox_agent` delegates to `docker_sandbox`.
- Inside the container, `python -m sandbox_agent` runs the workload.

The in-container path is guarded by `SANDBOX_AGENT_CONTAINER=1` and expected
mounts such as `/sandbox-output`, `/sandbox-work`, and `/sandbox-source/src`.

The default Docker topology is:

```text
Docker host
  docker_sandbox host runner
    |
    +-- Docker bridge network
    |     |
    |     +-- haproxy-sidecar-* container
    |           backend: host.docker.internal:3306
    |
    +-- Docker internal sandbox network
          |
          +-- sandbox-agent-* container
          |     MCP_SIDECAR_URL=http://mcp-sidecar:8000/mcp
          |
          +-- mcp-sidecar-* container
          |     network alias: mcp-sidecar
          |     MARIADB_HOST=haproxy-sidecar
          |
          +-- haproxy-sidecar-* container
          |     network alias: haproxy-sidecar
          |
          +-- squid proxy container
                network alias: egress-gateway
```

Optional runs may also include `code-sidecar-*`, `jina-reader-*`, and
`ollama-sidecar-*` containers when their capabilities are declared.

## Project Structure

```text
ARCHITECTURE.png               Static Docker topology infographic

src/sandbox_agent/
  __main__.py                  Package entry point for python -m sandbox_agent
  cli.py                       Host delegation and in-container workload entry point
  openai_agent.py              OpenAI Agents SDK workload
  openai_tools.py              OpenAI Agents SDK tool adapters
  sandbox_spec.toml            Declarative sandbox capability spec
  tools.py                     Neutral tools, MCP client calls, and artifact saving

src/mcp_sidecar/
  __main__.py                  Package entry point for python -m mcp_sidecar
  audit.py                     JSONL audit logging for resources and tools
  cli.py                       MCP sidecar command-line entry point
  resources.py                 Local MCP resources
  server.py                    FastMCP server construction and exposure registry
  tools.py                     Local, MariaDB, Microsoft Learn, Jina, and code tools
  dockerfile/Dockerfile        MCP sidecar image definition

src/code_sidecar/
  __main__.py                  Package entry point for python -m code_sidecar
  cli.py                       Code sidecar command-line entry point
  runner.py                    Child-process script validator and runner
  server.py                    Internal HTTP service and result capture
  dockerfile/Dockerfile        Code sidecar image definition

src/docker_sandbox/
  __main__.py                  Package entry point for python -m docker_sandbox
  cli.py                       Docker sandbox command-line orchestration
  container_factory.py         Docker image inspection and build
  container_guard.py           Runtime guard for in-container execution
  landlock_runner.py           Linux Landlock path-policy launcher
  models.py                    Docker orchestration dataclasses
  profiles.py                  Legacy named profile definitions
  run_results.py               Local run artifact persistence
  sandbox_container.py         Containers, network, sidecars, artifacts, teardown
  sandbox_spec.py              Spec validation and profile/Dockerfile generation
  dockerfile/remove_python_packaging.py
  dockerfile/runtime_sitecustomize.py

src/sandbox_tester/
  Probe definitions and report generation used by --test-sandbox

tests/
  Unit and integration-style tests for sandbox specs, sidecars, tools, and
  orchestration helpers

scripts/
  setup-dev.ps1
  check.ps1
```

## Notes

HAProxySidecar is a learning and hardening exercise, not a security proof. The
container policy reduces accidental host exposure and makes required capability
softening visible, but Docker, Landlock, seccomp, Squid, MCP tool boundaries,
sidecar behavior, and Python runtime guards should not be interpreted as a
complete isolation guarantee.

The current "only MCP sidecar can access MariaDB" posture is practical rather
than absolute: the agent is not given database environment variables and the
database tool is only exposed through MCP declarations, but Docker networking is
not yet enforcing per-container ACLs.

Generated content can vary between runs because it is model-generated.

Run artifacts under `.docker_sandbox/runs` are ignored by Git.

## Third-Party Notices

This project uses third-party packages including `mcp`, `openai`,
`openai-agents`, `pillow`, and `pymysql`. It also uses Docker images such as
`python:3.12-slim` for the agent, MCP sidecar, and code sidecar,
`ubuntu/squid:latest` for the Squid gateway, `haproxy:latest` for the HAProxy
sidecar, `ollama/ollama:latest` for optional Ollama runs, and
`ghcr.io/jina-ai/reader:oss` for the optional Jina Reader sidecar. See each
package and image license metadata for details.

## License

GNU General Public License v3.0. See the `LICENSE` file for details.
