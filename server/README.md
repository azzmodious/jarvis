#
## Run
## Test
## Troubleshooting 
### Elevenlabs MP3 sending through http request node
Ah, that's a crucial detail! Thank you for sharing that correction. 

So the **actual working configuration** is:

**n8n HTTP Request Node:**
- **Method**: `POST`
- **URL**: `http://localhost:5000/play-audio-base64`
- **Headers**: `Content-Type: application/json`
- **Body Type**: `JSON`
- **Body**: `{{ $input.item.binary.data }}` ← **This was the key!**

This makes perfect sense - ElevenLabs was actually storing the base64 audio data in the **binary.data field**, not in the JSON payload. Your Flask `/play-audio-base64` endpoint was then treating that base64 string as JSON and successfully extracting and decoding it.

This is a really important distinction because:
- `={{ $json }}` would send the JSON metadata 
- `{{ $input.item.binary.data }}` sends the actual base64-encoded audio data

This correction will help anyone else trying to integrate ElevenLabs with a custom audio playback service. The audio data from ElevenLabs TTS is indeed stored in the binary data field, even when it's base64 encoded.

Thanks for the correction - that's the kind of detail that makes all the difference! 🎯