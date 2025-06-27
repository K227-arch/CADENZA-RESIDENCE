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

# Initialize the GenAI client for speech responses
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={'api_version': 'v1alpha'}
)

# Use the model that supports audio output - this is key for speech responses
model = "gemini-2.0-flash-exp"
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],  # This ensures we get audio responses
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

# Add the realtime audio script
@app.get("/realtime_audio.js")
async def get_realtime_audio_js():
    with open("realtime_audio.js", "r") as f:
        return HTMLResponse(content=f.read(), media_type="application/javascript")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint that returns speech responses."""
    await websocket.accept()
    print(f"🔗 WebSocket connected: {websocket.client}")

    async def handle_client_message(data):
        """Handle JSON messages from client."""
        try:
            message = json.loads(data)
            message_type = message.get('type')
            
            if message_type == 'ai_greeting':
                greeting = message.get('message', 'Hello! How can I help you with the Cadenza Residence tour?')
                print(f"👋 Processing greeting for speech: {greeting}")
                
                # Send the greeting to Gemini to get speech response
                await send_text_for_speech_response(session, greeting)
                
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

    async def send_text_for_speech_response(session, text):
        """Send text to Gemini and get speech response."""
        try:
            print(f"📤 Sending text to Gemini for speech: {text}")
            
            # Create a proper content message
            content = types.LiveClientContent(
                turns=[
                    types.Content(
                        parts=[types.Part.from_text(text)],
                        role="user"
                    )
                ],
                turn_complete=True
            )
            
            # Send to Gemini
            await session.send(content)
            print("✅ Text sent to Gemini for speech generation")
            
        except Exception as e:
            print(f"❌ Error sending text for speech: {e}")
            import traceback
            traceback.print_exc()

    async def process_audio_input(audio_data):
        """Process incoming audio and send to Gemini."""
        try:
            print(f"🎤 Processing {len(audio_data)} bytes of audio input")
            
            # Send audio to Gemini for processing
            await session.send(types.LiveClientRealtimeInput(
                audio=types.Blob(
                    data=audio_data, 
                    mime_type="audio/pcm;rate=16000"
                )
            ))
            
        except Exception as e:
            print(f"❌ Error processing audio input: {e}")

    async def handle_gemini_response(session):
        """Handle speech responses from Gemini."""
        try:
            async for response in session.receive():
                print(f"📨 Received response from Gemini")
                
                # Check for server content
                if hasattr(response, 'server_content') and response.server_content:
                    server_content = response.server_content
                    print(f"📋 Server content received")
                    
                    # Handle model turn with audio
                    if hasattr(server_content, 'model_turn') and server_content.model_turn:
                        model_turn = server_content.model_turn
                        print(f"🤖 Model turn with {len(model_turn.parts)} parts")
                        
                        for i, part in enumerate(model_turn.parts):
                            print(f"📦 Processing part {i+1}")
                            
                            # Handle audio data (speech response)
                            if hasattr(part, 'inline_data') and part.inline_data:
                                if hasattr(part.inline_data, 'data') and part.inline_data.data:
                                    audio_data = part.inline_data.data
                                    print(f"🔊 Got speech audio: {len(audio_data)} bytes")
                                    
                                    # Send speech audio to client immediately
                                    await websocket.send_bytes(audio_data)
                                    print("✅ Speech audio sent to client")
                            
                            # Handle text (for debugging)
                            if hasattr(part, 'text') and part.text:
                                print(f"💬 Text part: {part.text}")
                    
                    # Handle turn completion
                    if hasattr(server_content, 'turn_complete') and server_content.turn_complete:
                        await websocket.send_text(json.dumps({
                            'type': 'ai_turn_complete'
                        }))
                        print("✅ AI speech turn completed")
                
                # Handle setup complete
                if hasattr(response, 'setup_complete'):
                    print("🚀 Gemini setup completed")
                
        except Exception as e:
            print(f"❌ Error handling Gemini response: {e}")
            import traceback
            traceback.print_exc()

    # Main WebSocket communication loop
    session = None
    try:
        # Connect to Gemini Live API with speech support
        async with client.aio.live.connect(model=model, config=config) as session:
            print("🚀 Connected to Gemini Live API for speech")
            
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
                        await process_audio_input(audio_data)
                        
                    except asyncio.TimeoutError:
                        # No data received, continue loop
                        await asyncio.sleep(0.001)
                        
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
        import traceback
        traceback.print_exc()
    finally:
        print("🔚 WebSocket session ended")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8083)