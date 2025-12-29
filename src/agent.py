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
from livekit.plugins import google, noise_cancellation, silero

logger = logging.getLogger("gemini-telephony-agent")

load_dotenv(".env.local")

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

call_transcript: list[dict] = []
call_start_time: datetime | None = None

async def hangup_call():
    ctx = get_job_context()
    if ctx is None:
        return
    await ctx.api.room.delete_room(
        api.DeleteRoomRequest(room=ctx.room.name)
    )

async def send_end_of_call_report():
    global call_transcript, call_start_time
    if not call_transcript:
        logger.info("No transcript to send (shutdown callback)")
        return
    call_end_time = datetime.now()
    duration_seconds = (call_end_time - call_start_time).total_seconds() if call_start_time else 0
    report = {
        "call_start": call_start_time.isoformat() if call_start_time else None,
        "call_end": call_end_time.isoformat(),
        "duration_seconds": duration_seconds,
        "transcript": call_transcript,
        "message_count": len(call_transcript),
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(WEBHOOK_URL, json=report, timeout=10.0)
            logger.info(f"End-of-call report sent (shutdown): {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send end-of-call report: {e}")
    call_transcript = []
    call_start_time = None

async def send_end_of_call_report_from_session(session: AgentSession):
    global call_start_time, call_transcript
    call_end_time = datetime.now()
    duration_seconds = (call_end_time - call_start_time).total_seconds() if call_start_time else 0
    transcript = []
    try:
        if hasattr(session, 'chat_ctx') and session.chat_ctx:
            for msg in session.chat_ctx.messages:
                content = msg.text_content() if hasattr(msg, 'text_content') else str(msg.content)
                transcript.append({
                    "role": msg.role,
                    "content": content,
                })
    except Exception as e:
        logger.error(f"Failed to extract chat context: {e}")
    if not transcript and call_transcript:
        transcript = call_transcript
    if not transcript:
        return
    report = {
        "call_start": call_start_time.isoformat() if call_start_time else None,
        "call_end": call_end_time.isoformat(),
        "duration_seconds": duration_seconds,
        "transcript": transcript,
        "message_count": len(transcript),
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(WEBHOOK_URL, json=report, timeout=10.0)
            logger.info(f"End-of-call report sent: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send end-of-call report: {e}")

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="")

    @function_tool
    async def hang_up(self, ctx: RunContext):
        """Hang up the phone call."""
        await send_end_of_call_report_from_session(ctx.session)
        await ctx.session.generate_reply(
            instructions="Say a brief, warm goodbye like 'Goodbye! Have a great day!'"
        )
        await asyncio.sleep(2)
        await hangup_call()

def prewarm(proc: agents.JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    global call_transcript, call_start_time
    call_transcript = []
    call_start_time = datetime.now()
    await ctx.connect()
    logger.info(f"Call started - Room: {ctx.room.name}")

    model = google.realtime.RealtimeModel(
        model="gemini-2.5-flash-native-audio-preview-09-2025",
        voice="Zephyr",
        instructions="""You are playful and on a phone call. Keep the responses short (under 60 words).""",
        temperature=0.6,
        thinking_config=types.ThinkingConfig(include_thoughts=False),
    )

    session = AgentSession(llm=model, vad=ctx.proc.userdata["vad"])

    @session.on("conversation_item_added")
    def on_conversation_item(event):
        msg = getattr(event, 'item', event)
        role = getattr(msg, 'role', 'unknown')
        content = ""
        if hasattr(msg, 'text_content') and callable(msg.text_content):
            content = msg.text_content()
        elif hasattr(msg, 'content'):
            content = str(msg.content[0]) if isinstance(msg.content, list) else str(msg.content)
        
        if role in ['user', 'assistant']:
            call_transcript.append({"role": role, "content": content})

    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )
    await session.generate_reply(instructions="Answer the phone warmly.")
    ctx.add_shutdown_callback(send_end_of_call_report)

if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            # agent_name kaldırıldı -> Bu worker her türlü görevi kabul eder.
        )
    )
