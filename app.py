from flask import Flask, render_template, request, jsonify
from main import chat, get_next_three_reservations, get_all_reservations
import pyttsx3

app = Flask(__name__)

# Initialize the TTS engine
engine = pyttsx3.init()
# Set a faster speaking rate
engine.setProperty('rate', 180) 

def speak_text(text):
    # Attempt to find a Spanish voice
    voices = engine.getProperty('voices')
    spanish_voice = None
    for voice in voices:
        # Check for Spanish (es) language tag
        if 'es_ES' in voice.languages:
            spanish_voice = voice
            break
    
    if spanish_voice:
        engine.setProperty('voice', spanish_voice.id)
    else:
        print("No Spanish voice found, using default.")

    engine.say(text)
    engine.runAndWait()

@app.route('/')
def index():
    # Get the next three reservations to display
    next_reservations = get_next_three_reservations()
    print(f"--> Debug: app.py - Passing {len(next_reservations)} reservations to index.html")
    return render_template('index.html', next_reservations=next_reservations)

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    user_input = request.form.get('message', '')
    if not user_input:
        return jsonify({'response': 'Please provide a message.'}), 400

    try:
        response = chat.send_message(user_input)
        speak_text(response.text) # Speak the bot's response
        return jsonify({'response': response.text})
    except Exception as e:
        return jsonify({'response': f"Error: {str(e)}"}), 500

@app.route('/reservations_data')
def reservations_data_endpoint():
    try:
        all_reservations = get_all_reservations()
        # Convert datetime objects to string for JSON serialization
        for res in all_reservations:
            if isinstance(res.get('check_in_dates'), datetime):
                res['check_in_dates'] = res['check_in_dates'].strftime('%Y-%m-%d')
            if isinstance(res.get('check_out_dates'), datetime):
                res['check_out_dates'] = res['check_out_dates'].strftime('%Y-%m-%d')
        return jsonify({'reservations': all_reservations})
    except Exception as e:
        return jsonify({'error': f"Error fetching reservations data: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
