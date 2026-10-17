"""BUG-001 developer native acceptance; independent E-drive jobs/models, shared Toolkit lock.

Fault injection only terminates subprocess.run's own newly started worker on timeout.
Never runs historical G0 injection, restarts Creo, or edits an existing user model.
"""

from __future__ import annotations

import argparse
import asyncio
import platform
import subprocess
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__" and not __package__:
    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "tools.test_model_reconciliation", *sys.argv[1:]], cwd=ROOT
        )
    )

import bridge
import generic_bridge as general
from creo_mechdog import reconciliation as rec
from tools.dev_check import git_state, source_hash


def box(pads: int = 0, base: bool = True) -> list[dict]:
    operations = (
        [
            {
                "op": "sketch",
                "label": "profile",
                "entities": [{"type": "rectangle", "name": "base", "min": [0, 0], "max": [60, 40]}],
            },
            {"op": "extrude", "label": "solid", "sketch": "profile", "depth": 10},
        ]
        if base
        else []
    )
    for index in range(pads):
        operations.extend(
            [
                {
                    "op": "sketch",
                    "label": f"pad_sk_{index}",
                    "entities": [
                        {
                            "type": "circle",
                            "name": f"circle_{index}",
                            "center": [8 + index % 8 * 6, 8 + index // 8 * 6],
                            "radius": 2,
                        }
                    ],
                },
                {
                    "op": "extrude",
                    "label": f"pad_{index}",
                    "sketch": f"pad_sk_{index}",
                    "depth": 12,
                },
            ]
        )
    return operations


class Acceptance:
    def __init__(self, directory: Path):
        self.directory = directory
        self.report = {
            "started_at": bridge.now(),
            "environment": platform.platform(),
            "source": git_state(ROOT),
            "data_root": str(directory),
            "cases": [],
            "not_verified": ["Creo 9/10", "WorkBuddy client", "external-reference recovery"],
        }
        self.counter = 0

    def record(self, name: str, **value) -> dict:
        self.report["cases"].append({"case": name, **value})
        bridge.write_json(self.directory / "evidence.json", self.report)

        print(name, value.get("job", {}).get("status", "recorded"), flush=True)
        return value

    def prepare(self):
        """Create only new isolated abnormal models for an external MCP client."""
        baseline = self.submit(box())
        assert baseline["status"] == "succeeded", baseline
        diverged = self.submit(box(24, base=False), baseline["model_id"], "timeout")
        saved = self.submit(box(), fault="lost_delivery")
        partial = self.submit(box(24), fault="timeout")
        abandoned = self.submit(box(24), fault="timeout")
        items = []
        for action, job in zip(rec.ACTIONS, (diverged, saved, partial, abandoned), strict=True):
            assert job["status"] == "unknown_outcome", job
            items.append(
                {"action": action, "model_id": job["model_id"], "original_job_id": job["job_id"]}
            )
        value = {"data_root": str(self.directory), "items": items, "prepared_at": bridge.now()}
        bridge.write_json(self.directory / "fixtures.json", value)
        bridge.write_json(
            self.directory / "client-config.json",
            {
                "mcpServers": {
                    "MCP_CREO_MechDog_dev": {
                        "command": sys.executable,
                        "args": [
                            str(ROOT / "tools/test_model_reconciliation.py"),
                            "--serve",
                            "--data-root",
                            str(self.directory),
                        ],
                        "cwd": str(ROOT),
                    }
                }
            },
        )
        return value

    def runner(self, job: dict, fault: str = "none") -> dict:
        output = self.directory / f"runner-{job['job_id']}.log"
        with output.open("wb") as stream:
            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "tools.test_model_reconciliation",
                    "--data-root",
                    str(self.directory),
                    "--run-job",
                    job["job_id"],
                    "--fault",
                    fault,
                ],
                cwd=ROOT,
                stdout=stream,
                stderr=subprocess.STDOUT,
                timeout=300,
                creationflags=bridge.HIDDEN,
            )
        if process.returncode:
            raise RuntimeError(output.read_text(encoding="utf-8", errors="replace"))
        return bridge.get_job(job["job_id"])

    def submit(self, operations: list[dict], model_id: str | None = None, fault="none") -> dict:
        with patch.object(bridge.subprocess, "Popen"):
            job = general.submit(
                operations,
                model_id=model_id,
                expected_revision=general.model_info(model_id)["revision"] if model_id else None,
            )
        result = self.runner(job, fault)
        self.record(f"modeling_{fault}", input=operations, submitted=job, job=result)
        return result

    def recover(self, model_id: str, action: str, live: bool = False) -> dict:
        evidence = rec.inspect(model_id, live)
        self.record(f"preflight_{action}", evidence=evidence)
        assert evidence["actions"][action]["available"], evidence["actions"]
        self.counter += 1
        arguments = (
            model_id,
            action,
            evidence["revision"],
            evidence["pending_job"],
            evidence["evidence_token"],
            f"native_case_{self.counter}",
        )
        with patch.object(bridge.subprocess, "Popen"):
            job = rec.apply(*arguments)
        result = self.runner(job)
        self.record(action, submitted=job, job=result, model=general.model_info(model_id))
        assert result["status"] == "succeeded", result
        duplicate = rec.apply(*arguments)
        assert (
            duplicate["job_id"] == result["job_id"] and duplicate["revision"] == result["revision"]
        )
        return result

    def run(self):
        self.report["worker"] = rec.identity(bridge.build_native())
        self.report["fingerprints"] = {
            name: source_hash(ROOT / name)
            for name in (
                "bridge.py",
                "generic_bridge.py",
                "native/generic.cpp",
                "src/creo_mechdog/reconciliation.py",
            )
        }
        probe = bridge.session_status(2, build_worker=False)
        self.record("session", probe=probe)
        assert probe.get("connected"), probe
        normal = self.submit(box())
        assert (
            normal["status"] == "succeeded" and normal["result"]["saved_file_reloaded_and_verified"]
        )
        mid = normal["model_id"]
        baseline = general.model_info(mid)
        assert abs(baseline["inspection"]["volume_mm3"] - 24000) < 0.01
        unknown = self.submit(box(24, base=False), mid, "timeout")
        assert unknown["status"] == "unknown_outcome", unknown
        live = rec.inspect(mid, live=True)
        self.record("baseline_diverged", evidence=live)
        assert live["live"].get("matches_baseline") is False, live
        restored = self.recover(mid, "restore_baseline")
        assert restored["revision"] == baseline["revision"]
        assert abs(restored["result"]["inspection"]["volume_mm3"] - 24000) < 0.01
        assert rec.identity(Path(baseline["part_file"]))["sha256"] == baseline["part_sha256"]
        following = self.submit([{"op": "set_parameters", "values": {"RECOVERY_NEXT": 7}}], mid)
        assert (
            following["status"] == "succeeded" and following["revision"] == baseline["revision"] + 1
        )
        # Real save/reload succeeds; hide its delivered result from the Python
        # adapter to reproduce saved-but-not-registered without killing Creo.
        saved = self.submit(box(), fault="lost_delivery")
        assert saved["status"] == "unknown_outcome"
        accepted = self.recover(saved["model_id"], "accept_saved")
        assert accepted["revision"] == 1
        assert self.submit([{"op": "regenerate"}], saved["model_id"])["status"] == "succeeded"
        partial = self.submit(box(24), fault="timeout")
        assert partial["status"] == "unknown_outcome"
        accepted_live = self.recover(partial["model_id"], "accept_live", live=True)
        assert (
            accepted_live["revision"] == 1
            and accepted_live["result"]["saved_file_reloaded_and_verified"]
        )
        assert self.submit([{"op": "regenerate"}], partial["model_id"])["status"] == "succeeded"
        abandoned = self.submit(box(24), fault="timeout")
        assert abandoned["status"] == "unknown_outcome"
        self.recover(abandoned["model_id"], "abandon_new")
        assert general.model_info(abandoned["model_id"])["status"] == "abandoned"
        # Ordinary failed operation must still roll back its owned checkpoint.
        failure = self.submit(
            [{"op": "set_dimensions", "values": [{"id": 999999, "value": 5}]}], mid
        )
        assert failure["status"] == "failed" and failure["result"]["rollback_succeeded"], failure
        other = self.submit(box())
        assert other["status"] == "succeeded"
        control = self.submit(box(30))
        assert control["status"] == "succeeded" and len(control["operations"]) == 62
        assert control["result"]["saved_file_reloaded_and_verified"] is True
        self.report.update(success=True, finished_at=bridge.now())
        bridge.write_json(self.directory / "evidence.json", self.report)


