"""Run POC3 whitespace pipeline with console progress (sequential agents)."""

from __future__ import annotations

import asyncio
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


async def _main() -> None:
    from app.modules.whitespace.whitespace_orchestrator import run_whitespace_pipeline

    result = await run_whitespace_pipeline(console=True)
    print(json.dumps(result, indent=2, default=str)[:4000])
    if len(json.dumps(result, default=str)) > 4000:
        print("... (truncated)")


if __name__ == "__main__":
    asyncio.run(_main())
