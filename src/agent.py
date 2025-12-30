import asyncio
import logging
from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, AgentSession, room_io, Agent
from google.genai import types
from livekit.plugins import google, silero

logger = logging.getLogger("gemini-agent")

# Boş bir Assistant sınıfı tanımlıyoruz (SDK bunu zorunlu tutar)
class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful assistant. Keep it brief.")

def prewarm(proc: agents.JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    logger.info(f"Bağlantı başarılı: {ctx.room.name}")

    model = google.realtime.RealtimeModel(
        model="gemini-2.5-flash-native-audio-preview-09-2025",
        voice="Zephyr",
        instructions="You are a helpful assistant. Keep it brief.",
        temperature=0.6,
        thinking_config=types.ThinkingConfig(include_thoughts=False),
    )

    session = AgentSession(llm=model, vad=ctx.proc.userdata["vad"])
    
    # HATA BURADAYDI: 'agent' argümanını ekleyerek başlatıyoruz
    await session.start(room=ctx.room, agent=Assistant())
    
    await session.generate_reply(instructions="Hello! I am connected and ready to help.")

if __name__ == "__main__":
    agents.cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
