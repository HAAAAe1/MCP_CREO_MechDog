"""BUG-001 / DEV-030 G0 isolation verification driver.

Developer-only driver for the isolated G0 worktree. Drives the real MCP stdio
service like a client, injects timeouts/kills at process level, and appends
per-scenario evidence to build/g0_evidence.json. Never modifies product code.

Usage:
  python build/g0_driver.py identity|start|s1|s2|s3|s4|s5|s6|s6restart
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from creo_mechdog.paths import SOURCE_PATHS

EVIDENCE = ROOT / "build/g0_evidence.json"
NATIVE_LOG_POLL = 0.1


def ev_load() -> dict:
    if EVIDENCE.exists():
        return json.loads(EVIDENCE.read_text(encoding="utf-8"))
    return {"driver": "build/g0_driver.py", "scenarios": {}, "models": {}}


def ev_save(data: dict) -> None:
    EVIDENCE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def record(scenario: str, **fields) -> None:
    data = ev_load()
    data["scenarios"].setdefault(scenario, {}).update(fields)
    ev_save(data)
    print(f"[{scenario}] " + json.dumps(fields, ensure_ascii=False)[:500], flush=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def box(pads: int = 0, x=60, y=40, z=10, prefix: str = "pad", base: bool = True) -> list[dict]:
    ops = []
    if base:
        ops += [
            {
                "op": "sketch",
                "label": "profile",
                "entities": [{"type": "rectangle", "name": "base", "min": [0, 0], "max": [x, y]}],
            },
            {"op": "extrude", "label": "solid", "sketch": "profile", "depth": z},
        ]
    for i in range(pads):
        ops.append(
            {
                "op": "sketch",
                "label": f"{prefix}_sk_{i}",
                "entities": [
                    {
                        "type": "circle",
                        "name": f"{prefix}_c_{i}",
                        "center": [8 + (i % 8) * 6, 8 + (i // 8) * 6],
                        "radius": 2,
                    }
                ],
            }
        )
        ops.append({"op": "extrude", "label": f"{prefix}_{i}", "sketch": f"{prefix}_sk_{i}", "depth": 2})
    return ops


def pads_for_timeout(timeout_s: float, multiple: float = 3.0) -> int:
    """Pick a pad count from the measured s1 rate so the job outlives the budget."""
    s1 = ev_load()["scenarios"].get("s1", {})
    per_pad = s1.get("seconds_per_pad")
    if not per_pad:
        return 30
    pads = math.ceil((timeout_s * multiple) / per_pad)
    return max(30, min(pads, 400))


def worker_pids(job_dir: str | None = None) -> list[tuple[int, str]]:
    ps = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process -Filter \"Name='creo_worker.exe'\""
            " | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    out = ps.stdout.strip()
    if not out:
        return []
    items = json.loads(out)
    if isinstance(items, dict):
        items = [items]
    result = []
    for item in items:
        cmdline = item.get("CommandLine") or ""
        if job_dir is None or job_dir.lower() in cmdline.lower():
            result.append((int(item["ProcessId"]), cmdline))
    return result


def kill_worker(job_dir: str) -> int:
    victims = worker_pids(job_dir)
    for pid, _cmdline in victims:
        subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)], capture_output=True, text=True, timeout=30
        )
    time.sleep(0.5)
    return len(victims)


def native_log_phases(job_dir: str) -> list[str]:
    log = Path(job_dir) / "native.log"
    if not log.exists():
        return []
    text = log.read_bytes().decode("utf-8", errors="replace")
    return re.findall(r"PHASE=([^\r\n]+)", text)


def wait_for_phase(job_dir: str, phase: str, deadline_s: float) -> bool:
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        if phase in native_log_phases(job_dir):
            return True
        time.sleep(NATIVE_LOG_POLL)
    return False


def set_config_timeout(seconds: int) -> int:
    cfg_path = ROOT / "config.json"
    value = read_json(cfg_path)
    previous = int(value["generic_timeout_seconds"])
    value["generic_timeout_seconds"] = seconds
    write_json(cfg_path, value)
    return previous


def restore_config_timeout(previous: int) -> None:
    cfg_path = ROOT / "config.json"
    value = read_json(cfg_path)
    value["generic_timeout_seconds"] = previous
    write_json(cfg_path, value)


def model_json(model_id: str) -> dict:
    return read_json(SOURCE_PATHS.models / model_id / "model.json")


def inject_model_fields(model_id: str, **fields) -> dict:
    path = SOURCE_PATHS.models / model_id / "model.json"
    model = read_json(path)
    before = {key: model.get(key) for key in fields}
    model.update(fields)
    write_json(path, model)
    return {"path": str(path), "before": before, "applied": fields}


def output_listing(model_id: str) -> list[dict]:
    out = SOURCE_PATHS.models / model_id / "output"
    if not out.exists():
        return []
    return [
        {"name": p.name, "sha256": sha256(p), "bytes": p.stat().st_size} for p in out.iterdir()
    ]


async def ensure_channel_ready(c, scenario: str, budget_s: float = 300.0) -> None:
    """After any worker kill, channel health is invalidated by design; restore it
    through the official creo_startup_status(retry=true) verification path."""
    r = await c.call_tool("creo_startup_status", {"retry": True})
    deadline = time.monotonic() + budget_s
    while time.monotonic() < deadline:
        r = await c.call_tool("creo_startup_status", {})
        st = r.structured_content
        if st.get("state") == "ready" and st.get("connected"):
            record(scenario, channel_retry_state="ready")
            return
        await asyncio.sleep(3)
    raise TimeoutError(f"channel retry did not reach ready: {st}")


async def poll_job(c, job_id: str, deadline_s: float = 300.0) -> dict:
    deadline = time.monotonic() + deadline_s
    last: dict | None = None
    while time.monotonic() < deadline:
        r = await c.call_tool("creo_get_job", {"job_id": job_id})
        last = r.structured_content
        if last and last.get("status") not in ("queued", "running"):
            return last
        await asyncio.sleep(1)
    return last or {"status": "poll_timeout"}


async def call(c, name: str, args: dict) -> dict:
    r = await c.call_tool(name, args)
    content = r.structured_content
    if content is None:
        content = {"raw": [getattr(item, "text", None) for item in r.content]}
    if r.is_error:
        content = {"is_error": True, **content}
    return content


async def submit_and_record(c, scenario: str, name: str, args: dict) -> dict:
    submitted = await call(c, name, args)
    record(scenario, **{f"submit_{name}": submitted})
    return submitted


async def get_client():
    return Client(
        StdioServerParameters(command=sys.executable, args=[str(ROOT / "server.py")], cwd=ROOT),
        read_timeout_seconds=120,
    )


async def ensure_ready(c, scenario: str) -> None:
    from tools.mcp_readiness import wait_for_startup

    status = await wait_for_startup(c, {}, ROOT / "build/g0_readiness.json", budget=420)
    record(
        scenario,
        startup_ready={
            "state": status.get("state"),
            "connected": status.get("connected"),
        },
    )


def register_model(key: str, **fields) -> None:
    data = ev_load()
    data.setdefault("models", {})[key] = fields
    ev_save(data)


async def cmd_identity() -> None:
    import version

    data = ev_load()
    data["identity"] = {
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "service_version": version.VERSION,
        "git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT
        ).stdout.strip(),
        "git_dirty": subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=ROOT
        ).stdout.strip(),
        "git_branch": subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, cwd=ROOT
        ).stdout.strip(),
        "worker_exe_sha256": sha256(ROOT / "build/creo_worker.exe"),
        "worker_exe_mtime_utc": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime((ROOT / "build/creo_worker.exe").stat().st_mtime)
        ),
        "config": read_json(ROOT / "config.json"),
        "python": sys.version.split()[0],
        "data_root": str(SOURCE_PATHS.data_root),
    }
    ps = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-Process parametric -ErrorAction SilentlyContinue"
            " | Select-Object Id,StartTime,WorkingSet64,Path | ConvertTo-Json -Compress",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    data["identity"]["creo_process"] = ps.stdout.strip() or "none"
    ev_save(data)
    print(json.dumps(data["identity"], ensure_ascii=False, indent=2))


async def cmd_start() -> None:
    async with await get_client() as c:
        await ensure_ready(c, "startup")
        status = await call(c, "creo_session_status", {})
        record("startup", session_status=status)


async def cmd_s1() -> None:
    pads = 30
    ops = box(pads=pads)
    async with await get_client() as c:
        await ensure_ready(c, "s1")
        t0 = time.monotonic()
        submitted = await submit_and_record(c, "s1", "creo_execute_plan", {"operations": ops})
        result = await poll_job(c, submitted["job_id"], deadline_s=420)
        duration = time.monotonic() - t0
        part = Path(result["result"]["part_file"]) if result.get("result") else None
        record(
            "s1",
            job_id=submitted["job_id"],
            model_id=submitted["model_id"],
            submit_revision=submitted.get("revision"),
            final_status=result["status"],
            final_revision=result.get("revision"),
            saved_verified=(
                result.get("result", {}).get("saved_file_reloaded_and_verified")
                if result.get("result")
                else None
            ),
            part_sha256=sha256(part) if part and part.exists() else None,
            duration_seconds=round(duration, 2),
            ops_count=len(ops),
            pads=pads,
            seconds_per_pad=round(max(duration - 15, 0.2) / pads, 3),
            message=result.get("message"),
        )
        assert result["status"] == "succeeded", result
        assert result["result"]["saved_file_reloaded_and_verified"] is True, result
        register_model(
            "m1", model_id=submitted["model_id"], revision=result.get("revision")
        )


async def cmd_s2() -> None:
    timeout_s = 12
    pads = pads_for_timeout(timeout_s)
    previous = set_config_timeout(timeout_s)
    record(
        "s2", injected_timeout_seconds=timeout_s, previous_timeout_seconds=previous, pads=pads
    )
    try:
        async with await get_client() as c:
            await ensure_ready(c, "s2")
            submitted = await submit_and_record(
                c,
                "s2",
                "creo_execute_plan",
                {"operations": box(pads=pads), "model_name": f"g0_s2_{int(time.time())}"},
            )
            job_dir = submitted["job_directory"]
            result = await poll_job(c, submitted["job_id"], deadline_s=180)
            model = model_json(submitted["model_id"])
            record(
                "s2",
                job_id=submitted["job_id"],
                model_id=submitted["model_id"],
                final_status=result["status"],
                stage=result.get("stage"),
                message=result.get("message"),
                recovery_required=result.get("recovery_required"),
                native_phases=native_log_phases(job_dir)[-12:],
                model_after={
                    "status": model.get("status"),
                    "pending_job": model.get("pending_job"),
                    "revision": model.get("revision"),
                    "part_file": model.get("part_file"),
                },
                output_files=output_listing(submitted["model_id"]),
            )
            assert result["status"] == "unknown_outcome", result
            blocked = await call(
                c,
                "creo_execute_plan",
                {
                    "operations": [{"op": "regenerate"}],
                    "model_id": submitted["model_id"],
                    "expected_revision": 0,
                },
            )
            record("s2", resubmit_while_pending=blocked)
            register_model(
                "m2",
                model_id=submitted["model_id"],
                job_id=submitted["job_id"],
                revision=model.get("revision"),
            )
    finally:
        restore_config_timeout(previous)
        record("s2", restored_timeout_seconds=previous)


async def cmd_s3() -> None:
    async with await get_client() as c:
        await ensure_ready(c, "s3")
        submitted = await submit_and_record(
            c,
            "s3",
            "creo_execute_plan",
            {"operations": box(pads=30), "model_name": f"g0_s3_{int(time.time())}"},
        )
        job_dir = submitted["job_directory"]
        hit = wait_for_phase(job_dir, "after_reload_blend_validation", 240)
        killed = kill_worker(job_dir) if hit else 0
        record("s3", phase_hit=hit, workers_killed=killed)
        result = await poll_job(c, submitted["job_id"], deadline_s=180)
        model = model_json(submitted["model_id"])
        record(
            "s3",
            job_id=submitted["job_id"],
            model_id=submitted["model_id"],
            final_status=result["status"],
            message=result.get("message"),
            recovery=result.get("recovery"),
            recovery_required=result.get("recovery_required"),
            model_after={
                "status": model.get("status"),
                "pending_job": model.get("pending_job"),
                "revision": model.get("revision"),
                "part_file": model.get("part_file"),
            },
            saved_output_files=output_listing(submitted["model_id"]),
            native_phases=native_log_phases(job_dir)[-12:],
        )
        register_model("m3", model_id=submitted["model_id"], job_id=submitted["job_id"])


async def cmd_s4() -> None:
    async with await get_client() as c:
        await ensure_ready(c, "s4")
        submitted = await submit_and_record(
            c,
            "s4",
            "creo_execute_plan",
            {"operations": box(pads=30), "model_name": f"g0_s4_{int(time.time())}"},
        )
        job_dir = submitted["job_directory"]
        hit = wait_for_phase(job_dir, "execute_extrude", 180)
        killed = kill_worker(job_dir) if hit else 0
        record("s4", phase_hit=hit, workers_killed=killed)
        result = await poll_job(c, submitted["job_id"], deadline_s=180)
        model = model_json(submitted["model_id"])
        record(
            "s4",
            job_id=submitted["job_id"],
            model_id=submitted["model_id"],
            final_status=result["status"],
            message=result.get("message"),
            model_after={
                "status": model.get("status"),
                "pending_job": model.get("pending_job"),
                "revision": model.get("revision"),
            },
        )
        register_model("m4", model_id=submitted["model_id"], job_id=submitted["job_id"])
        await ensure_channel_ready(c, "s4")
        other = await submit_and_record(
            c,
            "s4",
            "creo_execute_plan",
            {"operations": box(), "model_name": f"g0_s4_other_{int(time.time())}"},
        )
        if other.get("is_error") or not other.get("job_id"):
            record("s4", other_model_error=other)
            return
        other_result = await poll_job(c, other["job_id"], deadline_s=180)
        record(
            "s4",
            other_model_job=other["job_id"],
            other_model_status=other_result["status"],
            other_model_revision=other_result.get("revision"),
            other_saved_verified=(
                other_result.get("result", {}).get("saved_file_reloaded_and_verified")
                if other_result.get("result")
                else None
            ),
        )
        register_model("m5_other", model_id=other["model_id"])


async def cmd_s5() -> None:
    data = ev_load()
    m1 = data["models"]["m1"]
    model_id = m1["model_id"]
    expected_revision = m1["revision"]
    async with await get_client() as c:
        await ensure_ready(c, "s5")
        timeout_s = 12
        pads = pads_for_timeout(timeout_s)
        previous = set_config_timeout(timeout_s)
        try:
            submitted = await submit_and_record(
                c,
                "s5",
                "creo_execute_plan",
                {
                    "operations": box(pads=pads, prefix="s5pad", base=False),
                    "model_id": model_id,
                    "expected_revision": expected_revision,
                },
            )
            result = await poll_job(c, submitted["job_id"], deadline_s=180)
            record(
                "s5",
                timeout_job_id=submitted["job_id"],
                timeout_status=result["status"],
                timeout_message=result.get("message"),
            )
            assert result["status"] == "unknown_outcome", result
        finally:
            restore_config_timeout(previous)
        await ensure_channel_ready(c, "s5")
        blocked = await call(
            c,
            "creo_execute_plan",
            {
                "operations": [{"op": "regenerate"}],
                "model_id": model_id,
                "expected_revision": expected_revision,
            },
        )
        record("s5", resubmit_while_pending=blocked)
        injection = inject_model_fields(model_id, pending_job=None, status="ready")
        record("s5", developer_injection=injection)
        gate = await submit_and_record(
            c,
            "s5",
            "creo_execute_plan",
            {
                "operations": [
                    {
                        "op": "sketch",
                        "label": "g5_sk",
                        "entities": [
                            {"type": "circle", "name": "g5_c", "center": [30, 20], "radius": 3}
                        ],
                    },
                    {"op": "extrude", "label": "g5_pad", "sketch": "g5_sk", "depth": 2},
                ],
                "model_id": model_id,
                "expected_revision": expected_revision,
            },
        )
        gate_result = await poll_job(c, gate["job_id"], deadline_s=180)
        gate_model = model_json(model_id)
        record(
            "s5",
            gate_job_id=gate["job_id"],
            gate_status=gate_result["status"],
            gate_message=gate_result.get("message"),
            gate_result_summary=(
                {
                    key: gate_result.get("result", {}).get(key)
                    for key in (
                        "rollback_succeeded",
                        "failed_stage",
                        "failed_operation_index",
                        "failed_toolkit_call",
                        "toolkit_code",
                        "rollback_message",
                    )
                }
                if gate_result.get("result")
                else None
            ),
            model_after_gate={
                "status": gate_model.get("status"),
                "pending_job": gate_model.get("pending_job"),
                "revision": gate_model.get("revision"),
            },
        )
        if gate_model.get("status") == "ready" and not gate_model.get("pending_job"):
            retry = await submit_and_record(
                c,
                "s5",
                "creo_execute_plan",
                {
                    "operations": [
                        {
                            "op": "sketch",
                            "label": "g5b_sk",
                            "entities": [
                                {
                                    "type": "circle",
                                    "name": "g5b_c",
                                    "center": [45, 20],
                                    "radius": 3,
                                }
                            ],
                        },
                        {"op": "extrude", "label": "g5b_pad", "sketch": "g5b_sk", "depth": 2},
                    ],
                    "model_id": model_id,
                    "expected_revision": gate_model["revision"],
                },
            )
            retry_result = await poll_job(c, retry["job_id"], deadline_s=180)
            record(
                "s5",
                retry_job_id=retry["job_id"],
                retry_status=retry_result["status"],
                retry_revision=retry_result.get("revision"),
                retry_saved_verified=(
                    retry_result.get("result", {}).get("saved_file_reloaded_and_verified")
                    if retry_result.get("result")
                    else None
                ),
                retry_message=retry_result.get("message"),
            )
            if retry_result.get("revision") is not None:
                data = ev_load()
                data["models"]["m1"]["revision"] = retry_result["revision"]
                ev_save(data)


async def cmd_s6() -> None:
    data = ev_load()
    m3 = data["models"]["m3"]
    async with await get_client() as c:
        tools = await c.list_tools()
        names = sorted(t.name for t in tools.tools)
        recovery_like = [
            n
            for n in names
            if any(k in n for k in ("recover", "accept", "clear", "resolve", "reconcile", "rollback"))
        ]
        record("s6", tool_count=len(names), recovery_like_tools=recovery_like)
        blocked_readonly = await call(
            c,
            "creo_execute_plan",
            {"operations": [{"op": "dump_tree"}], "model_id": m3["model_id"]},
        )
        record("s6", readonly_while_pending=blocked_readonly)
        job = await call(c, "creo_get_job", {"job_id": m3["job_id"], "detail": "full"})
        record(
            "s6",
            m3_job_recovery_keys=sorted((job.get("recovery") or {}).keys()),
            m3_recovery_required=job.get("recovery_required"),
            m3_job_status=job.get("status"),
        )
        models = await call(c, "creo_list_models", {"limit": 10})
        record("s6", list_models_snapshot=models)


async def cmd_s6restart() -> None:
    data = ev_load()
    m1 = data["models"]["m1"]
    m2 = data["models"]["m2"]
    # M1 is already in the target state after S5: status=failed, pending cleared,
    # session holding unsaved mutations from the timed-out job. No third timeout
    # is needed; record the pre-restart state as evidence.
    m1_model = model_json(m1["model_id"])
    m2_model = model_json(m2["model_id"])
    record(
        "s6restart",
        m1_pre_restart={
            "status": m1_model.get("status"),
            "pending_job": m1_model.get("pending_job"),
            "revision": m1_model.get("revision"),
        },
        m2_pre_restart={
            "status": m2_model.get("status"),
            "pending_job": m2_model.get("pending_job"),
            "revision": m2_model.get("revision"),
            "part_file": m2_model.get("part_file"),
        },
    )
    ps = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-Process parametric -ErrorAction SilentlyContinue"
            " | Select-Object -First 1 -ExpandProperty Id",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    pid = ps.stdout.strip()
    record("s6restart", creo_pid_before_restart=pid)
    if not pid:
        record("s6restart", restart="no creo process found; abort")
        return
    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, text=True, timeout=30)
    time.sleep(5)
    async with await get_client() as c:
        await ensure_ready(c, "s6restart")
        record("s6restart", restarted=True)
        inject_model_fields(m1["model_id"], pending_job=None, status="ready")
        write1 = await submit_and_record(
            c,
            "s6restart",
            "creo_execute_plan",
            {
                "operations": [{"op": "regenerate"}],
                "model_id": m1["model_id"],
                "expected_revision": m1["revision"],
            },
        )
        r1 = await poll_job(c, write1["job_id"], deadline_s=180)
        record(
            "s6restart",
            m1_after_restart_status=r1["status"],
            m1_after_restart_revision=r1.get("revision"),
            m1_after_restart_message=r1.get("message"),
        )
        inject_model_fields(m2["model_id"], pending_job=None, status="ready")
        write2 = await submit_and_record(
            c,
            "s6restart",
            "creo_execute_plan",
            {
                "operations": [{"op": "regenerate"}],
                "model_id": m2["model_id"],
                "expected_revision": 0,
            },
        )
        r2 = await poll_job(c, write2["job_id"], deadline_s=180)
        record(
            "s6restart",
            m2_after_restart_status=r2["status"],
            m2_after_restart_message=r2.get("message"),
        )


COMMANDS = {
    "identity": cmd_identity,
    "start": cmd_start,
    "s1": cmd_s1,
    "s2": cmd_s2,
    "s3": cmd_s3,
    "s4": cmd_s4,
    "s5": cmd_s5,
    "s6": cmd_s6,
    "s6restart": cmd_s6restart,
}


def main() -> None:
    asyncio.run(COMMANDS[sys.argv[1]]())


if __name__ == "__main__":
    main()
