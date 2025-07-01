# LiveKit Voice AI Assistant
This project implements a real-time voice AI assistant using LiveKit for WebRTC communication, a Python backend powered by LiveKit Agents and Google's Gemini LLM, and a React (Next.js) frontend for user interaction.
## installation
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
#### ubuntu setup
curl -sSL https://get.livekit.io | bash
sudo apt install libportaudio2
#### livekit setup
livekit-server --dev
#### livekit agent
python main.py
#### livekit token server
python server.py
#### ngrok port forwarding 
ngrok http 8080
#### frontend setup
launched with the server.py script
## Table of Contents
- [Features](#-features)
- [Architecture](#️-architecture)
- [Prerequisites](#-prerequisites)
- [Setup and Running](#-setup-and-running)
- [Usage](#-usage)
- [Troubleshooting](#-troubleshooting)

# ✨ Features
Real-time Voice Interaction: Seamless bidirectional audio communication between the user and the AI.

Google Gemini Integration: Utilizes Google's Gemini models (e.g., gemini-2.5-flash-live) for powerful language understanding and generation.

Speech-to-Text (STT): Transcribes user speech into text in real-time.

Text-to-Speech (TTS): Synthesizes AI responses into natural-sounding speech.

Noise Cancellation: (Optional) Integrates noise cancellation for clearer audio input.

Responsive Frontend: A web-based interface built with React and LiveKit Components for an intuitive user experience.

# 🏛️ Architecture
The project consists of four main components that work together:

**LiveKit Server:** The central WebRTC media server (can be LiveKit Cloud or self-hosted) that handles real-time audio/video routing and signaling.

**Python Agent (Backend):**
- Connects to the LiveKit Server as a participant.
- Uses `livekit-plugins-google` to interact with the Gemini API for LLM, STT, and TTS.
- Subscribes to user audio from the LiveKit room and publishes AI-generated audio back.

**Token Server (Backend):**
- A small Node.js (or Python/Go) server that provides secure access tokens for the frontend to connect to the LiveKit Server. This keeps your LiveKit API Secret secure.

**React Frontend (Web):**
- Connects to the LiveKit Server using the `livekit-client` and `@livekit/components-react` SDKs.
- Obtains an access token from the Token Server.
- Captures user microphone input and sends it to the LiveKit Server.
- Plays back the AI agent's audio output.

```mermaid
graph TD
    User_Mic[User Microphone] -->|Audio Stream| Frontend(React Frontend)
    Frontend -->|WebRTC (Audio Track)| LiveKit_Server[LiveKit Server]
    LiveKit_Server -->|WebRTC (Audio Track)| Python_Agent[Python Agent]

    Python_Agent -->|STT| Gemini_API[Google Gemini API]
    Gemini_API -->|LLM Response| Python_Agent
    Python_Agent -->|TTS| Gemini_API
    Gemini_API -->|Synthesized Audio| Python_Agent

    Python_Agent -->|WebRTC (Audio Track)| LiveKit_Server
    LiveKit_Server -->|WebRTC (Audio Track)| Frontend
    Frontend -->|Audio Playback| User_Speakers[User Speakers/Headphones]

    Frontend -- Request Access Token --> Token_Server[Token Server]
    Token_Server -- Generates JWT with API Key/Secret --> LiveKit_Server_Auth[LiveKit Server (Authentication)]
    LiveKit_Server_Auth --> Token_Server
    Token_Server -->|Returns Token| Frontend
```

📋 Prerequisites

Before you begin, ensure you have the following installed:Node.js (LTS version recommended) & npm or pnpm (for the frontend and token server)Python 3.9+ (for the AI agent)LiveKit Server:LiveKit Cloud Account: (Recommended for ease of use) Sign up at livekit.io. You'll need your LiveKit URL, API Key, and API Secret from your project settings.Self-hosted LiveKit Server: If you prefer to self-host, follow the LiveKit self-hosting guide.Google Gemini API Key:Go to Google AI Studio.Create a new API key. This key will be used by your Python agent to access Gemini models. Ensure the "Generative Language API" is enabled for your Google Cloud project.🚀 Setup and RunningFollow these steps to set up and run each component of the project.1. Python AI Agent SetupClone this repository (or create the necessary files if you're building from scratch):git clone https://github.com/your-repo/your-voice-ai-agent.git # Replace with your actual repo
cd your-voice-ai-agent/python-agent # Navigate to your agent's directory

Create and activate a Python virtual environment:python3 -m venv venv
source venv/bin/activate # On Windows: .\venv\Scripts\activate

Install Python dependencies:pip install livekit-agents livekit-plugins-google python-dotenv sounddevice

Create a .env file in your python-agent directory and add your Google Gemini API key:GEMINI_API_KEY=your_google_gemini_api_key

Update your Python agent code (your_agent_script.py):Ensure your agent's code specifies the correct sounddevice IDs for your microphone input and AirPods output.import sounddevice as sd
import os
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import google, noise_cancellation
from livekit.agents import UserInputTranscribedEvent, AgentState # For debugging

load_dotenv()

# --- Configure Sounddevice (Crucial for audio I/O) ---
# List devices to find correct IDs: python -c "import sounddevice as sd; print(sd.query_devices())"
INPUT_DEVICE_ID = 10 # Replace with your webcam's input ID (e.g., HP ENVY USB Webcam: (2 in, 0 out))
OUTPUT_DEVICE_ID = 13 # Replace with your AirPods' output ID (e.g., pulse: (0 in, 32 out) or specific AirPods entry)

sd.default.input_device = INPUT_DEVICE_ID
sd.default.output_device = OUTPUT_DEVICE_ID
print(f"Sounddevice configured - Input: {sd.default.input_device}, Output: {sd.default.output_device}")
# You can also set sample rate and block size if needed, but often not required if system defaults work
# sd.default.samplerate = 48000
# sd.default.blocksize = 1024
# --- End Sounddevice Configuration ---

# Your LiveKit Server URL and API Keys (from LiveKit Cloud or self-hosted)
# These are used by the agent to connect to the LiveKit server
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
    print("Error: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET must be set in the .env file for the agent.")
    exit(1)

session_google = AgentSession(
    llm=google.beta.realtime.RealtimeModel(
        model="gemini-live-2.5-flash-preview", # Or "gemini-2.5-flash-preview-native-audio-dialog"
        voice="Puck", # Choose a voice (e.g., "Puck", "Charon", "Fable")
        temperature=0.8,
        instructions="You are a helpful assistant",
        api_key=os.getenv("GEMINI_API_KEY"),
    ),
)

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful voice AI assistant.")

async def entrypoint(ctx: agents.JobContext):
    # Set agent's LiveKit credentials
    ctx.room.set_livekit_url(LIVEKIT_URL)
    ctx.room.set_api_key(LIVEKIT_API_KEY)
    ctx.room.set_api_secret(LIVEKIT_API_SECRET)

    session = session_google

    # --- Debugging Event Listeners ---
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event: UserInputTranscribedEvent):
        print(f"DEBUG: User transcribed: '{event.transcript}', final: {event.is_final}")
        # Optionally, publish transcription back to the room as data for frontend display
        if event.is_final:
            ctx.room.local_participant.publish_data(
                json.dumps({"type": "transcription", "text": event.transcript}),
                agents.rtc.DataPacket_Kind.RELIABLE,
            )

    @session.on("agent_state_changed")
    def on_agent_state_changed(old_state: AgentState, new_state: AgentState):
        print(f"DEBUG: Agent state changed from {old_state} to {new_state}")
    # --- End Debugging Event Listeners ---

    await ctx.connect() # Connects the agent to the LiveKit room

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(), # Keep or comment out for testing
        ),
    )

    # Initial greeting from the agent
    await session.generate_reply(
        instructions="Greet the user warmly and offer your assistance. Ask them how you can help today."
    )

if __name__ == "__main__":
    # Add LiveKit server credentials to agent's .env
    # LIVEKIT_URL=wss://your.livekit.cloud
    # LIVEKIT_API_KEY=LK_xxxxxx
    # LIVEKIT_API_SECRET=your_livekit_secret
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))

