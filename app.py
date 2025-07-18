from flask import Flask, render_template, request, jsonify, Response
import main
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    # Get the next three reservations to display
    next_reservations = main.get_next_three_reservations()
    print(f"--> Debug: app.py - Passing {len(next_reservations)} reservations to index.html")
    return render_template('index.html', next_reservations=next_reservations)

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    user_input = request.form.get('message', '')
    if not user_input:
        return jsonify({'response': 'Please provide a message.'}), 400

    try:
        response = main.chat.send_message(user_input)
        return jsonify({'response': response.text})
    except Exception as e:
        return jsonify({'response': f"Error: {str(e)}"}), 500

@app.route('/reservations_data')
def reservations_data_endpoint():
    try:
        all_reservations = main.get_all_reservations()
        # Convert datetime objects to string for JSON serialization
        for res in all_reservations:
            if isinstance(res.get('check_in_dates'), datetime):
                res['check_in_dates'] = res['check_in_dates'].strftime('%Y-%m-%d')
            if isinstance(res.get('check_out_dates'), datetime):
                res['check_out_dates'] = res['check_out_dates'].strftime('%Y-%m-%d')
        return jsonify({'reservations': all_reservations})
    except Exception as e:
        return jsonify({'error': f"Error fetching reservations data: {str(e)}"}), 500

@app.route('/reservations.ics')
def serve_calendar():
    """Generate and serve the ICS calendar file with proper headers"""
    try:
        # Generate fresh ICS file
        result = main.generate_ics_file()
        
        if "successfully" in result:
            # Read the generated file
            with open('static/reservations.ics', 'r', encoding='utf-8') as f:
                ics_content = f.read()
            
            # Return with proper content type
            return Response(
                ics_content,
                mimetype='text/calendar',
                headers={
                    'Content-Disposition': 'inline; filename=reservations.ics',
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            )
        else:
            return Response("Error generating calendar", status=500)
            
    except Exception as e:
        return Response(f"Error: {str(e)}", status=500)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
