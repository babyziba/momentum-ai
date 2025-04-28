
import os
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import AsyncGenerator


from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import json
from typing import AsyncGenerator

from memeradar_agent.memeradar_agent import MemeRadarAgent

class AgentServer:
    def __init__(self, agent: MemeRadarAgent):
        self.agent = agent
        self.app = FastAPI()

        # Allow React dev server
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @self.app.post("/assist")
        async def assist(request: Request) -> StreamingResponse:
            payload = await request.json()
            prompt = payload.get("query", {}).get("prompt", "")
            session = payload.get("session", {})

            async def event_stream() -> AsyncGenerator[str, None]:
                try:
                    for i, chunk in enumerate(
                        self.agent.assist(input_text=prompt, context=session)
                    ):
                        # only one welcome when prompt is empty
                        if prompt == "" and i > 0:
                            break

                        # slight pacing
                        await asyncio.sleep(0.01)
                        yield f"event: FINAL_RESPONSE\ndata: {json.dumps(chunk)}\n\n"

                except Exception as e:
                    err = {"text": f"❌ Server error: {e}"}
                    yield f"event: FINAL_RESPONSE\ndata: {json.dumps(err)}\n\n"

                # done
                yield f"event: done\ndata: {json.dumps({'message':'complete'})}\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache"},
            )

    def run(self):
        uvicorn.run(self.app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