Important: Add your LiveKit URL, API Key, and API Secret to the Python agent's .env file as well:LIVEKIT_URL=wss://your.livekit.cloud
LIVEKIT_API_KEY=LK_xxxxxxxx
LIVEKIT_API_SECRET=your_livekit_secret_xxxxxxxx

Run the Python Agent:python your_agent_script.py # Or whatever your agent file is named

Keep an eye on the terminal for debug messages and any errors.2. Token Server Setup (Node.js Example)This server generates the access tokens required by your frontend.Create a new directory for your token server:mkdir token-server
cd token-server

Initialize a Node.js project and install dependencies:npm init -y
npm install express cors dotenv livekit-server-sdk

Create an index.js file (or app.js) with the following content:// token-server/index.js
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { AccessToken } = require('livekit-server-sdk');

const app = express();
app.use(cors()); // Enable CORS for frontend requests
app.use(express.json());

const LIVEKIT_API_KEY = process.env.LIVEKIT_API_KEY;
const LIVEKIT_API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL; // Your LiveKit server URL

if (!LIVEKIT_API_KEY || !LIVEKIT_API_SECRET || !LIVEKIT_URL) {
    console.error('LIVEKIT_API_KEY, LIVEKIT_API_SECRET, and LIVEKIT_URL must be set in .env');
    process.exit(1);
}

app.post('/get-token', (req, res) => {
    const { roomName, participantName } = req.body;

    if (!roomName || !participantName) {
        return res.status(400).send('roomName and participantName are required');
    }

    const at = new AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, {
        identity: participantName,
        ttl: 6 * 60 * 60, // Token valid for 6 hours
    });
    at.addGrant({ roomJoin: true, room: roomName, canPublish: true, canSubscribe: true });

    const token = at.toJwt();
    res.json({ token, url: LIVEKIT_URL }); // Send back the token and LiveKit URL
});

