"""Prepare an immutable resident Blend callback for explicit Creo loading."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def prepare_callback(build: Path, dll_sha256: str) -> dict:
    """Publish setup files without loading code or changing Creo security policy."""
    dll = build / "creo_blend_sync.dll"
    if len(dll_sha256) != 64 or hashlib.sha256(dll.read_bytes()).hexdigest() != dll_sha256:
        raise ValueError("Blend callback hash does not match the current build")
    root = build.parent.resolve()
    directory = build / "blend_callback" / dll_sha256
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "callback.dll"
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != dll_sha256:
            raise ValueError("Immutable Blend callback copy was changed; inspect it before setup")
    else:
        with target.open("xb") as output:
            output.write(dll.read_bytes())
    root_tag = hashlib.sha256(str(root).casefold().encode()).hexdigest()[:8]
    command = "MechDogBlend_" + dll_sha256[:24] + "_" + root_tag
    bootstrap = {"protocol": 2, "command": command, "resource_root": str(root)}
    metadata = {
        **bootstrap,
        "dll_sha256": dll_sha256,
        "module_file": str(target.resolve()),
        "ready_file": str((directory / "callback_result.json").resolve()),
        "registry_file": str((directory / "protk.dat").resolve()),
        "setup": "In Creo Auxiliary Applications, register protk.dat and start this application; review any DLL prompt yourself. Modeling never changes the security policy.",
    }
    if len(metadata["module_file"]) >= 260 or any(
        "\n" in value for value in (str(root), str(directory))
    ):
        raise ValueError("Blend callback setup path is too long or contains a newline")

    def publish(path: Path, content: str) -> None:
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8", newline="\n")

    publish(directory / "callback_bootstrap.json", json.dumps(bootstrap, indent=2) + "\n")
    registry_content = (
        "name MCP_CREO_MechDog Blend\nstartup dll\nexec_file " + metadata["module_file"]
    )
    registry_content += (
        "\ntext_dir " + str(directory.resolve()) + "\nallow_stop true\ndelay_start false\nend\n"
    )
    publish(directory / "protk.dat", registry_content)
    publish(build / "blend_callback.protk.dat", registry_content)
    metadata["registry_shortcut"] = str((build / "blend_callback.protk.dat").resolve())
    publish(build / "blend_callback_setup.json", json.dumps(metadata, indent=2) + "\n")
    return metadata


def callback_setup_status(build: Path) -> dict:
    """Report setup artifacts without claiming the DLL is loaded in Creo."""
    try:
        data = json.loads((build / "blend_callback_setup.json").read_text(encoding="utf-8"))
        module = Path(data["module_file"])
        if (
            data["protocol"] != 2
            or hashlib.sha256(module.read_bytes()).hexdigest() != data["dll_sha256"]
        ):
            raise ValueError("Invalid callback setup")
        return {
            "artifact_status": "prepared",
            "protocol": 2,
            "registry_file": data["registry_file"],
            "registry_shortcut": data.get("registry_shortcut", data["registry_file"]),
            "module_file": data["module_file"],
            "dll_sha256": data["dll_sha256"],
            "manual_setup_when_not_loaded": True,
            "runtime_readiness": "Native worker checks the active Creo DLL handle and protocol for each loft; artifacts alone do not confirm readiness",
            "instruction": data["setup"],
        }
    except (OSError, ValueError, KeyError, TypeError):
        return {
            "artifact_status": "not_prepared",
            "instruction": "Build the native worker to create the explicit callback setup artifacts",
        }
