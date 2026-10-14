"""Wait for public MCP readiness before developer integration mutations."""

from __future__ import annotations

import asyncio
import json
import math
import time
from pathlib import Path

from mcp import Client


async def wait_for_startup(client: Client, report: dict, output: Path, budget: float = 130) -> dict:
    if not math.isfinite(budget) or budget <= 0:
        raise ValueError("Readiness observation budget must be finite and positive")
    deadline = time.monotonic() + budget
    while True:
        response = await client.call_tool("creo_startup_status", {})
        status = response.structured_content
        report.setdefault("startup_queries", []).append(status)
        report["startup"] = status
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if response.is_error or not isinstance(status, dict):
            raise RuntimeError(f"MCP readiness query failed: {response}")
        if status.get("state") == "ready" and status.get("connected") is True:
            return status
        if status.get("state") not in {
            "checking",
            "building_worker",
            "starting",
            "waiting_for_connection",
        }:
            raise RuntimeError(f"Toolkit is not ready; no modeling request submitted: {status}")
        if time.monotonic() >= deadline:
            raise TimeoutError("Toolkit readiness observation ended; no modeling request submitted")
        await asyncio.sleep(1)
