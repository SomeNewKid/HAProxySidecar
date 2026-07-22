"""Create and inspect Docker sandbox container images."""

from __future__ import annotations

import subprocess
from shutil import which

from .models import (
    DockerConfiguration,
    DockerImageResult,
    DockerImageStatus,
)

_DOCKER_EXECUTABLE = "docker"


def ensure_base_image(configuration: DockerConfiguration) -> DockerImageResult:
    """Create the Docker sandbox base image if it is missing."""
    if not configuration.dockerfile_path.exists():
        return DockerImageResult(
            status=DockerImageStatus.DOCKERFILE_MISSING,
            image_name=configuration.profile.image_name,
            dockerfile_path=configuration.dockerfile_path,
        )

    if which(_DOCKER_EXECUTABLE) is None:
        return DockerImageResult(
            status=DockerImageStatus.DOCKER_MISSING,
            image_name=configuration.profile.image_name,
            dockerfile_path=configuration.dockerfile_path,
        )

    if _image_exists(configuration.profile.image_name):
        return DockerImageResult(
            status=DockerImageStatus.EXISTS,
            image_name=configuration.profile.image_name,
            dockerfile_path=configuration.dockerfile_path,
        )

    build_command = _build_image_command(configuration)
    build_result = subprocess.run(
        build_command,
        cwd=configuration.build_context,
        check=False,
    )

    if build_result.returncode != 0:
        return DockerImageResult(
            status=DockerImageStatus.BUILD_FAILED,
            image_name=configuration.profile.image_name,
            dockerfile_path=configuration.dockerfile_path,
            command=build_command,
        )

    return DockerImageResult(
        status=DockerImageStatus.CREATED,
        image_name=configuration.profile.image_name,
        dockerfile_path=configuration.dockerfile_path,
        command=build_command,
    )


def _image_exists(image_name: str) -> bool:
    inspect_command = [
        _DOCKER_EXECUTABLE,
        "image",
        "inspect",
        image_name,
    ]
    result = subprocess.run(
        inspect_command,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _build_image_command(configuration: DockerConfiguration) -> list[str]:
    return [
        _DOCKER_EXECUTABLE,
        "build",
        "--file",
        str(configuration.dockerfile_path),
        "--tag",
        configuration.profile.image_name,
        *configuration.profile.image_build_arguments,
        str(configuration.build_context),
    ]
