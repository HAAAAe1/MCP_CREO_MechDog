"""Seed provenance and historical native load evidence, never an implicit Toolkit probe."""

from __future__ import annotations

import json
import re
from pathlib import Path

import bridge
from creo_mechdog.recovery import file_identity

OBSERVATION_FIELDS = (
    "status",
    "toolkit_code",
    "creo_release_numeric",
    "creo_release_query_code",
    "session_fingerprint",
    "seed_sha256",
    "job_id",
    "checked_at",
    "modeling_saved_reloaded_verified",
    "evidence_persisted",
)


def metadata(entry: dict) -> dict:
    """No production Creo version is inferred from tested_creo, filenames or hashes."""
    rows = []
    digest = entry.get("sha256", "")
    if re.fullmatch(r"[a-f0-9]{64}", digest):
        directory = bridge.ROOT / "build/seed_compatibility" / digest
        # Bounded history only: none of these records proves the current session is compatible.
        if directory.is_dir() and not directory.is_symlink() and not directory.is_junction():
            for file in sorted(directory.glob("*.json"), reverse=True)[:2]:
                try:
                    if file.is_symlink() or file.stat().st_size > 16384:
                        continue
                    row = bridge.read_json(file)
                    if row.get("seed_sha256") == digest and row.get("status") in (
                        "loaded",
                        "load_failed",
                    ):
                        view = {key: row[key] for key in OBSERVATION_FIELDS if key in row}
                        if len(json.dumps(view, ensure_ascii=False).encode("utf-8")) <= 1024:
                            rows.append(view)
                except (OSError, ValueError, TypeError, AttributeError):
                    continue
    return {
        "seed_build_version": entry.get("seed_build_version"),
        "seed_build_version_source": entry.get("seed_build_version_source"),
        "native_compatibility": {
            "status": "not_verified_for_current_session",
            "scope": "available means matching file hash, not Creo load compatibility",
            "observations": rows,
        },
    }


def observe_load(request: dict, result: dict, job_id: str) -> dict | None:
    """Record only the actual load API result; later modeling success is separate."""
    seed = request.get("loft_seed")
    native = result.get("seed_native_load")
    if not seed or not isinstance(native, dict):
        return None
    observation = {
        "status": native.get("status", "not_attempted"),
        "toolkit_code": native.get("toolkit_code"),
        "creo_release_numeric": result.get("creo_release_numeric"),
        "creo_release_query_code": result.get("creo_release_query_code"),
        "session_fingerprint": result.get("session_fingerprint"),
        "seed_sha256": seed.get("snapshot_sha256"),
        "job_id": job_id,
        "checked_at": bridge.now(),
        "modeling_saved_reloaded_verified": result.get("saved_file_reloaded_and_verified") is True,
        "evidence_persisted": False,
    }
    release = observation["creo_release_numeric"]
    digest = observation["seed_sha256"]
    if (
        observation["status"] not in ("loaded", "load_failed")
        or isinstance(release, bool)
        or not isinstance(release, int)
        or release <= 0
        or not isinstance(digest, str)
        or not re.fullmatch(r"[a-f0-9]{64}", digest)
        or not observation["session_fingerprint"]
    ):
        observation["reason"] = (
            "Native load or runtime identity is incomplete; compatibility remains unverified"
        )
        return observation
    try:
        if file_identity(Path(request["template_file"])).get("sha256") != digest:
            raise ValueError(
                "Seed snapshot changed or exceeded diagnostic budget; load evidence is not attributable"
            )
        target = bridge.ROOT / "build/seed_compatibility" / digest / f"{release}-{job_id}.json"
        if any(p.is_symlink() or p.is_junction() for p in target.parents):
            raise ValueError("Seed evidence directory cannot traverse links")
        target.parent.mkdir(parents=True, exist_ok=True)
        observation["evidence_persisted"] = True
        bridge.write_json(target, observation)
    except (OSError, ValueError, KeyError) as error:
        observation.update(evidence_persisted=False, evidence_error=str(error))
    return observation