def serve(directory: Path, metadata_only: bool = False) -> None:
    """Developer fixture server; shares the real lock and never routes user data."""
    import server

    real_popen = subprocess.Popen

    def route(command, *args, **kwargs):
        if (
            isinstance(command, list)
            and len(command) == 4
            and command[1:3] == [str(ROOT / "bridge.py"), "run-job"]
        ):
            command = [
                command[0],
                "-m",
                "tools.test_model_reconciliation",
                "--data-root",
                str(directory),
                "--run-job",
                command[3],
            ]
        return real_popen(command, *args, **kwargs)

    with ExitStack() as stack:
        stack.enter_context(patch.object(subprocess, "Popen", side_effect=route))
        if metadata_only:
            stack.enter_context(patch.object(server.startup, "start"))
            stack.enter_context(patch.object(server.updates, "start"))
        server.mcp.run()


async def mcp_acceptance(directory: Path, metadata_only: bool = False) -> None:
    """Actual stdio protocol acceptance; this is developer evidence, not WorkBuddy."""
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    fixtures = bridge.read_json(directory / "fixtures.json")
    report = {
        "client": "Python MCP stdio developer client",
        "calls": [],
        "started_at": bridge.now(),
        "workbuddy": "not_run",
    }

    async with Client(
        StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "tools.test_model_reconciliation",
                "--serve",
                "--data-root",
                str(directory),
                *(["--metadata-only"] if metadata_only else []),
            ],
            cwd=ROOT,
        ),
        read_timeout_seconds=150,
    ) as client:

        async def call(name, args, error=False):
            reply = await client.call_tool(name, args)
            value = reply.structured_content
            report["calls"].append(
                {
                    "tool": name,
                    "input": args,
                    "is_error": reply.is_error,
                    "result": value,
                    "text": [block.text for block in reply.content if hasattr(block, "text")],
                }
            )
            bridge.write_json(directory / "mcp-evidence.json", report)
            assert bool(reply.is_error) == error, report["calls"][-1]
            return value

        capability = await call("creo_capabilities", {})
        assert capability["tool_count"] == 83
        assert Path(capability["runtime"]["job_root"]) == bridge.JOBS
        # Public diagnostic remains accessible while the actual shared OS lock is busy.
        first = fixtures["items"][0]
        with bridge.toolkit_lock(operation="developer_busy_probe"):
            evidence = await call("creo_reconcile_model", {"model_id": first["model_id"]})
            args = {
                "model_id": first["model_id"],
                "mode": "apply",
                "action": first["action"],
                "expected_revision": evidence["revision"],
                "expected_pending_job_id": evidence["pending_job"],
                "evidence_token": evidence["evidence_token"],
                "idempotency_key": "mcp_busy_not_accepted",
            }
            busy = await call("creo_reconcile_model", args, error=True)
            assert busy["status"] == "busy" and busy["accepted"] is False
        for index, item in enumerate([] if metadata_only else fixtures["items"]):
            evidence = await call(
                "creo_reconcile_model",
                {"model_id": item["model_id"], "live": item["action"] == "accept_live"},
            )
            args = {
                "model_id": item["model_id"],
                "mode": "apply",
                "action": item["action"],
                "expected_revision": evidence["revision"],
                "expected_pending_job_id": evidence["pending_job"],
                "evidence_token": evidence["evidence_token"],
                "idempotency_key": f"mcp_recovery_case_{index}",
            }
            created = await call("creo_reconcile_model", args)
            for _ in range(160):
                result = await call(
                    "creo_get_job", {"job_id": created["job_id"], "detail": "compact"}
                )
                if result["status"] not in ("queued", "running"):
                    break
                await asyncio.sleep(1)
            assert result["status"] == "succeeded", result
            if item["action"] != "abandon_new":
                assert result["result"]["saved_file_reloaded_and_verified"]
                assert result["result"]["sha256"]
            duplicate = await call("creo_reconcile_model", args)
            assert duplicate["job_id"] == created["job_id"]
            original = await call(
                "creo_get_job", {"job_id": item["original_job_id"], "detail": "compact"}
            )
            assert original["status"] == "unknown_outcome"
            assert original["recovery"]["resolution"]["recovery_id"] == created["job_id"]
        report.update(success=True, finished_at=bridge.now())
        report["scope"] = (
            "metadata and busy only" if metadata_only else "four explicit recovery actions"
        )
        bridge.write_json(directory / "mcp-evidence.json", report)


