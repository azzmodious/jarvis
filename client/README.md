# Voice Assistant Setup for Raspberry Pi

## Installation Requirements

```
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
bash Miniforge3-Linux-aarch64.sh
conda env create -f environment.yml
conda activate flask-audio

```
### 1. Install System Dependencies

First, update your Raspberry Pi and install required system packages:
https://claude.ai/chat/5c1a347a-b6bc-4a08-9cb0-2218ce0d520a
```bash
sudo apt update
sudo apt upgrade -y

sudo apt install mpg123 alsa-utils ffmpeg
sudo apt install pulseaudio pulseaudio-utils
sudo apt install python3-dev
sudo apt install libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev
sudo apt install libasound2-dev
conda remove pygame
```

## Test that the audo system works
```
speaker-test -t sine -f 1000 -l 1 -s 1
sudo find /usr -name "*.wav" | head -1 | xargs aplay
```


# You might need to remove pygame

## Install audio and development packages
sudo apt install -y \
    python3-pip \
    python3-dev \
    libasound2-dev \
    portaudio19-dev \
    flac \
    alsa-utils \
    pulseaudio

# Install additional audio libraries
sudo apt install -y libportaudio2 libportaudiocpp0
```

### 2. Python Dependencies

Create a `requirements.txt` file:

```
SpeechRecognition==3.10.0
pyaudio==0.2.11
requests==2.31.0
numpy==1.24.3
```

Install Python packages:

```bash
pip3 install -r requirements.txt
```

### 3. Audio Setup

#### Test Your Microphone

```bash
# List audio devices
arecord -l

# Test recording (press Ctrl+C to stop)
arecord -D plughw:1,0 -f cd test.wav

# Test playback
aplay test.wav
```

#### Configure Audio Device (if needed)

If you're using a USB microphone, you might need to set it as default:

```bash
# Create/edit ~/.asoundrc
nano ~/.asoundrc
```

Add this content (adjust card numbers based on `arecord -l` output):

```
pcm.!default {
    type asym
    playback.pcm "plughw:0,0"
    capture.pcm "plughw:1,0"
}
```

## Configuration

### 1. Update Webhook URL

In the Python script, replace this line:
```python
WEBHOOK_URL = "https://your-n8n-instance.com/webhook/voice-command"
```

With your actual n8n webhook URL.

### 2. Customize Wake Word

Change the wake word by modifying:
```python
WAKE_WORD = "assistant"  # Change to your preferred wake word
```

Popular options: "computer", "jarvis", "hello", "hey assistant"

### 3. Adjust Timeouts

You can modify these values based on your needs:
- `timeout=5`: Seconds to wait for command after wake word
- `phrase_timeout=3`: Seconds of silence before considering phrase complete

## Usage

### 1. Run the Voice Assistant

```bash
python3 voice_assistant.py
```

### 2. Interaction Flow

1. The assistant starts listening for the wake word
2. Say your wake word (default: "assistant")
3. After detection, speak your command
4. The command is transcribed and sent to your n8n webhook

### 3. N8N Webhook Payload

Your n8n workflow will receive JSON data like this:

```json
{
    "command": "turn on the lights",
    "timestamp": 1642765432.123,
    "source": "voice_assistant"
}
```

## Troubleshooting

### Common Issues

1. **"No module named '_portaudio'"**
   ```bash
   sudo apt install portaudio19-dev
   pip3 install --upgrade pyaudio
   ```

2. **Microphone not working**
   - Check `arecord -l` to see available devices
   - Test with `arecord -D plughw:X,Y -f cd test.wav` (replace X,Y with your device)
   - Adjust volume with `alsamixer`

3. **Wake word not detected**
   - Try speaking louder and clearer
   - Reduce background noise
   - Test different wake words (shorter words often work better)

4. **Speech recognition errors**
   - Ensure internet connection (uses Google Speech API)
   - Check microphone quality and positioning
   - Adjust microphone sensitivity in `alsamixer`

### Performance Tips

1. **Improve Wake Word Detection**
   - Use simple, distinct words
   - Speak clearly and at consistent volume
   - Position microphone 6-12 inches from your mouth

2. **Reduce Latency**
   - Use a faster internet connection
   - Consider offline speech recognition libraries for wake word detection
   - Adjust timeout values based on your speaking pace

3. **Auto-start on Boot**
   Create a systemd service:
   ```bash
   sudo nano /etc/systemd/system/voice-assistant.service
   ```
   
   Add:
   ```ini
   [Unit]
   Description=Voice Assistant
   After=network.target
   
   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/voice-assistant
   ExecStart=/usr/bin/python3 /home/pi/voice-assistant/voice_assistant.py
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   Enable and start:
   ```bash
   sudo systemctl enable voice-assistant.service
   sudo systemctl start voice-assistant.service
   ```

## Advanced Features

For production use, consider adding:

- **Offline wake word detection** using libraries like Porcupine or Snowboy
- **Local speech recognition** using Vosk for better privacy and reliability
- **Audio preprocessing** for noise reduction and voice activity detection
- **Multiple wake words** support
- **Conversation context** tracking
- **Response audio playback** integration with your existing MP3 player


wind: http://192.168.7.200:5000/play-audio-base64
raspi 1: http://192.168.7.141:5000/play-audio-base64
