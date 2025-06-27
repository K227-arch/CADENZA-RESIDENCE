import asyncio
import os
import json
import load_dotenv

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

# Use the free model that supports audio output
model = "gemini-2.0-flash-exp"
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],  # This ensures we get speech responses
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint that returns SPEECH responses from Gemini."""
    await websocket.accept()
    print(f"🔗 WebSocket connected: {websocket.client}")

    # Connect to Gemini Live API with speech support
    try:
        async with client.aio.live.connect(model=model, config=config) as session:
            print("🚀 Connected to Gemini Live API for SPEECH")
            
            async def handle_gemini_responses():
                """Handle speech responses from Gemini."""
                try:
                    async for response in session.receive():
                        print(f"📨 Received response: {type(response)}")
                        
                        # Handle server content with audio
                        if hasattr(response, 'server_content') and response.server_content:
                            server_content = response.server_content
                            
                            # Handle model turn with speech audio
                            if hasattr(server_content, 'model_turn') and server_content.model_turn:
                                model_turn = server_content.model_turn
                                
                                for part in model_turn.parts:
                                    # Handle speech audio data
                                    if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                                        audio_data = part.inline_data.data
                                        print(f"🔊 SPEECH AUDIO: {len(audio_data)} bytes")
                                        
                                        # Send speech audio to client
                                        await websocket.send_bytes(audio_data)
                                        print("✅ Speech sent to client!")
                                    
                                    # Also log any text for debugging
                                    if hasattr(part, 'text') and part.text:
                                        print(f"💬 Text: {part.text}")
                            
                            # Handle turn completion
                            if hasattr(server_content, 'turn_complete') and server_content.turn_complete:
                                await websocket.send_text(json.dumps({
                                    'type': 'speech_complete'
                                }))
                                print("✅ Speech turn completed")
                        
                        # Handle setup completion
                        if hasattr(response, 'setup_complete'):
                            print("🚀 Gemini setup completed - ready for speech!")
                            
                            # Send initial greeting for speech
                            greeting_text = "Hello! I'm your AI assistant for the Cadenza Residence virtual tour. How can I help you today?"
                            print(f"👋 Sending greeting for speech: {greeting_text}")
                            
                            # Send text to get speech response
                            await session.send(greeting_text)
                            
                except Exception as e:
                    print(f"❌ Error in speech handler: {e}")
                    import traceback
                    traceback.print_exc()

            # Start response handler
            response_task = asyncio.create_task(handle_gemini_responses())
            
            # Main message loop
            while True:
                try:
                    # Handle text messages
                    try:
                        message = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                        data = json.loads(message)
                        message_type = data.get('type')
                        
                        if message_type == 'ai_greeting':
                            greeting = data.get('message', 'Hello! How can I help you?')
                            print(f"👋 Sending custom greeting for speech: {greeting}")
                            await session.send(greeting)
                            
                        elif message_type == 'user_message':
                            user_text = data.get('message', '')
                            print(f"💬 User message for speech: {user_text}")
                            await session.send(user_text)
                            
                    except asyncio.TimeoutError:
                        pass
                    except json.JSONDecodeError:
                        pass
                    
                    # Handle audio input
                    try:
                        audio_data = await asyncio.wait_for(websocket.receive_bytes(), timeout=0.01)
                        print(f"🎤 Received {len(audio_data)} bytes of audio")
                        
                        # Send audio to Gemini for speech response
                        await session.send(types.LiveClientRealtimeInput(
                            audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
                        ))
                        
                    except asyncio.TimeoutError:
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
    print("🚀 Starting SPEECH-enabled Gemini server...")
    print("📍 Access at: http://localhost:8085")
    print("🔊 This server will return SPEECH responses from Gemini!")
    uvicorn.run(app, host="0.0.0.0", port=8085)