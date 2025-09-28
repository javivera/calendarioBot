#!/usr/bin/env python3
"""
Simple test client for the WebSocket server.
Usage: python test_client.py
"""

import asyncio
import websockets
import json
import base64

async def test_websocket():
    """Test the WebSocket server with a simple handshake and dummy audio."""
    try:
        async with websockets.connect("ws://localhost:9080") as websocket:
            print("Connected to WebSocket server!")
            
            # 1. Send setup/config message
            setup_message = {
                "setup": {
                    "temperature": 0.7,
                    "max_output_tokens": 100
                }
            }
            await websocket.send(json.dumps(setup_message))
            print("Sent setup message")
            
            # 2. Send dummy audio chunk (silence)
            silence = b"\x00" * 320  # 320 bytes of silence (16-bit PCM)
            audio_message = {
                "realtime_input": {
                    "media_chunks": [{
                        "mime_type": "audio/pcm",
                        "data": base64.b64encode(silence).decode("utf-8")
                    }]
                }
            }
            await websocket.send(json.dumps(audio_message))
            print("Sent audio chunk")
            
            # 3. Listen for responses
            print("Listening for responses...")
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(response)
                    
                    if "text" in data:
                        print(f"Received text: {data['text']}")
                    elif "audio" in data:
                        print(f"Received audio: {len(data['audio'])} characters (base64)")
                    else:
                        print(f"Received: {data}")
                        
            except asyncio.TimeoutError:
                print("No response received within 10 seconds")
            except websockets.ConnectionClosed:
                print("Connection closed by server")
                
    except ConnectionRefusedError:
        print("Error: Could not connect to ws://localhost:9080")
        print("Make sure the server is running with: python main2.py")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Testing WebSocket connection...")
    asyncio.run(test_websocket())