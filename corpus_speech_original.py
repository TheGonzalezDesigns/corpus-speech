import pyttsx3
import yaml
import logging
from typing import Optional, Dict, Any

class TextToSpeech:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.engine = None
        self._initialize_engine()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logging.warning(f"Config file {config_path} not found, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            'speech': {
                'engine': 'pyttsx3',
                'voice': {
                    'rate': 200,
                    'volume': 0.9,
                    'voice_id': None
                }
            }
        }
    
    def _initialize_engine(self):
        try:
            self.engine = pyttsx3.init()
            self._configure_voice()
            logging.info("Text-to-speech engine initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize TTS engine: {e}")
            raise
    
    def _configure_voice(self):
        if not self.engine:
            return
            
        voice_config = self.config['speech']['voice']
        
        # Set rate (speed)
        self.engine.setProperty('rate', voice_config['rate'])
        
        # Set volume
        self.engine.setProperty('volume', voice_config['volume'])
        
        # Set voice if specified
        if voice_config.get('voice_id'):
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if voice_config['voice_id'] in voice.id:
                    self.engine.setProperty('voice', voice.id)
                    break
    
    def speak(self, text: str) -> bool:
        if not self.engine:
            logging.error("TTS engine not initialized")
            return False
            
        try:
            self.engine.say(text)
            self.engine.runAndWait()
            logging.info(f"Spoke: {text[:50]}...")
            return True
        except Exception as e:
            logging.error(f"Error speaking text: {e}")
            return False
    
    def get_available_voices(self) -> list:
        if not self.engine:
            return []
            
        voices = self.engine.getProperty('voices')
        return [{"id": voice.id, "name": voice.name} for voice in voices]
    
    def set_voice_properties(self, rate: Optional[int] = None, 
                           volume: Optional[float] = None,
                           voice_id: Optional[str] = None):
        if not self.engine:
            return False
            
        try:
            if rate is not None:
                self.engine.setProperty('rate', rate)
                self.config['speech']['voice']['rate'] = rate
                
            if volume is not None:
                self.engine.setProperty('volume', volume)
                self.config['speech']['voice']['volume'] = volume
                
            if voice_id is not None:
                self.engine.setProperty('voice', voice_id)
                self.config['speech']['voice']['voice_id'] = voice_id
                
            return True
        except Exception as e:
            logging.error(f"Error setting voice properties: {e}")
            return False