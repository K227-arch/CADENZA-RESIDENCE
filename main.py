from livekit.plugins import google
from dotenv import load_dotenv
import os
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    noise_cancellation,
)
import sounddevice as sd
load_dotenv()
LIVEKIT_ROOM_NAME = os.getenv("LIVEKIT_ROOM_NAME", "cadenza-residence-ai-chat") # Define your room name here

sd.default.device = 10 # Still targeting pulse
# A common block size (can experiment with 512, 2048)
print(f"Sounddevice set to use device ID: {sd.default.device}, Sample Rate: {sd.default.samplerate}, Block Size: {sd.default.blocksize}")
# Create a session with Google Gemini
session_google = AgentSession(
    llm=google.beta.realtime.RealtimeModel(
        model="gemini-live-2.5-flash-preview",
        voice="Puck",
        temperature=0.8,
        instructions="You are a helpful assistant",
        api_key=os.getenv("GEMINI_API_KEY"),
        modalities=["AUDIO"],
    ),
)





class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful voice AI assistant.")


async def entrypoint(ctx: agents.JobContext):
    session = session_google

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            # LiveKit Cloud enhanced noise cancellation
            # - If self-hosting, omit this parameter
            # - For telephony applications, use `BVCTelephony` for best results
         #  noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()

    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))