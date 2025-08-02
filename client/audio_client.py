from flask import Flask, request, jsonify
import tempfile
import base64
import os
import pygame
import threading
from werkzeug.utils import secure_filename
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure upload settings
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'mp4', 'm4a', 'flac', 'aac'}

# Initialize pygame mixer for audio playback
pygame.mixer.init()

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def play_audio_file(file_path):
    """Play audio file using pygame mixer."""
    try:
        logger.info(f"Loading audio file: {file_path}")
        pygame.mixer.music.load(file_path)
        
        logger.info("Starting audio playback")
        pygame.mixer.music.play()
        
        # Wait for playback to complete
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
            
        logger.info("Audio playback completed")
        
    except Exception as e:
        logger.error(f"Error playing audio: {str(e)}")
    finally:
        # Clean up the temporary file
        try:
            os.unlink(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up file: {str(e)}")

@app.route('/play-audio-raw', methods=['POST'])
def play_audio_raw():
    """Endpoint to receive raw audio data or base64 encoded data."""
    try:
        # Get raw audio data from request body
        audio_data = request.data
        
        if not audio_data:
            return jsonify({'error': 'No audio data provided'}), 400
        
        logger.info(f"Received raw data: {len(audio_data)} bytes")
        logger.info(f"Content-Type: {request.content_type}")
        
        # Check if this looks like base64 data
        try:
            # Try to decode as text first
            data_str = audio_data.decode('utf-8')
            
            # Check if it looks like base64
            if len(data_str) > 100 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in data_str.strip()):
                logger.info("Data appears to be base64 encoded, attempting to decode...")
                
                # Remove data URL prefix if present
                if ',' in data_str and data_str.startswith('data:'):
                    data_str = data_str.split(',', 1)[1]
                
                # Decode base64
                audio_bytes = base64.b64decode(data_str)
                logger.info(f"Successfully decoded base64 to {len(audio_bytes)} bytes")
                
            else:
                # Use raw binary data
                audio_bytes = audio_data
                
        except (UnicodeDecodeError, base64.binascii.Error):
            # Not text/base64, use as raw binary
            audio_bytes = audio_data
        
        # Determine file extension based on content type or default to mp3
        content_type = request.content_type or 'audio/mpeg'
        if 'wav' in content_type:
            file_ext = '.wav'
        elif 'ogg' in content_type:
            file_ext = '.ogg'
        elif 'mp4' in content_type:
            file_ext = '.mp4'
        else:
            file_ext = '.mp3'  # Default for ElevenLabs
        
        # Create a temporary file to store the audio data
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name
        
        logger.info(f"Saved audio to temporary file: {temp_file_path}")
        
        # Play the audio file in a separate thread
        audio_thread = threading.Thread(target=play_audio_file, args=(temp_file_path,))
        audio_thread.daemon = True
        audio_thread.start()
        
        return jsonify({
            'status': 'success',
            'message': f'Audio data ({len(audio_bytes)} bytes) is now playing',
            'file_type': file_ext,
            'was_base64': len(audio_data) != len(audio_bytes)
        }), 200
        
    except Exception as e:
        logger.error(f"Error in play_audio_raw endpoint: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/play-audio-base64', methods=['POST'])
def play_audio_base64():
    """Endpoint to receive base64 encoded audio data."""
    try:
        # Get JSON data from request
        json_data = request.get_json()
        
        if not json_data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Look for base64 audio data in common field names
        base64_audio = None
        audio_field = None
        
        possible_fields = ['audio', 'data', 'audio_base64', 'speech', 'content', 'file']
        
        for field in possible_fields:
            if field in json_data and json_data[field]:
                base64_audio = json_data[field]
                audio_field = field
                break
        
        if not base64_audio:
            return jsonify({
                'error': 'No base64 audio data found',
                'available_fields': list(json_data.keys())
            }), 400
        
        logger.info(f"Found base64 audio data in field '{audio_field}'")
        logger.info(f"Base64 string length: {len(base64_audio)} characters")
        
        # Decode base64 audio data
        try:
            # Remove data URL prefix if present (e.g., "data:audio/mpeg;base64,")
            if ',' in base64_audio and base64_audio.startswith('data:'):
                base64_audio = base64_audio.split(',', 1)[1]
            
            audio_bytes = base64.b64decode(base64_audio)
            logger.info(f"Decoded audio size: {len(audio_bytes)} bytes")
            
        except Exception as e:
            return jsonify({'error': f'Failed to decode base64: {str(e)}'}), 400
        
        # Determine file extension
        file_ext = '.mp3'  # Default
        content_type = request.content_type or ''
        if 'wav' in content_type:
            file_ext = '.wav'
        elif 'ogg' in content_type:
            file_ext = '.ogg'
        
        # Create temporary file and save decoded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name
        
        logger.info(f"Saved decoded audio to: {temp_file_path}")
        
        # Play the audio file in a separate thread
        audio_thread = threading.Thread(target=play_audio_file, args=(temp_file_path,))
        audio_thread.daemon = True
        audio_thread.start()
        
        return jsonify({
            'status': 'success',
            'message': f'Base64 audio data decoded and playing ({len(audio_bytes)} bytes)',
            'source_field': audio_field,
            'file_type': file_ext
        }), 200
        
    except Exception as e:
        logger.error(f"Error in play_audio_base64 endpoint: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/play-audio', methods=['POST'])
def play_audio():
    """Endpoint to receive and play audio files."""
    try:
        # Debug: Log what we received
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Files: {list(request.files.keys())}")
        logger.info(f"Form data: {list(request.form.keys())}")
        logger.info(f"Request data length: {len(request.data)}")
        
        # Check if a file was uploaded
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed. Supported formats: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Create a temporary file to store the uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file.filename.rsplit(".", 1)[1].lower()}') as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        logger.info(f"Received audio file: {file.filename}")
        logger.info(f"Saved to temporary file: {temp_file_path}")
        
        # Play the audio file in a separate thread to avoid blocking the response
        audio_thread = threading.Thread(target=play_audio_file, args=(temp_file_path,))
        audio_thread.daemon = True
        audio_thread.start()
        
        return jsonify({
            'status': 'success',
            'message': f'Audio file "{file.filename}" is now playing',
            'filename': file.filename
        }), 200
        
    except Exception as e:
        logger.error(f"Error in play_audio endpoint: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/status', methods=['GET'])
def status():
    """Health check endpoint."""
    return jsonify({
        'status': 'running',
        'message': 'Flask Audio Player Service is active',
        'supported_formats': list(ALLOWED_EXTENSIONS)
    }), 200

@app.route('/debug-request', methods=['POST'])
def debug_request():
    """Debug endpoint to see exactly what we're receiving."""
    try:
        logger.info("=== DEBUG REQUEST ===")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Content-Length: {request.content_length}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Files: {list(request.files.keys())}")
        logger.info(f"Form data: {list(request.form.keys())}")
        logger.info(f"Raw data length: {len(request.data)}")
        logger.info(f"Raw data preview: {request.data[:100]}")  # First 100 bytes
        
        return jsonify({
            'content_type': request.content_type,
            'content_length': request.content_length,
            'files': list(request.files.keys()),
            'form_keys': list(request.form.keys()),
            'raw_data_length': len(request.data),
            'headers': dict(request.headers)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stop-audio', methods=['POST'])
def stop_audio():
    """Endpoint to stop currently playing audio."""
    try:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            logger.info("Audio playback stopped")
            return jsonify({'status': 'success', 'message': 'Audio playback stopped'}), 200
        else:
            return jsonify({'status': 'info', 'message': 'No audio currently playing'}), 200
    except Exception as e:
        logger.error(f"Error stopping audio: {str(e)}")
        return jsonify({'error': f'Error stopping audio: {str(e)}'}), 500

if __name__ == '__main__':
    print("Starting Flask Audio Player Service...")
    print("Endpoints available:")
    print("  POST /play-audio - Upload and play audio file")
    print("  GET  /status     - Check service status")
    print("  POST /stop-audio - Stop currently playing audio")
    print(f"Supported audio formats: {', '.join(ALLOWED_EXTENSIONS)}")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)