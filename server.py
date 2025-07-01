import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from livekit import api

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="LiveKit Token Server",
    description="Generates LiveKit Access Tokens for frontend applications.",
    version="1.0.0",
)

# Configure CORS (Cross-Origin Resource Sharing)
# This is crucial for your frontend (e.g., from 3DVista or localhost:3000)
# to be able to make requests to this server.
# In production, replace "*" with the specific origin(s) of your frontend.
origins = [
    "http://localhost",
    "http://localhost:3000", # If your React frontend runs on 3000
    "http://127.0.0.1:3000",
    # Add the domain(s) where your 3DVista tour will be hosted, e.g.:
    # "https://your-3dvista-tour-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
import asyncio
import io
import os
import json
import base64
import load_dotenv
import numpy as np

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles



# --- Configuration ---
load_dotenv.load_dotenv()


# --- Serve Static Files ---
app.mount("/loading", StaticFiles(directory="loading"), name="loading")
app.mount("/media", StaticFiles(directory="media"), name="media")
app.mount("/misc", StaticFiles(directory="misc"), name="misc")
app.mount("/fonts", StaticFiles(directory="fonts"), name="fonts")
app.mount("/lib", StaticFiles(directory="lib"), name="lib")
app.mount("/skin", StaticFiles(directory="skin"), name="skin")
app.mount("/locale", StaticFiles(directory="locale"), name="locale")

@app.get("/")
async def get():
    return HTMLResponse(content=open("index.htm").read(), status_code=200)

@app.get("/manifest.json")
async def get_manifest():
    with open("manifest.json", "r") as f:
        return json.loads(f.read())

@app.get("/fonts.css")
async def get_fonts_css():
    with open("fonts.css", "r") as f:
        return HTMLResponse(content=f.read(), media_type="text/css")

@app.get("/script.js")
async def get_script_js():
    with open("script.js", "r") as f:
        return HTMLResponse(content=f.read(), media_type="application/javascript")

@app.get("/script_general.js")
async def get_script_general_js():
    with open("script_general.js", "r") as f:
        return HTMLResponse(content=f.read(), media_type="application/javascript")

@app.get("/scorm.js")
async def get_scorm_js():
    with open("scorm.js", "r") as f:
        return HTMLResponse(content=f.read(), media_type="application/javascript")

@app.get("/favicon.ico")
async def get_favicon():
    with open("favicon.ico", "rb") as f:
        return HTMLResponse(content=f.read(), media_type="image/x-icon")

# Retrieve LiveKit credentials from environment variables
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.getenv("LIVEKIT_URL") # e.g., wss://your.livekit.cloud

# Basic validation for environment variables
if not all([LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL]):
    raise ValueError(
        "LIVEKIT_API_KEY, LIVEKIT_API_SECRET, and LIVEKIT_URL "
        "must be set in the .env file for the token server."
    )

# Pydantic model for request body validation
class TokenRequest(BaseModel):
    roomName: str
    participantName: str

@app.post("/get-token")
async def get_token(request_data: TokenRequest):
    """
    Generates a LiveKit Access Token for a given room and participant.
    """
    room_name = request_data.roomName
    participant_name = request_data.participantName

    # Create an AccessToken instance
    # The identity is a unique identifier for the participant in the room
    # The ttl (time-to-live) sets how long the token is valid (e.g., 6 hours)
    at = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)

    # Set identity and ttl as properties after initialization
    at.identity = participant_name
    # 6 hours in seconds
    
    # Grant permissions to the participant
    at.with_grants(api.VideoGrants(
        room_join=True,       # Allow joining the room
        room=room_name,       # Specify the room to join
        can_publish=True,     # Allow publishing tracks (e.g., microphone)
        can_subscribe=True,   # Allow subscribing to tracks (e.g., agent's audio)
    ))

    # Generate the JWT token
    token = at.to_jwt()

    return {"token": token, "url": LIVEKIT_URL}

# You can run this server using Uvicorn:
# pip install uvicorn
# uvicorn token_server:app --host 0.0.0.0 --port 8080 --reload
# (Assuming this file is named token_server.py)

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting SPEECH-enabled Gemini server with OFFICIAL API...")
    print("📍 Access at: http://localhost:8080")
    print("🔊 This server uses the CORRECT Live API implementation!")
    print("🎵 Voice: Aoede (you can change this in the config)")
    uvicorn.run(app, host="0.0.0.0", port=8080)