# ------------------------------------------------------------------------------
# SPDX-FileCopyrightText: ADAC Contributors
# SPDX-License-Identifier: Apache-2.0
# ------------------------------------------------------------------------------

import re as _re
import typing as _typing

__version__ = "0.1.0"

_SEMVER = _re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)


class SemVer(_typing.NamedTuple):
    major: int
    minor: int
    patch: int
    prerelease: str | None
    build: str | None


def parse_semver(*, text: str) -> SemVer:
    match = _SEMVER.match(text)
    if match is None:
        raise ValueError(f"not a semantic version: {text!r}")
    return SemVer(
        major=int(match["major"]),
        minor=int(match["minor"]),
        patch=int(match["patch"]),
        prerelease=match["prerelease"],
        build=match["build"],
    )


version = parse_semver(text=__version__)
