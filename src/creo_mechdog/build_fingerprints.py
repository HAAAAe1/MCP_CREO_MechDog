"""Stable build fingerprints for repository-native text dependencies.

Repository source files can change line endings (CRLF vs LF) without any
semantic change, for example through git's autocrlf normalization or an
editor resave. Fingerprints that hash raw bytes then force needless loader
rebuilds, which replaces the registered loader generation and silently
breaks an existing Creo registration. Build fingerprints therefore hash the
CRLF→LF-normalized content of repository-native text dependencies; SDK
headers, effective configuration, integrity SHA256 values of binaries and
release artifacts keep using raw bytes.
"""

from __future__ import annotations

import hashlib
import itertools
from pathlib import Path

# Identifies the normalized fingerprint algorithm stored in build caches.
FINGERPRINT_ALGORITHM = "sha256-repo-lf-v1"


def normalize_lf(data: bytes) -> bytes:
    """Apply the single CRLF→LF normalization used by build fingerprints."""
    return data.replace(b"\r\n", b"\n")


def read_dependency_snapshot(root: Path, relatives: tuple[str, ...]) -> dict[str, bytes]:
    """Read every dependency once so one build decision uses one consistent view."""
    snapshot: dict[str, bytes] = {}
    for relative in relatives:
        source = root / relative
        if source.is_file():
            snapshot[relative] = source.read_bytes()
    return snapshot


def normalized_digest(prefix: bytes, abi_digest: bytes, snapshot: dict[str, bytes]) -> str:
    """Current algorithm: dependency bytes are normalized before hashing."""
    digest = hashlib.sha256(prefix + abi_digest)
    for relative, data in snapshot.items():
        digest.update(relative.encode() + normalize_lf(data))
    return digest.hexdigest()


def match_cached_fingerprint(
    cache: object, current_fingerprint: str, legacy_candidates: set[str]
) -> tuple[bool, str | None]:
    """Match a build cache against the normalized fingerprint.

    New caches carry ``algorithm`` plus the normalized ``fingerprint`` and may
    reuse their recorded ``generation_key``. Caches without the marker were
    written by the raw-byte algorithm; an exact hit in ``legacy_candidates``
    proves the sources only differ in line endings, and the cached fingerprint
    itself stays the physical generation key so registered paths survive.
    """
    if not isinstance(cache, dict):
        return False, None
    if cache.get("algorithm") == FINGERPRINT_ALGORITHM:
        if cache.get("fingerprint") == current_fingerprint:
            return True, cache.get("generation_key") or current_fingerprint
        return False, None
    legacy = cache.get("fingerprint")
    if isinstance(legacy, str) and legacy in legacy_candidates:
        return True, legacy
    return False, None


def legacy_digest_candidates(
    prefix: bytes, abi_digest: bytes, snapshot: dict[str, bytes]
) -> set[str]:
    """Recompute the pre-normalization algorithm over line-ending variants.

    Older caches stored a raw-byte fingerprint. To prove that today's files
    differ from the cached build only by line endings, each dependency is
    expanded into its original, LF-only and CRLF-only form and the raw-byte
    algorithm is recomputed for every combination. An exact match means the
    cached generation can be reused without rebuilding the DLL or moving the
    registered loader directory.
    """
    variants: list[list[bytes]] = []
    for data in snapshot.values():
        lf = normalize_lf(data)
        variants.append([data, lf, lf.replace(b"\n", b"\r\n")])
    relatives = list(snapshot)
    candidates: set[str] = set()
    for combination in itertools.product(*variants):
        digest = hashlib.sha256(prefix + abi_digest)
        for relative, data in zip(relatives, combination):
            digest.update(relative.encode() + data)
        candidates.add(digest.hexdigest())
    return candidates
