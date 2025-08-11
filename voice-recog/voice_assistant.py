#!/usr/bin/env python3
"""
Speech Recognition Assistant
A voice assistant that listens for wake words, captures commands,
and sends them to an n8n webhook for processing.
"""

import speech_recognition as sr
import pyaudio
import wave
import time
import json
import requests
import yaml
import threading
import queue
import logging
from datetime import datetime
from pathlib import Path
import sys

# Optional imports for advanced features
try:
    import snowboy.snowboydetect as snowboydetect
    SNOWBOY_AVAILABLE = True
except ImportError:
    SNOWBOY_AVAILABLE = False
    print("Snowboy not available - using simple keyword detection")

try:
    from pydub import AudioSegment
    from pydub.effects import normalize
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("Pydub not available - noise reduction disabled")

try:
    import numpy as np
    import sounddevice as sd
    import soundfile as sf
    AUDIO_PLAYBACK_AVAILABLE = True
except ImportError:
    AUDIO_PLAYBACK_AVAILABLE = False
    print("Audio playback not available - wake word acknowledgment disabled")


class VoiceAssistant:
    def __init__(self, config_path="config.yaml"):
        self.config = self.load_config(config_path)
        self.setup_logging()
        
        # Audio setup
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # State management
        self.listening = False
        self.wake_detected = False
        self.audio_queue = queue.Queue()
        
        # Initialize recognizer settings
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            
        self.logger.info("Voice Assistant initialized")
        
    def load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            return config
        except FileNotFoundError:
            # Default configuration
            default_config = {
                'wake_word': 'jarvis',
                'stop_phrases': ['stop listening', 'goodbye', 'exit'],
                'webhook_url': 'https://n8n.casa-bakewell.com/webhook/discord-general-channel',
                'client_id': 'voice_assistant',
                'recognition_timeout': 5,
                'phrase_timeout': 3,
                'energy_threshold': 300,
                'dynamic_energy_threshold': True,
                'pause_threshold': 0.8,
                'snowboy_model': 'jarvis.pmdl',  # Optional Snowboy model file
                'logging_level': 'INFO',
                'acknowledgment_tone': {
                    'enabled': True,
                    'audio_file': 'acknowledgment.wav',  # Path to audio file (WAV, MP3, FLAC, etc.)
                    'volume': 0.5,     # Volume multiplier (0.0 to 1.0)
                    'fallback_tone': {
                        'frequency': 800,  # Hz (used if audio file not found)
                        'duration': 0.2    # seconds
                    }
                }
            }
            
            # Save default config
            with open(config_path, 'w') as file:
                yaml.dump(default_config, file, default_flow_style=False)
            
            print(f"Created default config file: {config_path}")
            return default_config
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.get('logging_level', 'INFO')),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('voice_assistant.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def play_acknowledgment_tone(self):
        """Play an audio file (WAV, MP3, etc.) or fallback tone to acknowledge wake word detection"""
        if not self.config['acknowledgment_tone']['enabled']:
            return
            
        if not AUDIO_PLAYBACK_AVAILABLE:
            self.logger.warning("Audio playback not available - cannot play acknowledgment")
            return
            
        tone_config = self.config['acknowledgment_tone']
        
        # Support both old 'wav_file' and new 'audio_file' config keys for backward compatibility
        audio_file = tone_config.get('audio_file') or tone_config.get('wav_file', 'acknowledgment.wav')
        volume = tone_config.get('volume', 0.5)
        
        # Try to play audio file first
        try:
            # Check if file exists
            if Path(audio_file).exists():
                self.logger.debug(f"Attempting to play audio file: {audio_file}")
                
                # Load and play audio file (supports WAV, MP3, FLAC, OGG, etc.)
                data, sample_rate = sf.read(audio_file)
                
                # Apply volume adjustment
                if volume != 1.0:
                    data = data * volume
                
                # Handle different audio formats
                if len(data.shape) == 1:
                    # Mono audio
                    audio_data = data
                else:
                    # Stereo or multi-channel - convert to mono by taking the mean
                    audio_data = np.mean(data, axis=1) if data.shape[1] > 1 else data.flatten()
                
                # Ensure audio data is in the correct range
                audio_data = np.clip(audio_data, -1.0, 1.0)
                
                # Play the audio
                sd.play(audio_data, sample_rate)
                sd.wait()  # Wait for playback to complete
                
                file_extension = Path(audio_file).suffix.upper()
                self.logger.debug(f"Successfully played {file_extension} acknowledgment file: {audio_file}")
                return
                
            else:
                self.logger.warning(f"Audio file not found: {audio_file}, using fallback tone")
                
        except Exception as e:
            self.logger.warning(f"Failed to play audio file '{audio_file}': {e}, using fallback tone")
        
        # Fallback to generated tone if audio file fails
        try:
            fallback_config = tone_config.get('fallback_tone', {})
            frequency = fallback_config.get('frequency', 800)
            duration = fallback_config.get('duration', 0.2)
            sample_rate = 44100
            
            # Generate sine wave tone
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            tone = np.sin(2 * np.pi * frequency * t) * volume
            
            # Apply fade in/out to avoid clicks
            fade_samples = int(0.01 * sample_rate)  # 10ms fade
            if len(tone) > fade_samples * 2:
                tone[:fade_samples] *= np.linspace(0, 1, fade_samples)
                tone[-fade_samples:] *= np.linspace(1, 0, fade_samples)
            
            # Play the tone
            sd.play(tone, sample_rate)
            sd.wait()  # Wait for playback to complete
            
            self.logger.debug("Played fallback acknowledgment tone")
            
        except Exception as e:
            self.logger.warning(f"Failed to play acknowledgment sound: {e}")
    
    def send_to_webhook(self, text):
        """Send transcribed text to n8n webhook"""
        payload = {
            "body": {
                "content": {
                    "text": text,
                    "timestamp": time.time(),
                    "client_id": self.config['client_id']
                }
            }
        }
        
        try:
            response = requests.post(
                self.config['webhook_url'],
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"Successfully sent to webhook: {text}")
            else:
                self.logger.error(f"Webhook error {response.status_code}: {response.text}")
                
        except requests.RequestException as e:
            self.logger.error(f"Failed to send to webhook: {e}")
    
    def detect_wake_word_simple(self, audio_text):
        """Simple wake word detection using text matching"""
        if not audio_text:
            return False
            
        wake_word = self.config['wake_word'].lower()
        text_lower = audio_text.lower()
        
        return wake_word in text_lower
    
    def detect_stop_phrase(self, audio_text):
        """Detect stop phrases in the audio text"""
        if not audio_text:
            return False
            
        text_lower = audio_text.lower()
        stop_phrases = [phrase.lower() for phrase in self.config['stop_phrases']]
        
        return any(phrase in text_lower for phrase in stop_phrases)
    
    def process_audio_with_noise_reduction(self, audio_data):
        """Apply noise reduction if pydub is available"""
        if not PYDUB_AVAILABLE:
            return audio_data
            
        try:
            # Convert audio data to AudioSegment
            audio_segment = AudioSegment.from_wav(audio_data)
            
            # Apply noise reduction techniques
            normalized_audio = normalize(audio_segment)
            
            # You can add more sophisticated noise reduction here
            return normalized_audio
            
        except Exception as e:
            self.logger.warning(f"Noise reduction failed: {e}")
            return audio_data
    
    def listen_for_wake_word(self):
        """Continuously listen for wake word"""
        self.logger.info(f"Listening for wake word: '{self.config['wake_word']}'")
        
        while self.listening:
            try:
                with self.microphone as source:
                    # Listen for audio with timeout
                    audio = self.recognizer.listen(
                        source, 
                        timeout=1,
                        phrase_time_limit=self.config['phrase_timeout']
                    )
                
                # Recognize speech
                try:
                    text = self.recognizer.recognize_google(audio, language='en-US')
                    self.logger.debug(f"Heard: {text}")
                    
                    # Check for wake word
                    if self.detect_wake_word_simple(text):
                        self.logger.info("Wake word detected!")
                        self.wake_detected = True
                        
                        # Play acknowledgment tone
                        self.play_acknowledgment_tone()
                        
                        self.capture_command()
                        
                except sr.UnknownValueError:
                    # No speech recognized, continue listening
                    pass
                except sr.RequestError as e:
                    self.logger.error(f"Recognition error: {e}")
                    time.sleep(1)
                    
            except sr.WaitTimeoutError:
                # Timeout occurred, continue listening
                pass
            except KeyboardInterrupt:
                self.logger.info("Interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Error in wake word detection: {e}")
                time.sleep(1)
    
    def capture_command(self):
        """Capture and process voice command after wake word"""
        self.logger.info("Listening for command...")
        
        try:
            with self.microphone as source:
                # Give user time to speak after wake word
                time.sleep(0.5)
                
                # Listen for command
                audio = self.recognizer.listen(
                    source,
                    timeout=self.config['recognition_timeout'],
                    phrase_time_limit=10
                )
            
            # Recognize the command
            try:
                command_text = self.recognizer.recognize_google(audio, language='en-US')
                self.logger.info(f"Command captured: {command_text}")
                
                # Check for stop phrase
                if self.detect_stop_phrase(command_text):
                    self.logger.info("Stop phrase detected")
                    self.stop_listening()
                    return
                
                # Send command to webhook
                self.send_to_webhook(command_text)
                
            except sr.UnknownValueError:
                self.logger.warning("Could not understand the command")
            except sr.RequestError as e:
                self.logger.error(f"Recognition service error: {e}")
                
        except sr.WaitTimeoutError:
            self.logger.warning("No command received within timeout period")
        except Exception as e:
            self.logger.error(f"Error capturing command: {e}")
        
        # Reset wake detection state
        self.wake_detected = False
    
    def start_listening(self):
        """Start the voice assistant"""
        self.listening = True
        
        # Setup recognizer parameters
        self.recognizer.energy_threshold = self.config['energy_threshold']
        self.recognizer.dynamic_energy_threshold = self.config['dynamic_energy_threshold']
        self.recognizer.pause_threshold = self.config['pause_threshold']
        
        self.logger.info("Starting Voice Assistant...")
        self.logger.info(f"Wake word: '{self.config['wake_word']}'")
        self.logger.info(f"Stop phrases: {self.config['stop_phrases']}")
        self.logger.info("Say 'Ctrl+C' to quit or use stop phrases")
        
        try:
            self.listen_for_wake_word()
        except KeyboardInterrupt:
            self.logger.info("Stopping Voice Assistant...")
        finally:
            self.stop_listening()
    
    def stop_listening(self):
        """Stop the voice assistant"""
        self.listening = False
        self.logger.info("Voice Assistant stopped")


def main():
    """Main entry point"""
    print("Speech Recognition Assistant")
    print("==========================")
    
    # Initialize assistant
    assistant = VoiceAssistant()
    
    # Start listening
    assistant.start_listening()


if __name__ == "__main__":
    main()