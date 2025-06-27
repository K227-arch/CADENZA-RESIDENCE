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

from google import genai
from google.genai import types

# --- Configuration ---
load_dotenv.load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

# Initialize the GenAI client for real-time streaming
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={'api_version': 'v1alpha'}
)

# Use the free model that supports real-time audio
model = "gemini-2.0-flash-exp"
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    system_instruction="You are a helpful AI assistant for the Cadenza Residence virtual tour. Respond naturally and conversationally in a friendly tone. Keep responses concise and engaging."
)

# Initialize FastAPI app
app = FastAPI()

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
    """Serves the index.html page."""
    return HTMLResponse(content=open("index.htm").read(), status_code=200)

@app.get("/manifest.json")
async def get_manifest():
    """Serves the manifest.json file."""
    with open("manifest.json", "r") as f:
        return json.loads(f.read())

@app.get("/fonts.css")
async def get_fonts_css():
    """Serves the fonts.css file."""
    with open("fonts.css", "r") as f:
        return HTMLResponse(content=f.read(), media_type="text/css")

@app.get("/script.js")
async def get_script_js():
    """Serves the script.js file."""
    with open("script.js", "r") as f:
        return HTMLResponse(content=f.read(), media_type="application/javascript")

@app.get("/script_general.js")
async def get_script_general_js():
    """Serves the script_general.js file."""
    with open("script_general.js", "r") as f:
        return HTMLResponse(content=f.read(), media_type="application/javascript")

@app.get("/scorm.js")
async def get_scorm_js():
    """Serves the scorm.js file."""
    with open("scorm.js", "r") as f:
        return HTMLResponse(content=f.read(), media_type="application/javascript")

@app.get("/favicon.ico")
async def get_favicon():
    """Serves the favicon.ico file."""
    with open("favicon.ico", "rb") as f:
        return HTMLResponse(content=f.read(), media_type="image/x-icon")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time WebSocket endpoint for Gemini Live API."""
    await websocket.accept()
    print(f"🔗 WebSocket connected: {websocket.client}")

    # Real-time audio processing variables
    audio_buffer = bytearray()
    is_speaking = False
    silence_counter = 0
    SILENCE_THRESHOLD = 10  # Frames of silence before stopping
    CHUNK_SIZE = 1024  # Smaller chunks for lower latency

    async def handle_client_message(data):
        """Handle JSON messages from client."""
        try:
            message = json.loads(data)
            message_type = message.get('type')
            
            if message_type == 'ai_greeting':
                greeting = message.get('message', 'Hello! How can I help you with the Cadenza Residence tour?')
                print(f"👋 Sending greeting: {greeting}")
                
                # Send immediate text response
                await websocket.send_text(json.dumps({
                    'type': 'greeting_complete',
                    'message': greeting
                }))
                
            elif message_type == 'start_realtime_voice':
                print("🎤 Started real-time voice mode")
                await websocket.send_text(json.dumps({
                    'type': 'voice_status',
                    'status': 'listening'
                }))
                
            elif message_type == 'stop_realtime_voice':
                print("🔇 Stopped real-time voice mode")
                await websocket.send_text(json.dumps({
                    'type': 'voice_status',
                    'status': 'stopped'
                }))
                
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON: {data}")

    async def process_audio_chunk(audio_data):
        """Process incoming audio in real-time."""
        nonlocal audio_buffer, is_speaking, silence_counter
        
        # Convert to numpy array for processing
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Simple voice activity detection
        audio_level = np.abs(audio_array).mean()
        voice_threshold = 500  # Adjust based on testing
        
        if audio_level > voice_threshold:
            is_speaking = True
            silence_counter = 0
            audio_buffer.extend(audio_data)
        else:
            silence_counter += 1
            if is_speaking and silence_counter > SILENCE_THRESHOLD:
                # End of speech detected, process the buffer
                if len(audio_buffer) > 0:
                    return bytes(audio_buffer)
                audio_buffer.clear()
                is_speaking = False
        
        return None

    async def stream_to_gemini(session, audio_data):
        """Stream audio to Gemini in real-time."""
        try:
            # Send audio immediately without buffering
            await session.send(types.LiveClientRealtimeInput(
                audio=types.Blob(
                    data=audio_data, 
                    mime_type="audio/pcm;rate=16000;channels=1"
                )
            ))
            print(f"🎵 Sent {len(audio_data)} bytes to Gemini")
        except Exception as e:
            print(f"❌ Error sending to Gemini: {e}")

    async def handle_gemini_response(session):
        """Handle real-time responses from Gemini."""
        try:
            async for response in session.receive():
                print(f"📨 Received response type: {type(response)}")
                
                # Handle different response types
                if hasattr(response, 'server_content') and response.server_content:
                    server_content = response.server_content
                    
                    # Handle audio responses
                    if hasattr(server_content, 'model_turn') and server_content.model_turn:
                        model_turn = server_content.model_turn
                        for part in model_turn.parts:
                            if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                                audio_data = part.inline_data.data
                                print(f"🔊 Streaming {len(audio_data)} bytes of audio")
                                
                                # Stream audio immediately to client
                                await websocket.send_bytes(audio_data)
                    
                    # Handle text responses (for debugging)
                    if hasattr(server_content, 'model_turn') and server_content.model_turn:
                        for part in server_content.model_turn.parts:
                            if hasattr(part, 'text') and part.text:
                                print(f"💬 Text response: {part.text}")
                    
                    # Handle turn completion
                    if hasattr(server_content, 'turn_complete') and server_content.turn_complete:
                        await websocket.send_text(json.dumps({
                            'type': 'ai_turn_complete'
                        }))
                        print("✅ AI turn completed")
                
        except Exception as e:
            print(f"❌ Error handling Gemini response: {e}")

    # Main WebSocket communication loop
    try:
        # Connect to Gemini Live API
        async with client.aio.live.connect(model=model, config=config) as session:
            print("🚀 Connected to Gemini Live API")
            
            # Start response handler
            response_task = asyncio.create_task(handle_gemini_response(session))
            
            # Main message loop
            while True:
                try:
                    # Try to receive text message first
                    try:
                        message = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                        await handle_client_message(message)
                        continue
                    except asyncio.TimeoutError:
                        pass
                    
                    # Try to receive binary audio data
                    try:
                        audio_data = await asyncio.wait_for(websocket.receive_bytes(), timeout=0.01)
                        print(f"🎤 Received {len(audio_data)} bytes of audio")
                        
                        # Process audio in real-time
                        processed_audio = await process_audio_chunk(audio_data)
                        if processed_audio:
                            await stream_to_gemini(session, processed_audio)
                        else:
                            # Stream small chunks immediately for real-time response
                            if len(audio_data) >= CHUNK_SIZE:
                                await stream_to_gemini(session, audio_data)
                        
                    except asyncio.TimeoutError:
                        # No data received, continue loop
                        await asyncio.sleep(0.001)  # Very small sleep to prevent busy waiting
                        
                except WebSocketDisconnect:
                    print("🔌 Client disconnected")
                    break
                except Exception as e:
                    print(f"❌ Error in main loop: {e}")
                    break
            
            # Cleanup
            response_task.cancel()
            try:
                await response_task
            except asyncio.CancelledError:
                pass
                
    except Exception as e:
        print(f"❌ Error in WebSocket handler: {e}")
    finally:
        print("🔚 WebSocket session ended")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)