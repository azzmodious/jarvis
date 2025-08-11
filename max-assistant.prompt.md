# Max Assistant Prompt
This is a simple voice assistant that listens for a wake word, captures your command, and sends it to an n8n webhook for further processing.
** Functionality includes:
- When the application starts, a startup sound plays.
  - Supported sound file formats: mp3, wav, ogg
  - The startup sound file can be configured in `config.yaml`
  - It should send a notification to the n8n webhook indicating that the assistant is online.
    -- The webhook URL is 'https://n8n.casa-bakewell.com/webhook-test/startup'
    -- The startup notification should include:
        - Action: "startup"
        - Text: "Voice assistant is now online."
        - Timestamp
        - Client ID (IP address of the client)
    -- JSON payload should be like:
        ```json
            { 
                "content":
                {
                    "action": "startup",
                    "text": "Voice assistant is now online.",
                    "timestamp": 1642765432.123,
                    "client_id": <client_ip_address>
                }
            }
        ```
- The application should have a REST endpoint ("/prompt") that can be called to listen for voice input without requiring a wake word. Once the voice input is captured, it should be processed as a command.
  - When the "/prompt" endpoint is called an event should be triggered. This event should be configurable in `config.yaml` and should invode an HTTP webhook or python script. 
  - The endpoint should accept a POST request with a JSON body containing the command to be executed.
  - The command should be processed and sent to the n8n webhook (https://n8n.casa-bakewell.com/webhook-test/process_input)
  - The input JSON payload for the command should be like:
    ```json
    { 
        "content":
        {   "prompt": "What color would you like the lights to be?",
            "wait_for_response": true,
            "timestamp": 1642765432.123,
            "client_id": < client_ip_address >
        }
    }
    ```
  - The application should respond to the POST request with a JSON response indicating that the command was received and is being processed.
    ```json
    {
        "status": "success",
        "message": "Command received and is being processed."
    }
    ```
- The application listens for a wake word, which defaults to "jarvis".
- When the wake word is detected, an acknowledgment sound plays.
  - Supported sound file formats: mp3, wav, ogg
  - The acknowledgment sound file can be configured in `config.yaml`
- When commands is captured, a command acknowledgment sound plays.
  - Supported sound file formats: mp3, wav, ogg
  - The command acknowledgment sound file can be configured in `config.yaml`
- When the stop phrase is detected, a stop acknowledgment sound plays.
  - Supported sound file formats: mp3, wav, ogg
  - The stop acknowledgment sound file can be configured in `config.yaml`

** Technical Requirements:
- This application must be built using Python 3.
- It must run on Raspberry Pi, Linux, and Windows systems.


** Documentation Requirements:

** Installation Requirements: