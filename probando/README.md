# Audio Chat with Gemini + OpenAI TTS

A web application that records audio, sends it to Google's Gemini API for processing, and plays back the response using OpenAI's high-quality text-to-speech.

## Features

- 🎤 **Audio Recording**: Web-based microphone recording using WebRTC
- 🤖 **Gemini API Integration**: Sends audio to Gemini 2.0 Flash for processing
- 🔊 **OpenAI TTS**: High-quality text-to-speech using OpenAI's TTS API
- 🌐 **WebSocket Communication**: Real-time bidirectional communication
- 📱 **Responsive Interface**: Clean, modern web UI

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up your API keys:**
   - Get a Google AI API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Get an OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys)
   - Set the environment variables:
     ```bash
     export GOOGLE_API_KEY="your-google-api-key-here"
     export OPENAI_API_KEY="your-openai-api-key-here"
     ```
   - Or modify the API keys directly in `app.py`

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open your browser:**
   - Navigate to `http://localhost:8080`
   - Allow microphone permissions when prompted

## How it Works

1. User clicks "🎤 Start Recording" and speaks
2. Audio is captured as WebM and sent via WebSocket to Flask server
3. Server forwards audio to Gemini API using the google-genai library
4. Gemini processes the audio and returns text response
5. Text is sent to OpenAI TTS API to generate high-quality speech
6. Generated audio is sent back to browser and played automatically

## System Requirements

- Python 3.8+
- A microphone
- Modern web browser with WebRTC support
- Audio output device/speakers
- Valid Google AI and OpenAI API keys

## Troubleshooting

- **No microphone access**: Check browser permissions
- **Audio not playing**: Make sure your system has audio output enabled
- **Connection errors**: Verify your API keys are valid
- **Dependencies issues**: Try installing packages individually
- **TTS not working**: Ensure OPENAI_API_KEY is set correctly

## File Structure

```
├── app.py              # Main Flask application with OpenAI TTS
├── templates/
│   └── index.html      # Web interface with audio playback
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## API Costs

- **Gemini API**: Free tier available with usage limits
- **OpenAI TTS**: $15.00 per 1M characters (very cost-effective for voice responses)