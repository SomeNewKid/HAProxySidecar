# OllamaSidecar

OllamaSidecar is a Python command-line project for running an OpenAI Agents SDK
workload inside a hardened, disposable Docker sandbox with optional sidecar
containers. This repository was copied from CodeSidecar and now focuses on one
new capability: an Ollama sidecar that hosts small local models behind an
OpenAI-compatible endpoint.

The current default topology combines:

- a sandboxed AI agent container
- a Squid proxy sidecar for controlled network egress
- an MCP server sidecar that exposes only declared tools/resources
- an Ollama sidecar that serves local models on the internal Docker network
- optional sidecars such as Jina Reader and code execution for other workloads
- a Docker internal network that lets containers communicate without exposing
  sidecars directly to the host

> [!WARNING]
> This is an experimental sandboxing and sidecar orchestration project. It is a
> learning and hardening exercise, not a finished security model.

## Current Workload

The sample workload demonstrates Ollama, MCP, and the OpenAI Agents SDK working
together locally.

On each run, the sandbox agent:

1. Calls the MCP sidecar function `get_html_element_name`, which currently
   returns `<table>`.
2. Uses the OpenAI Agents SDK with `qwen3:0.6b` hosted by the Ollama sidecar.
3. Generates a simple HTML document explaining the returned element.
4. Saves the document as `/sandbox-output/site/index.html`.
5. Saves and prints a short status message in `/sandbox-output/answer.txt`.

The current implementation keeps orchestration deterministic. In testing,
`qwen3:0.6b` handled text generation and simple constrained tool use, but was
not reliable at autonomously sequencing multiple tool calls. The workload
therefore calls MCP directly from Python, uses the local model for generation,
and saves the generated document through the existing local save function.

## Run

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m sandbox_agent
```

The host-side command:

1. Loads `src/sandbox_agent/sandbox_spec.toml`.
2. Validates the requested capabilities and sidecar configuration.
3. Builds or reuses a hash-tagged Docker image for the agent container.
4. Builds or reuses a separate hash-tagged Docker image for the Ollama sidecar.
5. Builds or reuses the MCP sidecar image when `mcp_client` is enabled.
6. Creates a per-run Docker internal network.
7. Starts Squid when `network` is declared.
8. Starts the Ollama sidecar when `ollama` is declared.
9. Waits for Ollama to answer readiness probes and confirm declared models.
10. Starts the MCP sidecar and exposes only declared MCP tools/resources.
11. Runs the disposable agent container.
12. Persists run artifacts and removes disposable containers/network.

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
  "ollama",
]

[squid_proxy]
allowed_domains = []
allowed_ip_addresses = []

[ollama_sidecar]
models = [
  "qwen3:0.6b",
]

[mcp_sidecar]
tools = [
  "get_html_element_name",
]
resources = []
```

The design rule is that the sandbox starts minimal, and every softened boundary
must be declared. Unknown top-level keys, unknown table keys, and unsupported
capability values fail closed.

### Ollama Spec

Declaring `"ollama"` requires:

```toml
[ollama_sidecar]
models = [
  "qwen3:0.6b",
]
```

Rules:

- `[ollama_sidecar].models` must be a non-empty list of non-empty strings.
- Duplicate model names fail validation.
- `[ollama_sidecar]` cannot contain unknown keys.
- Non-empty Ollama sidecar configuration is rejected unless `"ollama"` is in
  `capabilities`.
- Model names are normalized and sorted before hashing.

The Ollama image hash is separate from the agent image hash. Changing only the
normalized Ollama model list changes only the Ollama sidecar image name. Merely
reordering the same model list does not trigger a different Ollama image name.

Models are pulled during the Ollama image build, not at container runtime. This
keeps runs deterministic and makes model changes visible as Docker image
changes.

## Runtime Environment

When the Ollama sidecar is enabled, the agent container receives:

```text
OLLAMA_BASE_URL=http://ollama-sidecar:11434
OLLAMA_MODEL=<first declared model>
OPENAI_BASE_URL=http://ollama-sidecar:11434/v1
OPENAI_API_KEY=ollama
```

`OPENAI_BASE_URL` lets OpenAI-compatible client libraries, including the OpenAI
Agents SDK when configured with `OpenAIChatCompletionsModel`, call the local
Ollama endpoint instead of the OpenAI API.

The Ollama sidecar runs on the internal Docker network with alias:

```text
ollama-sidecar
```

It is not intended to be exposed directly to the host.

## Capabilities

Supported capabilities include:

- `network`: enables the Squid egress gateway and Docker internal networking.
- `mcp_client`: installs the Python MCP client package in the agent image and
  requires `network`.
- `openai`: installs the OpenAI Python SDK for direct client workloads.
- `openai_agents`: installs the OpenAI Agents SDK and requires `network`.
- `ollama`: starts the Ollama sidecar and requires `network`.
- `code_execution`: starts the code-execution sidecar for constrained Python
  script execution.
- `jina_reader`: starts the Jina Reader sidecar for readable page/document
  fetching.

Provider-backed capabilities can add provider domains and host environment
variables. In Ollama mode, the agent receives an explicit local
`OPENAI_BASE_URL` and dummy `OPENAI_API_KEY=ollama`, so the default workload does
not call the OpenAI API.

## Sidecars

### Ollama

The Ollama sidecar image is generated from the declared model list. Its
Dockerfile starts from:

```text
ollama/ollama:latest
```

During image build, it starts `ollama serve`, pulls each declared model, and
then shuts the server down. At runtime, the sidecar starts Ollama with:

