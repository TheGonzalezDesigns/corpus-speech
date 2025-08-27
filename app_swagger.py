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
    'voice_id': fields.String(description='Voice ID to use', example='ito'),
    'voice_description': fields.String(description='Custom voice description for Hume TTS', example='Warm, conversational tone')
})

voice_model = api.model('VoiceRequest', {
    'voice_id': fields.String(required=True, description='Voice ID to set', example='ito')
})

speed_model = api.model('SpeedRequest', {
    'speed': fields.Float(required=True, description='Speech speed multiplier (0.5-2.0)', example=1.0)
})

emotion_model = api.model('EmotionRequest', {
    'emotion': fields.String(required=True, description='Emotional context for speech', example='calm'),
    'description': fields.String(description='Detailed voice description', example='Warm, friendly tone with slight excitement')
})

engine_model = api.model('EngineRequest', {
    'engine': fields.String(required=True, description='TTS engine to use', example='hume', enum=['hume', 'pyttsx3'])
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

@api.route('/voice')
class Voice(Resource):
    @api.expect(voice_model)
    @api.response(200, 'Success', success_response)
    @api.response(400, 'Bad Request', error_response)
    @api.response(500, 'Internal Server Error', error_response)
    def post(self):
        """Set the active voice for speech synthesis"""
        if not tts:
            return {"error": "TTS not initialized"}, 500
        
        data = request.get_json()
        if not data or 'voice_id' not in data:
            return {"error": "Missing 'voice_id' field"}, 400
        
        voice_id = data['voice_id']
        success = tts.set_voice_properties(voice_id=voice_id)
        
        if success:
            return {"status": "success", "message": f"Voice set to {voice_id}"}
        else:
            return {"error": f"Failed to set voice to {voice_id}"}, 500

@api.route('/speed')
class Speed(Resource):
    @api.expect(speed_model)
    @api.response(200, 'Success', success_response)
    @api.response(400, 'Bad Request', error_response)
    @api.response(500, 'Internal Server Error', error_response)
    def post(self):
        """Set speech speed/rate"""
        if not tts:
            return {"error": "TTS not initialized"}, 500
        
        data = request.get_json()
        if not data or 'speed' not in data:
            return {"error": "Missing 'speed' field"}, 400
        
        speed = data['speed']
        if speed < 0.5 or speed > 2.0:
            return {"error": "Speed must be between 0.5 and 2.0"}, 400
        
        # For Hume, speed is handled differently than pyttsx3 rate
        if hasattr(tts, 'config') and tts.config.get('speech', {}).get('engine') == 'hume':
            tts.config['hume']['tts']['speed'] = speed
            return {"status": "success", "message": f"Speech speed set to {speed}x"}
        else:
            # Convert speed multiplier to pyttsx3 rate (approximate)
            rate = int(200 * speed)  # Base rate 200 wpm
            success = tts.set_voice_properties(rate=rate)
            if success:
                return {"status": "success", "message": f"Speech rate set to {rate} wpm (speed: {speed}x)"}
            else:
                return {"error": "Failed to set speech speed"}, 500

@api.route('/emotion')
class Emotion(Resource):
    @api.expect(emotion_model)
    @api.response(200, 'Success', success_response)
    @api.response(400, 'Bad Request', error_response)
    @api.response(500, 'Internal Server Error', error_response)
    def post(self):
        """Set emotional context and voice description for Hume TTS"""
        if not tts:
            return {"error": "TTS not initialized"}, 500
        
        data = request.get_json()
        if not data or 'emotion' not in data:
            return {"error": "Missing 'emotion' field"}, 400
        
        emotion = data['emotion']
        description = data.get('description', f"Natural {emotion} tone")
        
        success = tts.set_voice_properties(voice_description=description)
        
        if success:
            return {"status": "success", "message": f"Emotion set to {emotion}"}
        else:
            return {"error": f"Failed to set emotion to {emotion}"}, 500

@api.route('/engine')
class Engine(Resource):
    @api.expect(engine_model)
    @api.response(200, 'Success', success_response)
    @api.response(400, 'Bad Request', error_response)
    @api.response(500, 'Internal Server Error', error_response)
    def post(self):
        """Switch TTS engine between Hume and pyttsx3"""
        if not tts:
            return {"error": "TTS not initialized"}, 500
        
        data = request.get_json()
        if not data or 'engine' not in data:
            return {"error": "Missing 'engine' field"}, 400
        
        engine = data['engine']
        if engine not in ['hume', 'pyttsx3']:
            return {"error": "Engine must be 'hume' or 'pyttsx3'"}, 400
        
        tts.config['speech']['engine'] = engine
        
        # Re-initialize the selected engine
        try:
            tts._initialize_engines()
            return {"status": "success", "message": f"Switched to {engine} TTS engine"}
        except Exception as e:
            return {"error": f"Failed to switch to {engine} engine: {str(e)}"}, 500

@api.route('/info')
class Info(Resource):
    @api.response(200, 'Success')
    @api.response(500, 'Internal Server Error', error_response)
    def get(self):
        """Get current TTS engine information and settings"""
        if not tts:
            return {"error": "TTS not initialized"}, 500
        
        engine_info = tts.get_engine_info()
        current_config = {
            'speech': tts.config.get('speech', {}),
            'hume': tts.config.get('hume', {})
        }
        
        return {
            "engine_info": engine_info,
            "current_config": current_config,
            "available_voices": tts.get_available_voices()
        }

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