# Speech Recorgnition Assistant
This is a simple voice assistant that listens for a wake word, captures your command, and sends it to an n8n webhook for further processing.
** Functionality includes:
- Wake word detection. Default is "jarvis"
- Acknowledgment sound when the wake word is detected
-- sound file formats supported: mp3, wav, ogg
-- Acknowledgment sound file can be configured in `config.yaml`
- Wake word detection and command capture events shound have event handlers to make it easy to extend functionality
- Stop phrase detection
- transcripts should be sent to n8n webhook (https://n8n.casa-bakewell.com/webhook/discord-general-channel)
-- JSON payload should be like:
```json
{ 
    "content":
    {
        "text": "turn on the lights",
        "timestamp": 1642765432.123,
        "client_id": "voice_assistant"
    }
}
```
- Online speech recognition using Google Web Speech API
- Offline wake word detection using Snowboy (optional)
- Noise reduction using `pydub` (optional)
- Easy to extend with custom n8n workflows

** Technical details:
- Uses Python 3
- Runs on Raspberry Pi, Linux and Windows systems
- Speech recognition via `speech_recognition` library
- Wake word detection via `snowboy` (optional)
- Dependency management via `conda`
- Conda virtual environment should be called `voice-assistant`
- Configurable via `config.yaml`