def controlled_deadline(directory: Path) -> dict:
    """Exercise the production phase watchdog with a short test-only constructor budget."""
    directory.mkdir(parents=True, exist_ok=True)
    exe = directory / "recovery-deadline.exe"
    script = directory / "build.cmd"
    script.write_text(
        f"@echo off\nsetlocal DisableDelayedExpansion\n{bridge.compiler_setup_script(bridge.config())}\n"
        f'cl /nologo /MD /EHsc /std:c++17 /W3 /I"{ROOT / "native"}" "{ROOT / "tools/test_recovery_deadline.cpp"}" '
        f'/Fo"{directory / "fixture.obj"}" /Fe"{exe}"\n',
        encoding="utf-8",
    )
    with (directory / "build.log").open("wb") as output:
        process = subprocess.run(
            ["cmd.exe", "/d", "/c", str(script)],
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=120,
            creationflags=bridge.HIDDEN,
        )
    assert process.returncode == 0, "Deadline fixture failed to compile; inspect build.log"
    cases = []
    for mode, expected in (("complete", 0), ("timeout", 31)):
        path = directory / mode
        path.mkdir()
        began = time.monotonic()
        process = subprocess.run(
            [str(exe), mode, str(path)], timeout=3, creationflags=bridge.HIDDEN
        )
        value = {
            "mode": mode,
            "exit_code": process.returncode,
            "elapsed_seconds": time.monotonic() - began,
        }
        assert process.returncode == expected, value
        if mode == "timeout":
            value["checkpoint"] = bridge.read_json(path / "native_checkpoint.json")
            assert value["checkpoint"]["completion_stage"] == "recovery_phase_timeout"
            assert not (path / "native_result.json").exists()
        else:
            assert bridge.read_json(path / "native_result.json")["success"]
        cases.append(value)
    result = {"success": True, "scope": "Actual production watchdog, no Creo calls", "cases": cases}
    bridge.write_json(directory / "deadline-evidence.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--run-job")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--mcp", action="store_true")
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--controlled", action="store_true")
    parser.add_argument("--fault", choices=("none", "timeout", "lost_delivery"), default="none")
    args = parser.parse_args()
    directory = (
        args.data_root or ROOT / f"build/bug001-feat018-recovery/run-{time.time_ns()}"
    ).resolve()
    allowed = (ROOT / "build/bug001-feat018-recovery").resolve()
    if allowed not in directory.parents:
        raise ValueError(
            "Test data must use a new directory under E-drive ignored recovery fixtures"
        )
    directory.mkdir(parents=True, exist_ok=True)
    bridge.JOBS = directory / "jobs"
    general.MODELS = directory / "models"
    if args.controlled:
        controlled_deadline(directory)
        return
    if args.serve:
        serve(directory, args.metadata_only)
        return
    if args.mcp:
        asyncio.run(mcp_acceptance(directory, args.metadata_only))
        return
    if args.run_job:
        real_run = subprocess.run

        def native_run(*values, **kwargs):
            if args.fault == "timeout":
                kwargs["timeout"] = 12
            result = real_run(*values, **kwargs)
            if args.fault == "lost_delivery":
                file = bridge.job_path(args.run_job) / "native_result.json"
                if file.exists():
                    file.rename(file.with_name("delivered-but-not-received.json"))
            return result

        with patch.object(bridge.subprocess, "run", side_effect=native_run):
            bridge.run_job(args.run_job)
        return
    acceptance = Acceptance(directory)
    try:
        if args.prepare:
            acceptance.prepare()
        else:
            acceptance.run()
    except BaseException as error:
        acceptance.report.update(success=False, error=str(error), finished_at=bridge.now())
        bridge.write_json(directory / "evidence.json", acceptance.report)
        raise


if __name__ == "__main__":
    main()
