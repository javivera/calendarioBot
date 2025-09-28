from flask import Flask, render_template, request, jsonify
from flask_sock import Sock
import asyncio
import json
import base64
import os
import tempfile
import threading
from pathlib import Path
from google import genai
from openai import OpenAI
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
sock = Sock(app)

# Set up API keys
if 'GOOGLE_API_KEY' not in os.environ:
    os.environ['GOOGLE_API_KEY'] = 'AIzaSyBXr8JTH4QC8EnZviykf50rhgI-c6kPFuw'

if 'OPENAI_API_KEY' not in os.environ:
    print("Warning: OPENAI_API_KEY not set. Please set it in .env file or environment variable for TTS functionality.")
    openai_client = None
else:
    openai_client = OpenAI()

MODEL = "gemini-2.0-flash-exp"

client = genai.Client(
    http_options={
        'api_version': 'v1alpha',
    }
)

class AudioProcessor:
    def __init__(self, websocket):
        self.websocket = websocket
        self.session = None
        
    async def process_audio_with_gemini(self, audio_data, mime_type):
        """Send audio to Gemini and get response"""
        try:
            print(f"Processing audio - Type: {type(audio_data)}, Size: {len(audio_data) if hasattr(audio_data, '__len__') else 'unknown'}, MIME: {mime_type}")
            
            config = {
                "generation_config": {
                    "response_modalities": ["text"]
                }
            }
            
            async with client.aio.live.connect(model=MODEL, config=config) as session:
                self.session = session
                print("Connected to Gemini session")
                
                # Ensure audio_data is base64 string
                if isinstance(audio_data, bytes):
                    print("Converting bytes to base64 string")
                    audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                elif isinstance(audio_data, str):
                    print("Audio data is already a string")
                    # Validate it's base64
                    try:
                        base64.b64decode(audio_data)
                        audio_b64 = audio_data
                        print("String is valid base64")
                    except Exception:
                        print("String is not valid base64, encoding as base64")
                        audio_b64 = base64.b64encode(audio_data.encode('utf-8')).decode('utf-8')
                else:
                    raise ValueError(f"Unsupported audio data type: {type(audio_data)}")
                
                print(f"Base64 string length: {len(audio_b64)}")
                
                # Create parts for Gemini
                parts = [{
                    "mime_type": mime_type,
                    "data": audio_b64
                }]
                
                print(f"Sending parts to Gemini: {len(parts)} parts")
                
                # Send input to Gemini
                await session.send(input=parts)
                print("Audio sent to Gemini successfully")
                
                # Get response from Gemini
                async for response in session.receive():
                    print(f"Received response type: {type(response)}")
                    if response.server_content is None:
                        print("No server content, continuing...")
                        continue
                        
                    model_turn = response.server_content.model_turn
                    if model_turn:
                        print(f"Model turn found with {len(model_turn.parts)} parts")
                        for part in model_turn.parts:
                            if hasattr(part, 'text') and part.text is not None:
                                print(f"Got text response: {part.text[:100]}...")
                                # Send text response back to client
                                self.websocket.send(json.dumps({
                                    "type": "text",
                                    "content": part.text
                                }))
                                
                                # Use OpenAI TTS to generate and send audio
                                self.generate_and_send_tts(part.text)
                                
                    if response.server_content.turn_complete:
                        print("Turn complete")
                        break
                        
        except Exception as e:
            import traceback
            print(f"Error processing with Gemini: {e}")
            print(f"Full traceback: {traceback.format_exc()}")
            try:
                self.websocket.send(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
            except Exception as send_error:
                print(f"Failed to send error message: {send_error}")
    
    def generate_and_send_tts(self, text):
        """Generate TTS audio using OpenAI and send to client"""
        def generate_audio():
            try:
                if openai_client:
                    # Generate audio file using OpenAI TTS
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                        response = openai_client.audio.speech.create(
                            model="tts-1",
                            voice="nova", 
                            input=text,
                        )
                        response.stream_to_file(temp_file.name)
                        
                        # Read the audio file and convert to base64
                        with open(temp_file.name, "rb") as audio_file:
                            audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
                            
                        # Send audio data to client
                        try:
                            self.websocket.send(json.dumps({
                                "type": "audio",
                                "data": audio_data,
                                "format": "mp3"
                            }))
                        except Exception as send_error:
                            print(f"Failed to send audio: {send_error}")
                        
                        # Clean up temp file
                        os.unlink(temp_file.name)
                else:
                    print(f"OpenAI client not available, text: {text}")
            except Exception as e:
                print(f"TTS Error: {e}")
        
        # Run TTS generation in a separate thread to avoid blocking
        thread = threading.Thread(target=generate_audio)
        thread.daemon = True
        thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@sock.route('/audio')
def audio_stream(ws):
    """Handle WebSocket connection for audio streaming"""
    processor = AudioProcessor(ws)
    
    try:
        while True:
            message = ws.receive()
            
            if isinstance(message, str):
                # Handle JSON messages
                try:
                    data = json.loads(message)
                    if data.get('type') == 'audio':
                        # Use the base64 audio data directly, don't decode it
                        audio_data = data['audio']  # Keep as base64 string
                        mime_type = data.get('mime_type', 'audio/webm')
                        
                        # Run async processing in event loop
                        asyncio.run(processor.process_audio_with_gemini(audio_data, mime_type))
                        
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    try:
                        ws.send(json.dumps({"type": "error", "message": "Invalid JSON"}))
                    except Exception:
                        pass
                except Exception as e:
                    print(f"Error processing audio: {e}")
                    try:
                        ws.send(json.dumps({"type": "error", "message": str(e)}))
                    except Exception:
                        pass
            
            elif isinstance(message, bytes):
                # Handle binary audio data directly
                mime_type = "audio/webm"
                try:
                    asyncio.run(processor.process_audio_with_gemini(message, mime_type))
                except Exception as e:
                    print(f"Error processing binary audio: {e}")
                    try:
                        ws.send(json.dumps({"type": "error", "message": str(e)}))
                    except Exception:
                        pass
                
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            ws.send(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass  # Connection might be closed

if __name__ == '__main__':
    app.run(debug=True, port=8080)