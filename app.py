from flask import Flask, request, jsonify
import logging
import yaml
from corpus_speech import TextToSpeech

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize TTS
try:
    tts = TextToSpeech()
except Exception as e:
    logging.error(f"Failed to initialize TTS: {e}")
    tts = None

@app.route('/speak', methods=['POST'])
def speak():
    if not tts:
        return jsonify({"error": "TTS not initialized"}), 500
    
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Missing 'text' field"}), 400
    
    text = data['text']
    success = tts.speak(text)
    
    if success:
        return jsonify({"status": "success", "message": "Text spoken successfully"})
    else:
        return jsonify({"error": "Failed to speak text"}), 500

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "running" if tts else "error",
        "module": "corpus-speech",
        "available_voices": tts.get_available_voices() if tts else []
    })

@app.route('/config', methods=['POST'])
def update_config():
    if not tts:
        return jsonify({"error": "TTS not initialized"}), 500
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No configuration data provided"}), 400
    
    success = tts.set_voice_properties(
        rate=data.get('rate'),
        volume=data.get('volume'),
        voice_id=data.get('voice_id')
    )
    
    if success:
        return jsonify({"status": "success", "message": "Configuration updated"})
    else:
        return jsonify({"error": "Failed to update configuration"}), 500

@app.route('/voices', methods=['GET'])
def get_voices():
    if not tts:
        return jsonify({"error": "TTS not initialized"}), 500
    
    return jsonify({"voices": tts.get_available_voices()})

if __name__ == '__main__':
    # Load config for server settings
    try:
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
        api_config = config.get('api', {})
    except:
        api_config = {'host': '0.0.0.0', 'port': 5001}
    
    app.run(
        host=api_config.get('host', '0.0.0.0'),
        port=api_config.get('port', 5001),
        debug=False
    )