const port = process.env.PORT || 8080;
app.listen(port, () => {
    console.log(`Token server listening on port ${port}`);
});

Create a .env file in your token-server directory and add your LiveKit credentials:LIVEKIT_API_KEY=LK_xxxxxxxx
LIVEKIT_API_SECRET=your_livekit_secret_xxxxxxxx
LIVEKIT_URL=wss://your.livekit.cloud
PORT=8080

Run the Token Server:node index.js

This server will run on http://localhost:8080 by default.3. React Frontend SetupWe'll use the official LiveKit agent-starter-react template as a base, as it's optimized for this use case.Clone the LiveKit agent-starter-react template:git clone https://github.com/livekit-examples/agent-starter-react.git
cd agent-starter-react

Install Node.js dependencies:pnpm install # Or npm install / yarn install

Create a .env.local file in the root of the agent-starter-react directory.Crucially, this frontend will call your Token Server to get the LiveKit URL and Token. So, you only need to tell the frontend where your Token Server is.Note: The agent-starter-react template might have its own LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET in its .env.example. You can remove these from .env.local as the token server will provide them.# .env.local (for the frontend)
NEXT_PUBLIC_TOKEN_SERVER_URL=http://localhost:8080/get-token # Adjust if your token server is on a different port/host
NEXT_PUBLIC_LIVEKIT_ROOM_NAME=your-agent-room # Make sure this matches the room your Python agent joins
NEXT_PUBLIC_PARTICIPANT_PREFIX=web-user- # Prefix for frontend participants

Modify the frontend to fetch the token from your token server:The agent-starter-react template likely has a lib/client-utils.ts or similar file that handles token fetching. You'll need to modify it to point to your NEXT_PUBLIC_TOKEN_SERVER_URL.Locate the token fetching logic (e.g., in app/page.tsx or a custom hook like useLiveKitToken). It might look something like this:// Inside a component or hook that fetches the token
const fetchToken = async (roomName: string, participantName: string) => {
    const tokenServerUrl = process.env.NEXT_PUBLIC_TOKEN_SERVER_URL;
    if (!tokenServerUrl) {
        console.error("NEXT_PUBLIC_TOKEN_SERVER_URL is not set.");
        return null;
    }
    try {
        const response = await fetch(tokenServerUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ roomName, participantName }),
        });
        const data = await response.json();
        return { token: data.token, livekitUrl: data.url };
    } catch (error) {
        console.error('Error fetching token:', error);
        return null;
    }
};

Ensure the LiveKitRoom component in app/page.tsx or similar is using this fetched token and URL. The agent-starter-react template usually handles this well with its useVoiceAssistant hook.Run the React Frontend:pnpm dev # Or npm run dev / yarn dev

Open your browser to http://localhost:3000 (or whatever port Next.js starts on).💡 UsageEnsure all three components are running:LiveKit Server (Cloud or self-hosted)Python AI AgentNode.js Token ServerReact FrontendOpen your frontend in the browser.Grant microphone permission when prompted by the browser.You should hear the initial greeting from your AI agent.Speak clearly into your microphone. The agent should transcribe your speech, process it, and reply. You should see debug logs in your Python agent's terminal showing transcription and state changes.⚠️ TroubleshootingNo Audio Output from AI:Double-check sd.default.output_device in your Python agent. Use python -c "import sounddevice as sd; print(sd.query_devices())" to find the correct ID for your AirPods' output.Ensure your AirPods are set to "A2DP Sink" profile in pavucontrol (Linux).Check browser console for "autoplay blocked" messages. You might need to click a "Start Audio" button in the UI if one is provided by the LiveKit Components.AI doesn't respond after you speak:Check Python agent logs: Look for DEBUG: User transcribed: messages. If they don't appear or show incorrect transcriptions, the STT or VAD is the issue.VAD Sensitivity: Speak clearly with natural pauses. If you talk too fast or too slowly, the VAD might not detect turns correctly.Gemini API Key: Ensure your GEMINI_API_KEY is correct and has access to the gemini-live-2.5-flash-preview model. Check your Google Cloud API usage.Network Issues: Ensure your Python agent has a stable internet connection to reach the Gemini API and LiveKit Server.Frontend cannot connect to LiveKit:Verify NEXT_PUBLIC_TOKEN_SERVER_URL in your frontend's .env.local matches your running token server.Check your token server's terminal for errors or successful token generation.Ensure your LiveKit Server URL (LIVEKIT_URL) in the token server's .env is correct.Check browser developer console for network errors (e.g., failed WebSocket connections, CORS issues).CORS Errors: Ensure your token server has app.use(cors()); configured correctly to allow requests from your frontend's origin (http://localhost:3000).🤝 ContributingContributions are welcome! Please feel free to open issues or pull requests.📄 LicenseThis project is licensed under the Apache 2.0 License.