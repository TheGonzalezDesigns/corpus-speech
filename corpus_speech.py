import os
import yaml
import logging
import base64
import io
import pygame
import requests
from typing import Optional, Dict, Any
from hume.client import HumeClient

class TextToSpeech:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.pyttsx3_engine = None
        self.hume_client = None
        self._initialize_engines()
        
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
                'engine': 'hume',
                'voice': {
                    'rate': 200,
                    'volume': 0.9,
                    'voice_id': 'ito'
                }
            },
            'hume': {
                'api_key': None,
                'base_url': 'https://api.hume.ai/v0',
                'tts': {
                    'format': 'mp3',
                    'instant_mode': True,
                    'num_generations': 1,
                    'speed': 1.0,
                    'voice_description': None
                }
            }
        }
    
    def _initialize_engines(self):
        engine_type = self.config.get('speech', {}).get('engine', 'hume')
        
        if engine_type == 'hume':
            self._initialize_hume()
        else:
            self._initialize_pyttsx3()
    
    def _initialize_pyttsx3(self):
        try:
            import pyttsx3
            self.pyttsx3_engine = pyttsx3.init()
            self._configure_pyttsx3_voice()
            logging.info("pyttsx3 TTS engine initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize pyttsx3 TTS engine: {e}")
            raise
    
    def _initialize_hume(self):
        try:
            api_key = os.environ.get('HUME_API_KEY') or self.config.get('hume', {}).get('api_key')
            if not api_key:
                raise ValueError("HUME_API_KEY not found in environment or config")
            
            self.hume_client = HumeClient(api_key=api_key)
            
            # Initialize pygame mixer for audio playback
            pygame.mixer.init()
            
            logging.info("Hume TTS client initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize Hume TTS client: {e}")
            # Fall back to pyttsx3
            logging.info("Falling back to pyttsx3...")
            self.config['speech']['engine'] = 'pyttsx3'
            self._initialize_pyttsx3()
    
    def _configure_pyttsx3_voice(self):
        if not self.pyttsx3_engine:
            return
            
        voice_config = self.config['speech']['voice']
        
        # Set rate (speed)
        self.pyttsx3_engine.setProperty('rate', voice_config['rate'])
        
        # Set volume
        self.pyttsx3_engine.setProperty('volume', voice_config['volume'])
        
        # Set voice if specified
        if voice_config.get('voice_id'):
            voices = self.pyttsx3_engine.getProperty('voices')
            for voice in voices:
                if voice_config['voice_id'] in voice.id:
                    self.pyttsx3_engine.setProperty('voice', voice.id)
                    break
    
    def speak(self, text: str) -> bool:
        engine_type = self.config.get('speech', {}).get('engine', 'hume')
        
        if engine_type == 'hume' and self.hume_client:
            return self._speak_with_hume(text)
        elif engine_type == 'pyttsx3' and self.pyttsx3_engine:
            return self._speak_with_pyttsx3(text)
        else:
            logging.error("No TTS engine available")
            return False
    
    def _speak_with_hume(self, text: str) -> bool:
        try:
            from hume.tts import PostedUtterance, PostedContextWithUtterances
            from hume.tts import FormatMp3, FormatWav, PostedUtteranceVoiceWithId
            
            voice_config = self.config['speech']['voice']
            hume_config = self.config['hume']['tts']
            
            # Prepare the utterance with proper voice specification
            voice_id = voice_config.get('voice_id', 'ito')
            voice_description = hume_config.get('voice_description')
            
            # Create voice object with ID
            voice_obj = PostedUtteranceVoiceWithId(id=voice_id)
            
            # Create utterance with voice object and description
            description = voice_description or "Natural conversational tone"
            
            utterance = PostedUtterance(
                text=text,
                description=description,
                voice=voice_obj
            )
            
            # Determine format
            format_type = hume_config.get('format', 'mp3').lower()
            if format_type == 'wav':
                audio_format = FormatWav()
            else:
                audio_format = FormatMp3()
            
            # Use Hume SDK to synthesize speech
            response = self.hume_client.tts.synthesize_json(
                utterances=[utterance],
                format=audio_format,
                num_generations=hume_config.get('num_generations', 1)
            )
            
            # Extract audio data
            if response.generations and len(response.generations) > 0:
                audio_b64 = response.generations[0].audio
                audio_bytes = base64.b64decode(audio_b64)
                
                # Play audio using pygame
                self._play_audio_bytes(audio_bytes)
                
                logging.info(f"Hume TTS spoke: {text[:50]}...")
                return True
            else:
                logging.error("No audio generated by Hume TTS")
                return False
                
        except Exception as e:
            logging.error(f"Error with Hume TTS: {e}")
            return False
    
    def _speak_with_pyttsx3(self, text: str) -> bool:
        if not self.pyttsx3_engine:
            logging.error("pyttsx3 engine not initialized")
            return False
            
        try:
            self.pyttsx3_engine.say(text)
            self.pyttsx3_engine.runAndWait()
            logging.info(f"pyttsx3 spoke: {text[:50]}...")
            return True
        except Exception as e:
            logging.error(f"Error with pyttsx3: {e}")
            return False
    
    def _play_audio_bytes(self, audio_bytes: bytes):
        """Play audio bytes using pygame"""
        try:
            # Create a BytesIO object from the audio bytes
            audio_buffer = io.BytesIO(audio_bytes)
            
            # Load and play the audio
            pygame.mixer.music.load(audio_buffer)
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
        except Exception as e:
            logging.error(f"Error playing audio: {e}")
            raise
    
    def get_available_voices(self) -> list:
        engine_type = self.config.get('speech', {}).get('engine', 'hume')
        
        if engine_type == 'hume' and self.hume_client:
            try:
                # Get voices from Hume API
                response = self.hume_client.tts.voices.list(provider="HUME_AI")
                voices = []
                
                # Handle paginated response
                for voice in response:
                    voices.append({
                        "id": voice.id,
                        "name": f"{voice.name or voice.id} - Hume Voice",
                        "provider": voice.provider,
                        "tags": voice.tags if hasattr(voice, 'tags') else {}
                    })
                
                logging.info(f"Retrieved {len(voices)} voices from Hume API")
                return voices
                
            except Exception as e:
                logging.error(f"Failed to get Hume voices: {e}")
                # Fall back to hardcoded common voices
                return [
                    {"id": "ito", "name": "Ito - Conversational", "provider": "hume"},
                    {"id": "dacher", "name": "Dacher - Warm and approachable", "provider": "hume"},
                    {"id": "aiden", "name": "Aiden - Confident and clear", "provider": "hume"},
                    {"id": "dorothy", "name": "Dorothy - Friendly and engaging", "provider": "hume"}
                ]
                
        elif self.pyttsx3_engine:
            voices = self.pyttsx3_engine.getProperty('voices')
            return [{"id": voice.id, "name": voice.name, "provider": "pyttsx3"} for voice in voices]
        else:
            return []
    
    def get_voice_id_by_name(self, voice_name: str) -> Optional[str]:
        """Get voice ID by friendly name"""
        voices = self.get_available_voices()
        
        # Try exact name match first
        for voice in voices:
            if voice['name'].lower() == voice_name.lower():
                return voice['id']
        
        # Try partial name match (e.g. "ito" matches "Ito - Hume Voice")
        voice_name_lower = voice_name.lower()
        for voice in voices:
            voice_name_clean = voice['name'].split(' -')[0].lower()  # Get just the name part
            if voice_name_clean == voice_name_lower:
                return voice['id']
        
        # Try contains match
        for voice in voices:
            if voice_name_lower in voice['name'].lower():
                return voice['id']
        
        return None
    
    def get_voice_name_choices(self) -> list:
        """Get list of voice names for dropdown choices"""
        voices = self.get_available_voices()
        return [voice['name'].split(' -')[0] for voice in voices]  # Just the name part, not "- Hume Voice"
    
    def set_voice_properties(self, rate: Optional[int] = None, 
                           volume: Optional[float] = None,
                           voice_id: Optional[str] = None,
                           voice_description: Optional[str] = None) -> bool:
        try:
            engine_type = self.config.get('speech', {}).get('engine', 'hume')
            
            if engine_type == 'hume':
                # Update Hume-specific settings
                if voice_id is not None:
                    self.config['speech']['voice']['voice_id'] = voice_id
                if voice_description is not None:
                    self.config['hume']['tts']['voice_description'] = voice_description
                return True
                
            elif engine_type == 'pyttsx3' and self.pyttsx3_engine:
                # Update pyttsx3 settings
                if rate is not None:
                    self.pyttsx3_engine.setProperty('rate', rate)
                    self.config['speech']['voice']['rate'] = rate
                    
                if volume is not None:
                    self.pyttsx3_engine.setProperty('volume', volume)
                    self.config['speech']['voice']['volume'] = volume
                    
                if voice_id is not None:
                    self.pyttsx3_engine.setProperty('voice', voice_id)
                    self.config['speech']['voice']['voice_id'] = voice_id
                    
                return True
            else:
                return False
                
        except Exception as e:
            logging.error(f"Error setting voice properties: {e}")
            return False
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Get information about the current TTS engine"""
        engine_type = self.config.get('speech', {}).get('engine', 'hume')
        
        return {
            'engine': engine_type,
            'available': self.hume_client is not None if engine_type == 'hume' else self.pyttsx3_engine is not None,
            'voice_id': self.config['speech']['voice'].get('voice_id'),
            'hume_available': self.hume_client is not None,
            'pyttsx3_available': self.pyttsx3_engine is not None
        }