```text
OLLAMA_HOST=0.0.0.0:11434
```

The harness waits for:

1. TCP connectivity to port `11434`.
2. `/api/tags` to report every declared model.

Readiness details are persisted as:

```text
ollama-sidecar-readiness-results.json
```

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
- `microsoft_docs_search`
- `microsoft_docs_fetch`
- `microsoft_code_sample_search`
- `jina_read_url`
- `run_python_script`

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

`[squid_proxy]` controls the egress allowlist. The Ollama sidecar is internal
and is included in proxy bypass settings for agent-to-sidecar calls.

### Code Execution

The optional `code_execution` capability starts a local code-execution sidecar
with alias `code-sidecar`. The AI agent does not call it directly; instead,
`[mcp_sidecar].tools` must expose `run_python_script`, and the MCP sidecar
forwards script requests to:

```text
CODE_SIDECAR_URL=http://code-sidecar:8090
```

This sidecar remains available for workloads that need exact computation, but it
is not used by the current default Ollama workload.

### Jina Reader

The optional `jina_reader` capability starts `ghcr.io/jina-ai/reader:oss` with
alias `jina-reader`. The MCP sidecar receives:

```text
JINA_READER_URL=http://jina-reader:8081
```

This sidecar is not used by the current default Ollama workload.

## Run Artifacts

A successful default run contains files similar to:

```text
.docker_sandbox/runs/run-YYYY-mm-dd-HH-MM-SS/
  Dockerfile
  answer.txt
  config.json
  gateway-logs.json
  gateway-start-results.json
  landlock-policy.json
  mcp-sidecar-exposure.json
  mcp-sidecar-logs.json
  mcp-sidecar-metadata.json
  mcp-sidecar-start-results.json
  mcp-sidecar-stderr.txt
  mcp-sidecar-stdout.txt
  mcp-sidecar-tool-calls.jsonl
  ollama-sidecar-logs.json
  ollama-sidecar-metadata.json
  ollama-sidecar-readiness-results.json
  ollama-sidecar-start-results.json
  ollama-sidecar-stderr.txt
  ollama-sidecar-stdout.txt
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
it should include a successful `get_html_element_name` call returning `<table>`.

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
- Network access during image builds to download Python packages, Docker base
  images, and declared Ollama models.
- Enough disk space for Docker images and pulled Ollama model weights.

The default Ollama-backed workload does not require a host `OPENAI_API_KEY`.

Docker image builds can take several minutes the first time an image is created,
especially when a model must be pulled into the Ollama sidecar image.

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
  prompt, local model configuration, MCP client calls, HTML document generation,
  and artifact saving.
- `mcp_sidecar`: the MCP server container workload. It owns local MCP resources,
  local MCP tools, Microsoft Learn proxy tools, Jina Reader client logic,
  code-execution client logic, streamable HTTP server setup, and sidecar audit
  logging.
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
    +-- Docker internal network
          |
          +-- sandbox-agent-* container
          |     OPENAI_BASE_URL=http://ollama-sidecar:11434/v1
          |     OLLAMA_MODEL=qwen3:0.6b
          |     MCP_SIDECAR_URL=http://mcp-sidecar:8000/mcp
          |
          +-- ollama-sidecar-* container
          |     network alias: ollama-sidecar
          |
          +-- mcp-sidecar-* container
          |     network alias: mcp-sidecar
          |
          +-- squid proxy container
                network alias: egress-gateway
```

Optional runs may also include `code-sidecar-*` and `jina-reader-*` containers
when their capabilities are declared.

## Project Structure

```text
ARCHITECTURE.png               Static Docker topology infographic

src/sandbox_agent/
  __main__.py                  Package entry point for python -m sandbox_agent
  cli.py                       Host delegation and in-container workload entry point
  openai_agent.py              Ollama-backed OpenAI Agents SDK workload
  openai_tools.py              OpenAI Agents SDK tool adapters
  sandbox_spec.toml            Declarative sandbox capability spec
  tools.py                     Neutral tools, MCP client calls, and artifact saving

src/mcp_sidecar/
  __main__.py                  Package entry point for python -m mcp_sidecar
  audit.py                     JSONL audit logging for resources and tools
  cli.py                       MCP sidecar command-line entry point
  resources.py                 Local MCP resources
  server.py                    FastMCP server construction and exposure registry
  tools.py                     Local, Microsoft Learn, Jina, and code tools
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

OllamaSidecar is a learning and hardening exercise, not a security proof. The
container policy reduces accidental host exposure and makes required capability
softening visible, but Docker, Landlock, seccomp, Squid, MCP tool boundaries,
sidecar behavior, and Python runtime guards should not be interpreted as a
complete isolation guarantee.

Generated content can vary between runs because it is model-generated. Small
local models such as `qwen3:0.6b` are useful for proving local text generation
through the sidecar, but should not be assumed reliable for complex reasoning or
multi-tool planning.

Run artifacts under `.docker_sandbox/runs` are ignored by Git.

## Third-Party Notices

This project uses third-party packages including `mcp`, `openai`,
`openai-agents`, and `pillow`. It also uses Docker images such as
`python:3.12-slim` for the agent, MCP sidecar, and code sidecar,
`ubuntu/squid:latest` for the Squid gateway, `ollama/ollama:latest` for the
Ollama sidecar, and `ghcr.io/jina-ai/reader:oss` for the optional Jina Reader
sidecar. See each package and image license metadata for details.

## License

GNU General Public License v3.0. See the `LICENSE` file for details.
