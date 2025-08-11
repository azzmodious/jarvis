#!/bin/bash

# Voice Assistant Setup Script
echo "Setting up Voice Recognition Assistant..."

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "Error: Conda is not installed. Please install Miniconda or Anaconda first."
    echo "Download from: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Create conda environment
echo "Creating conda environment 'voice-assistant'..."
conda env create -f environment.yml

# Activate environment
echo "Activating environment..."
conda activate voice-assistant

# Install system dependencies based on OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Installing Linux audio dependencies..."
    sudo apt-get update
    sudo apt-get install -y portaudio19-dev python3-pyaudio alsa-utils
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Installing macOS audio dependencies..."
    if command -v brew &> /dev/null; then
        brew install portaudio
    else
        echo "Homebrew not found. Please install portaudio manually."
    fi
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "Windows detected. PyAudio should install automatically."
fi

# Install additional Python packages if needed
echo "Installing additional Python packages..."
pip install --upgrade pip

# Note about MP3 support
echo ""
echo "Note: MP3 support depends on system codecs."
echo "If MP3 files don't work, try converting to WAV format"
echo "or install additional codecs for your system."

# Test microphone access
echo "Testing microphone access..."
python3 -c "
import speech_recognition as sr
r = sr.Recognizer()
with sr.Microphone() as source:
    print('Microphone test passed!')
    r.adjust_for_ambient_noise(source)
    print('Ambient noise adjustment completed.')
"

echo ""
echo "Setup complete!"
echo ""
echo "To use the voice assistant:"
echo "1. conda activate voice-assistant"
echo "2. python3 voice_assistant.py"
echo ""
echo "Configuration file: config.yaml"
echo "Log file: voice_assistant.log"