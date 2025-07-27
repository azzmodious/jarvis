#!/usr/bin/env python3
"""
Voice Assistant for Raspberry Pi
Listens for wake word, converts speech to text, and sends to n8n webhook
"""

import speech_recognition as sr
import pyaudio
import wave
import threading
import time
import requests
import json
import logging
from typing import Optional
import queue
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VoiceAssistant:
    def __init__(self, webhook_url: str, wake_word: str = "assistant", 
                 timeout: int = 5, phrase_timeout: int = 3):
        """
        Initialize the Voice Assistant
        
        Args:
            webhook_url: The n8n webhook URL to send commands to
            wake_word: The wake word to listen for (default: "assistant")
            timeout: Seconds to wait for audio input after wake word
            phrase_timeout: Seconds of silence before considering phrase complete
        """
        self.webhook_url = webhook_url
        self.wake_word = wake_word.lower()
        self.timeout = timeout
        self.phrase_timeout = phrase_timeout
        
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Audio settings
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        
        # State management
        self.listening = False
        self.audio_queue = queue.Queue()
        
        # Calibrate microphone
        self._calibrate_microphone()
        
    def _calibrate_microphone(self):
        """Calibrate microphone for ambient noise"""
        logger.info("Calibrating microphone for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        logger.info("Microphone calibrated")
    
    def _listen_for_wake_word(self) -> bool:
        """
        Listen for the wake word using simple speech recognition
        Returns True if wake word is detected
        """
        try:
            with self.microphone as source:
                # Listen for audio with a shorter timeout for wake word detection
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
            
            # Use Google's free speech recognition for wake word detection
            text = self.recognizer.recognize_google(audio).lower()
            logger.debug(f"Heard: {text}")
            
            return self.wake_word in text
            
        except sr.WaitTimeoutError:
            # Normal timeout, continue listening
            return False
        except sr.UnknownValueError:
            # Could not understand audio
            return False
        except sr.RequestError as e:
            logger.error(f"Speech recognition error: {e}")
            return False
    
    def _record_command(self) -> Optional[str]:
        """
        Record and transcribe voice command after wake word detection
        Returns the transcribed text or None if failed
        """
        logger.info("Wake word detected! Listening for command...")
        
        try:
            with self.microphone as source:
                # Listen for the actual command with longer timeout
                audio = self.recognizer.listen(
                    source, 
                    timeout=self.timeout, 
                    phrase_time_limit=self.phrase_timeout
                )
            
            logger.info("Processing voice command...")
            
            # Transcribe the command
            command_text = self.recognizer.recognize_google(audio)
            logger.info(f"Command recognized: {command_text}")
            
            return command_text
            
        except sr.WaitTimeoutError:
            logger.warning("No command received within timeout period")
            return None
        except sr.UnknownValueError:
            logger.warning("Could not understand the command")
            return None
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return None
    
    def _send_to_webhook(self, command: str) -> bool:
        """
        Send the voice command to n8n webhook
        
        Args:
            command: The transcribed voice command
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                "command": command,
                "timestamp": time.time(),
                "source": "voice_assistant"
            }
            
            logger.info(f"Sending command to webhook: {command}")
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Command sent successfully to n8n workflow")
                return True
            else:
                logger.error(f"Webhook request failed with status {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Error sending to webhook: {e}")
            return False
    
    def run(self):
        """Main loop - listen for wake word and process commands"""
        logger.info(f"Voice Assistant started. Listening for wake word: '{self.wake_word}'")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                # Listen for wake word
                if self._listen_for_wake_word():
                    # Record and process command
                    command = self._record_command()
                    
                    if command:
                        # Send command to n8n workflow
                        success = self._send_to_webhook(command)
                        
                        if success:
                            logger.info("Command processed successfully")
                        else:
                            logger.error("Failed to process command")
                    
                    # Brief pause before listening for wake word again
                    time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Voice Assistant stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

def main():
    # Configuration - Update these values for your setup
    WEBHOOK_URL = "https://your-n8n-instance.com/webhook/voice-command"  # Replace with your n8n webhook URL
    WAKE_WORD = "assistant"  # Change to your preferred wake word
    
    # Create and run voice assistant
    assistant = VoiceAssistant(
        webhook_url=WEBHOOK_URL,
        wake_word=WAKE_WORD,
        timeout=5,  # Seconds to wait for command after wake word
        phrase_timeout=3  # Seconds of silence before considering phrase complete
    )
    
    assistant.run()

if __name__ == "__main__":
    main()