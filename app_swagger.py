from flask import Flask, request
from flask_restx import Api, Resource, fields
import logging
import yaml
from corpus_speech import TextToSpeech

app = Flask(__name__)
api = Api(app, 
    version='1.0',
    title='Corpus Speech API',
    description='Text-to-speech synthesis capability for Corpus AI companion',
    doc='/swagger'
)

logging.basicConfig(level=logging.INFO)

# Initialize TTS
try:
    tts = TextToSpeech()
except Exception as e:
    logging.error(f"Failed to initialize TTS: {e}")
    tts = None

# Define API models
speak_model = api.model('SpeakRequest', {
    'text': fields.String(required=True, description='Text to convert to speech', example='Hello, I am your AI companion!')
})

config_model = api.model('ConfigRequest', {
    'rate': fields.Integer(description='Speech rate in words per minute', example=200),
    'volume': fields.Float(description='Volume level between 0.0 and 1.0', example=0.9),
    'voice_id': fields.String(description='Voice ID to use', example='english-us')
})

success_response = api.model('SuccessResponse', {
    'status': fields.String(description='Response status'),
    'message': fields.String(description='Response message')
})

error_response = api.model('ErrorResponse', {
    'error': fields.String(description='Error message')
})

status_response = api.model('StatusResponse', {
    'status': fields.String(description='Service status'),
    'module': fields.String(description='Module name'),
    'available_voices': fields.List(fields.Raw, description='List of available voices')
})

voices_response = api.model('VoicesResponse', {
    'voices': fields.List(fields.Raw, description='List of available voices with details')
})

@api.route('/speak')
class Speak(Resource):
    @api.expect(speak_model)
    @api.response(200, 'Success', success_response)
    @api.response(400, 'Bad Request', error_response)
    @api.response(500, 'Internal Server Error', error_response)
    def post(self):
        """Convert text to speech"""
        if not tts:
            return {"error": "TTS not initialized"}, 500
        
        data = request.get_json()
        if not data or 'text' not in data:
            return {"error": "Missing 'text' field"}, 400
        
        text = data['text']
        success = tts.speak(text)
        
        if success:
            return {"status": "success", "message": "Text spoken successfully"}
        else:
            return {"error": "Failed to speak text"}, 500

@api.route('/status')
class Status(Resource):
    @api.response(200, 'Success', status_response)
    def get(self):
        """Get service status and available voices"""
        return {
            "status": "running" if tts else "error",
            "module": "corpus-speech",
            "available_voices": tts.get_available_voices() if tts else []
        }

@api.route('/config')
class Config(Resource):
    @api.expect(config_model)
    @api.response(200, 'Success', success_response)
    @api.response(400, 'Bad Request', error_response)
    @api.response(500, 'Internal Server Error', error_response)
    def post(self):
        """Update voice configuration settings"""
        if not tts:
            return {"error": "TTS not initialized"}, 500
        
        data = request.get_json()
        if not data:
            return {"error": "No configuration data provided"}, 400
        
        success = tts.set_voice_properties(
            rate=data.get('rate'),
            volume=data.get('volume'),
            voice_id=data.get('voice_id')
        )
        
        if success:
            return {"status": "success", "message": "Configuration updated"}
        else:
            return {"error": "Failed to update configuration"}, 500

@api.route('/voices')
class Voices(Resource):
    @api.response(200, 'Success', voices_response)
    @api.response(500, 'Internal Server Error', error_response)
    def get(self):
        """Get detailed list of available voices"""
        if not tts:
            return {"error": "TTS not initialized"}, 500
        
        return {"voices": tts.get_available_voices()}

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