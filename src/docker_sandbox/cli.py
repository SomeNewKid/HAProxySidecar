"""Command-line interface for Docker sandbox experiments."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from .container_factory import ensure_base_image
from .models import (
    DockerConfiguration,
    DockerImageResult,
    DockerImageStatus,
    DockerRunResult,
    SandboxRunTarget,
)
from .profiles import SUPPORTED_PROFILE_NAMES, get_docker_profile
from .run_results import save_run_results
from .sandbox_container import run_sandbox_container
from .sandbox_spec import (
    generate_dockerfile,
    load_sandbox_spec,
    resolve_environment_variables,
    resolve_local_environment_variable_names,
    resolve_profile,
)

_DEFAULT_BASE_DIRECTORY = Path(".docker_sandbox")
_DEFAULT_DOCKERFILE = Path("src") / "docker_sandbox" / "dockerfile" / "Dockerfile"
_DEFAULT_SANDBOX_SPEC = Path("src") / "sandbox_agent" / "sandbox_spec.toml"
_DEFAULT_GUEST_USER = "sandbox"


def main(arguments: list[str] | None = None) -> int:
    """Run the Docker sandbox command-line interface."""
    parsed_arguments = _parse_arguments(arguments)
    configuration = _configuration_from_arguments(parsed_arguments)
    image_result = ensure_base_image(configuration)
    _print_image_result(image_result)

    if image_result.status not in {DockerImageStatus.EXISTS, DockerImageStatus.CREATED}:
        return 1

    run_result = run_sandbox_container(
        configuration,
        verbose=parsed_arguments.verbose,
        serialize_evidence=parsed_arguments.serialize_evidence,
    )
    save_run_results(run_result)
    print(f"Run results saved to: {run_result.run_directory}")

    if parsed_arguments.keep_container:
        print(f"Kept disposable Docker container '{run_result.container_name}'.")
    else:
        run_result.remove_container()
        print(f"Removed disposable Docker container '{run_result.container_name}'.")

    return _exit_code_from_run_result(run_result)


def _parse_arguments(arguments: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Sandbox Agent in a Docker sandbox."
    )
    parser.add_argument(
        "--base-directory",
        type=Path,
        default=_DEFAULT_BASE_DIRECTORY,
        help=(
            f"Host directory for Docker sandbox files. Default: "
            f"{_DEFAULT_BASE_DIRECTORY}"
        ),
    )
    parser.add_argument(
        "--dockerfile",
        type=Path,
        default=_DEFAULT_DOCKERFILE,
        help=f"Dockerfile used to build the image. Default: {_DEFAULT_DOCKERFILE}",
    )
    parser.add_argument(
        "--guest-user",
        default=_DEFAULT_GUEST_USER,
        help=(
            "Container user used to run Sandbox Agent. The default image creates "
            f"this user as '{_DEFAULT_GUEST_USER}'."
        ),
    )
    parser.add_argument(
        "--profile",
        choices=SUPPORTED_PROFILE_NAMES,
        default=None,
        help=(
            "Legacy Docker hardening profile to apply instead of the sandbox spec. "
            f"Supported profiles: {', '.join(SUPPORTED_PROFILE_NAMES)}"
        ),
    )
    parser.add_argument(
        "--sandbox-spec",
        type=Path,
        default=_DEFAULT_SANDBOX_SPEC,
        help=f"Declarative sandbox spec. Default: {_DEFAULT_SANDBOX_SPEC}",
    )
    parser.add_argument(
        "--keep-container",
        action="store_true",
        help="Keep the disposable container after execution instead of removing it.",
    )
    parser.add_argument(
        "--test-sandbox",
        action="store_true",
        help="Run the sandbox_tester probe suite instead of Sandbox Agent.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Pass verbose progress output through to Sandbox Agent.",
    )
    parser.add_argument(
        "--serialize-evidence",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(arguments)


def _configuration_from_arguments(
    arguments: argparse.Namespace,
) -> DockerConfiguration:
    repository_root = Path.cwd().resolve()
    base_directory = arguments.base_directory.expanduser().resolve()
    if arguments.profile is not None:
        dockerfile_path = arguments.dockerfile.expanduser()
        if not dockerfile_path.is_absolute():
            dockerfile_path = repository_root / dockerfile_path
        profile = get_docker_profile(arguments.profile)
        return DockerConfiguration(
            base_directory=base_directory,
            dockerfile_path=dockerfile_path.resolve(),
            build_context=repository_root,
            guest_user=arguments.guest_user,
            profile=profile,
        )

    sandbox_spec_path = arguments.sandbox_spec.expanduser()
    if not sandbox_spec_path.is_absolute():
        sandbox_spec_path = repository_root / sandbox_spec_path

    spec = load_sandbox_spec(sandbox_spec_path.resolve())
    profile = resolve_profile(spec)
    run_target = (
        SandboxRunTarget.TESTER if arguments.test_sandbox else SandboxRunTarget.AGENT
    )
    image_tag = spec.image_tag
    if run_target == SandboxRunTarget.TESTER:
        image_tag = f"{image_tag}-test-sandbox"
        profile = replace(
            profile,
            name=f"{profile.name}-test-sandbox",
            image_name=f"sandbox-agent/sandbox-agent:{image_tag}",
        )

    generated_dockerfile = generate_dockerfile(
        spec,
        include_probe_dependencies=run_target == SandboxRunTarget.TESTER,
    )
    dockerfile_path = base_directory / "generated" / image_tag / "Dockerfile"
    dockerfile_path.parent.mkdir(parents=True, exist_ok=True)
    dockerfile_path.write_text(f"{generated_dockerfile.rstrip()}\n", encoding="utf-8")

    return DockerConfiguration(
        base_directory=base_directory,
        dockerfile_path=dockerfile_path.resolve(),
        build_context=repository_root,
        guest_user=arguments.guest_user,
        profile=profile,
        generated_dockerfile=generated_dockerfile,
        resolved_spec=spec.to_dict()
        | {
            "image_name": profile.image_name,
            "ollama_image_name": spec.ollama_image_name,
            "test_sandbox": run_target == SandboxRunTarget.TESTER,
        },
        environment_variables=resolve_environment_variables(spec),
        local_environment_variable_names=resolve_local_environment_variable_names(spec),
        run_target=run_target,
        enabled_capabilities=frozenset(spec.capabilities),
        mcp_sidecar_tools=spec.mcp_sidecar_tools,
        mcp_sidecar_resources=spec.mcp_sidecar_resources,
        haproxy=spec.haproxy,
        ollama_models=spec.ollama_models,
        ollama_image_name=spec.ollama_image_name,
    )


def _print_image_result(result: DockerImageResult) -> None:
    if result.status == DockerImageStatus.DOCKER_MISSING:
        print("Docker CLI was not found on PATH.")
        return

    if result.status == DockerImageStatus.DOCKERFILE_MISSING:
        print(f"Dockerfile was not found: {result.dockerfile_path}")
        return

    if result.status == DockerImageStatus.EXISTS:
        print(f"Docker sandbox base image already exists: {result.image_name}")
        return

    if result.status == DockerImageStatus.CREATED:
        print(f"Docker sandbox base image created: {result.image_name}")
        return

    print(f"Docker sandbox base image build failed: {result.image_name}")


def _exit_code_from_image_result(result: DockerImageResult) -> int:
    if result.status in {DockerImageStatus.EXISTS, DockerImageStatus.CREATED}:
        return 0

    return 1


def _exit_code_from_run_result(result: DockerRunResult) -> int:
    return result.exit_code
