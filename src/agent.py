import asyncio
import logging
import os
from datetime import datetime

import httpx
from dotenv import load_dotenv
from livekit import agents, api, rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    function_tool,
    get_job_context,
    room_io,
)
from google.genai import types
from livekit.plugins import google, silero

logger = logging.getLogger("gemini-telephony-agent")

load_dotenv(".env.local")

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
call_transcript: list[dict] = []
call_start_time: datetime | None = None

async def hangup_call():
    ctx = get_job_context()
    if ctx is None: return
    await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))

async def send_end_of_call_report():
    global call_transcript, call_start_time
    if not call_transcript: return
    call_end_time = datetime.now()
    duration_seconds = (call_end_time - call_start_time).total_seconds() if call_start_time else 0
    report = {
        "call_start": call_start_time.isoformat() if call_start_time else None,
        "call_end": call_end_time.isoformat(),
        "duration_seconds": duration_seconds,
        "transcript": call_transcript,
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(WEBHOOK_URL, json=report, timeout=10.0)
    except Exception as e:
        logger.error(f"Webhook error: {e}")

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="")

    @function_tool
    async def hang_up(self, ctx: RunContext):
        """Telefonu kapatır."""
        await ctx.session.generate_reply(instructions="Say a brief goodbye.")
        await asyncio.sleep(2)
        await hangup_call()

def prewarm(proc: agents.JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    global call_transcript, call_start_time
    call_transcript = []
    call_start_time = datetime.now()
    
    # auto_subscribe=True (varsayılan) zaten herkesi duymasını sağlar.
    await ctx.connect()
    
    logger.info(f"Odaya bağlandı: {ctx.room.name}")

    model = google.realtime.RealtimeModel(
        model="gemini-2.5-flash-native-audio-preview-09-2025",
        voice="Zephyr",
        instructions="""You are a professional assistant at Mars Logistics. 
        You are in a group call with multiple people. Listen to everyone and be helpful.""",
        temperature=0.6,
        thinking_config=types.ThinkingConfig(include_thoughts=False),
    )

    session = AgentSession(llm=model, vad=ctx.proc.userdata["vad"])

    @session.on("conversation_item_added")
    def on_conversation_item(event):
        msg = getattr(event, 'item', event)
        role = getattr(msg, 'role', 'unknown')
        if role in ['user', 'assistant']:
            content = msg.text_content() if hasattr(msg, 'text_content') else ""
            call_transcript.append({"role": role, "content": content})

    # On-prem uyumluluğu için karmaşık ses filtrelerini kaldırdık.
    await session.start(agent=Assistant(), room=ctx.room)
    
    await session.generate_reply(instructions="Greet everyone in the room.")
    ctx.add_shutdown_callback(send_end_of_call_report)

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
