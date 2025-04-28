#!/usr/bin/env python3
import os
import sys

# **1. Make sure src/ is on PYTHONPATH before any imports**
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import asyncio
import json
import logging

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Now this will resolve to src/momentum/momentum_agent.py
from momentum.momentum_agent import MomentumAgent

logger = logging.getLogger("serve_agent")
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = MomentumAgent()


async def _stream_assist(request: Request) -> StreamingResponse:
    body = await request.json()

    # Frontend sends { query: { prompt } }, but we also accept top-level `prompt`
    prompt = body.get("prompt") or body.get("query", {}).get("prompt", "")

    # `assist` yields an async generator of dicts
    async def event_generator():
        for chunk in agent.assist(prompt, context={}):
            yield json.dumps(chunk) + "\n"

    return StreamingResponse(event_generator(), media_type="application/json")


@app.post("/assist")
async def assist(request: Request):
    return await _stream_assist(request)


if __name__ == "__main__":
    # **2. Add this so `python3 serve_agent.py` actually starts Uvicorn**
    uvicorn.run("serve_agent:app", host="0.0.0.0", port=8080, log_level="info")
