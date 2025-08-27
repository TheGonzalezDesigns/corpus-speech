from flask import Flask, request
from flask_restx import Api, Resource, fields
from flask_restx.inputs import regex
import logging
import yaml
from corpus_speech import TextToSpeech
from marshmallow import validate

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
    'rate': fields.Integer(description='Speech rate in words per minute', example=200, 
                          enum=[150, 175, 200, 225, 250, 275, 300]),
    'volume': fields.Float(description='Volume level', example=0.9,
                          enum=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]),
    'voice_id': fields.String(description='Voice ID to use', example='ito',
                             enum=['ito', 'dacher', 'aiden', 'dorothy']),
    'voice_description': fields.String(description='Custom voice description for Hume TTS', example='Warm, conversational tone',
                                      enum=['Warm, conversational tone', 'Energetic and enthusiastic voice', 'Calm and thoughtful delivery',
                                           'Curious and questioning tone', 'Confident and clear speech', 'Friendly and approachable manner'])
})

# Define voice choices - will be populated dynamically
VOICE_CHOICES = ['ito', 'dacher', 'aiden', 'dorothy']  # fallback

# Get actual voice names from TTS system if available
try:
    if tts:
        VOICE_CHOICES = tts.get_voice_name_choices()
        logging.info(f"Loaded {len(VOICE_CHOICES)} voice names for Swagger dropdown")
except Exception as e:
    logging.warning(f"Could not load dynamic voice names for dropdown: {e}")
    VOICE_CHOICES = ['Ito', 'Dacher', 'Aiden', 'Dorothy']  # fallback names
    logging.info("Using fallback voice names")
SPEED_CHOICES = [0.5, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.7, 2.0]
EMOTION_CHOICES = ['calm', 'excited', 'curious', 'observant', 'friendly', 'enthusiastic', 'confident', 'warm', 'energetic', 'thoughtful']
ENGINE_CHOICES = ['hume', 'pyttsx3']

voice_model = api.model('VoiceRequest', {
    'voice_name': fields.String(required=True, description='Voice name to set', 
                               example='Ito', enum=VOICE_CHOICES)
})

speed_model = api.model('SpeedRequest', {
    'speed': fields.Float(required=True, description='Speech speed multiplier', example=1.0,
                         enum=SPEED_CHOICES)
})

DESCRIPTION_CHOICES = [
    'Warm, conversational tone', 'Energetic and enthusiastic voice', 'Calm and thoughtful delivery',
    'Curious and questioning tone', 'Confident and clear speech', 'Friendly and approachable manner',
    'Excited with clear emotion', 'Observant and descriptive style', 'Professional and articulate',
    'Casual and relaxed delivery'
]

emotion_model = api.model('EmotionRequest', {
    'emotion': fields.String(required=True, description='Emotional context for speech', example='calm',
                            enum=EMOTION_CHOICES),
    'description': fields.String(description='Detailed voice description', example='Warm, conversational tone',
                                enum=DESCRIPTION_CHOICES)
})

engine_model = api.model('EngineRequest', {
    'engine': fields.String(required=True, description='TTS engine to use', example='hume', enum=ENGINE_CHOICES)
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
    @api.doc(params={
        'voice_name': {'description': 'Voice name to set', 'enum': VOICE_CHOICES, 'required': True}
    })
    @api.response(200, 'Success', success_response)
    @api.response(400, 'Bad Request', error_response)
    @api.response(500, 'Internal Server Error', error_response)
    def post(self):
        """Set the active voice for speech synthesis by friendly name"""
        if not tts:
            return {"error": "TTS not initialized"}, 500
        
        voice_name = request.args.get('voice_name')
        if not voice_name:
            return {"error": "Missing 'voice_name' parameter"}, 400
        
        # Convert voice name to ID
        voice_id = tts.get_voice_id_by_name(voice_name)
        if not voice_id:
            available_names = tts.get_voice_name_choices()
            return {"error": f"Voice '{voice_name}' not found. Available voices: {available_names[:10]}..."}, 400
        
        success = tts.set_voice_properties(voice_id=voice_id)
        
        if success:
            return {"status": "success", "message": f"Voice set to {voice_name} (ID: {voice_id[:8]}...)"}
        else:
            return {"error": f"Failed to set voice to {voice_name}"}, 500

@api.route('/speed')
class Speed(Resource):
    @api.doc(params={
        'speed': {'description': 'Speech speed multiplier', 'enum': SPEED_CHOICES, 'required': True, 'type': 'number'}
    })
    @api.response(200, 'Success', success_response)
    @api.response(400, 'Bad Request', error_response)
    @api.response(500, 'Internal Server Error', error_response)
    def post(self):
        """Set speech speed/rate"""
        if not tts:
            return {"error": "TTS not initialized"}, 500
        
        speed_str = request.args.get('speed')
        if not speed_str:
            return {"error": "Missing 'speed' parameter"}, 400
        
        try:
            speed = float(speed_str)
        except ValueError:
            return {"error": "Speed must be a valid number"}, 400
        
        if speed not in SPEED_CHOICES:
            return {"error": f"Invalid speed. Choose from: {SPEED_CHOICES}"}, 400
        
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
    @api.doc(params={
        'emotion': {'description': 'Emotional context for speech', 'enum': EMOTION_CHOICES, 'required': True},
        'description': {'description': 'Voice description style', 'enum': DESCRIPTION_CHOICES, 'required': False}
    })
    @api.response(200, 'Success', success_response)
    @api.response(400, 'Bad Request', error_response)
    @api.response(500, 'Internal Server Error', error_response)
    def post(self):
        """Set emotional context and voice description for Hume TTS"""
        if not tts:
            return {"error": "TTS not initialized"}, 500
        
        emotion = request.args.get('emotion')
        if not emotion:
            return {"error": "Missing 'emotion' parameter"}, 400
        
        if emotion not in EMOTION_CHOICES:
            return {"error": f"Invalid emotion. Choose from: {EMOTION_CHOICES}"}, 400
        
        description = request.args.get('description', f"Natural {emotion} tone")
        
        success = tts.set_voice_properties(voice_description=description)
        
        if success:
            return {"status": "success", "message": f"Emotion set to {emotion} with description: {description}"}
        else:
            return {"error": f"Failed to set emotion to {emotion}"}, 500

@api.route('/engine')
class Engine(Resource):
    @api.doc(params={
        'engine': {'description': 'TTS engine to use', 'enum': ENGINE_CHOICES, 'required': True}
    })
    @api.response(200, 'Success', success_response)
    @api.response(400, 'Bad Request', error_response)
    @api.response(500, 'Internal Server Error', error_response)
    def post(self):
        """Switch TTS engine between Hume and pyttsx3"""
        if not tts:
            return {"error": "TTS not initialized"}, 500
        
        engine = request.args.get('engine')
        if not engine:
            return {"error": "Missing 'engine' parameter"}, 400
        
        if engine not in ENGINE_CHOICES:
            return {"error": f"Invalid engine. Choose from: {ENGINE_CHOICES}"}, 400
        
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