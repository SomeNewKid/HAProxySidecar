"""Remove Python packaging tools from a minimal sandbox image."""

from __future__ import annotations

import pathlib
import shutil
import sysconfig

_RUNTIME_SITECUSTOMIZE_PATH = pathlib.Path("/tmp/runtime_sitecustomize.py")
_PACKAGE_NAMES = (
    "_distutils_hack",
    "ensurepip",
    "pip",
    "pkg_resources",
    "setuptools",
    "wheel",
)


def main() -> None:
    """Remove packaging modules and install runtime process guards."""
    paths = {
        pathlib.Path(sysconfig.get_path(name))
        for name in ("purelib", "platlib", "stdlib")
    }
    paths.update(_discover_extra_package_paths())

    patterns = [
        *_PACKAGE_NAMES,
        *(f"{name}-*.dist-info" for name in _PACKAGE_NAMES),
        *(f"{name}-*.egg-info" for name in _PACKAGE_NAMES),
        "distutils-precedence.pth",
    ]
    for path in paths:
        for pattern in patterns:
            for match in path.glob(pattern):
                if match.is_dir():
                    shutil.rmtree(match, ignore_errors=True)
                else:
                    match.unlink(missing_ok=True)

    for path in paths:
        if path.exists() and path.name != "ensurepip":
            shutil.copyfile(_RUNTIME_SITECUSTOMIZE_PATH, path / "sitecustomize.py")


def _discover_extra_package_paths() -> set[pathlib.Path]:
    roots = (pathlib.Path("/usr/local/lib"), pathlib.Path("/usr/lib"))
    patterns = (
        "python*/dist-packages",
        "python*/site-packages",
        "python*/ensurepip",
    )
    return {
        path
        for root in roots
        if root.exists()
        for pattern in patterns
        for path in root.glob(pattern)
    }


if __name__ == "__main__":
    main()
