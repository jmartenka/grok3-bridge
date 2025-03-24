import json
import logging
import threading
import time
import uuid

from flask import Flask, Response, jsonify, request, stream_with_context
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("grok3-bridge")

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": "*", "expose_headers": "*"}})

# Initialize Socket.IO
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
    async_mode="threading",
    always_connect=True,
    logger=True,
    engineio_logger=True,
)

# In-memory storage
responses = {}
streaming_responses = {}

# Global constants
TIMEOUT = 60  # seconds


@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response


@socketio.on("connect")
def handle_connect():
    """Handle client connection"""
    logger.info("Plugin connected")


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("Plugin disconnected")


@socketio.on("response")
def handle_response(data):
    """Handle response from the plugin"""
    logger.info(f"Received response from Grok: {data[:100]}..." if data else "Empty response")

    # Get request ID
    request_id = getattr(socketio, "request_id", "default")

    # Store response
    responses[request_id] = data

    # Update streaming response if applicable
    if request_id in streaming_responses:
        streaming_responses[request_id]["complete"] = True
        streaming_responses[request_id]["text"] = data

    # Notify waiting clients
    socketio.emit(f"response_{request_id}", data)


@socketio.on_error()
def handle_error(e):
    """Handle Socket.IO errors"""
    logger.error(f"Socket.IO error: {str(e)}")


def format_openai_streaming_chunk(chunk_id, model, content, is_first=False, is_last=False):
    """Format a chunk for OpenAI streaming API"""
    if is_first:
        data = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": content}, "finish_reason": None}],
        }
    elif is_last:
        data = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
    else:
        data = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
        }

    return f"data: {json.dumps(data)}\n\n"


def format_prompt_from_messages(messages):
    """Format OpenAI messages into a prompt for Grok"""
    prompt = ""
    system_content = ""

    # Extract system messages
    for msg in messages:
        if msg.get("role") == "system":
            system_content += msg.get("content", "") + "\n"

    # Add system content
    if system_content:
        prompt += f"System: {system_content.strip()}\n\n"

    # Add user and assistant messages
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")

        if role == "system":
            continue  # Already handled
        elif role == "user":
            prompt += f"User: {content}\n\n"
        elif role == "assistant":
            prompt += f"Assistant: {content}\n\n"

    return prompt.strip()


@app.route("/v1/chat/completions", methods=["POST", "OPTIONS"])
def chat_completions():
    """OpenAI-compatible chat completions endpoint"""
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,PUT,POST,DELETE,OPTIONS"
        return response

    try:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        socketio.request_id = request_id
        response_id = f"chatcmpl-{request_id.replace('-', '')}"

        # Process request data
        data = request.json
        messages = data.get("messages", [])
        model = data.get("model", "grok-3")
        stream = data.get("stream", False)

        # Format prompt for Grok
        prompt = format_prompt_from_messages(messages)

        # Send request to plugin
        socketio.emit("request", prompt)
        logger.info(f"Sent request to plugin: {prompt[:100]}...")

        # Handle streaming mode
        if stream:
            return handle_streaming_request(request_id, response_id, model)

        # Handle regular mode
        return handle_regular_request(request_id, response_id, model)

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500


def handle_streaming_request(request_id, response_id, model):
    """Handle streaming response mode"""
    # Initialize streaming response
    streaming_responses[request_id] = {"complete": False, "text": "", "chunks_sent": 0}

    def generate_stream():
        # Send initial chunk with role
        yield format_openai_streaming_chunk(response_id, model, "", is_first=True)

        # Track state
        start_time = time.time()
        last_text_length = 0

        # Wait for response with timeout
        while time.time() - start_time < TIMEOUT:
            # Check for complete response
            if request_id in streaming_responses and streaming_responses[request_id]["complete"]:
                full_text = streaming_responses[request_id]["text"]

                # Process line by line for better streaming visualization
                if last_text_length < len(full_text):
                    remaining_text = full_text[last_text_length:]

                    # Check if there are newlines to split into chunks
                    if "\n" in remaining_text:
                        lines = remaining_text.split("\n")
                        for line in lines:
                            if line.strip():
                                yield format_openai_streaming_chunk(response_id, model, line + "\n")
                                time.sleep(0.1)  # Add a small delay for better visualization
                        last_text_length = len(full_text)
                    else:
                        # No newlines, send as one chunk
                        yield format_openai_streaming_chunk(response_id, model, remaining_text)
                        last_text_length = len(full_text)

                # Send completion
                yield format_openai_streaming_chunk(response_id, model, "", is_last=True)
                yield "data: [DONE]\n\n"
                break

            # Check for partial response
            if request_id in responses:
                current_text = responses[request_id]

                # If new content is available, process it
                if len(current_text) > last_text_length:
                    new_content = current_text[last_text_length:]

                    # Check if there are newlines to split into chunks
                    if "\n" in new_content:
                        lines = new_content.split("\n")
                        for line in lines:
                            if line.strip():
                                yield format_openai_streaming_chunk(response_id, model, line + "\n")
                                time.sleep(0.1)  # Add a small delay for better visualization
                        last_text_length = len(current_text)
                    else:
                        # No newlines, send as one chunk
                        yield format_openai_streaming_chunk(response_id, model, new_content)
                        last_text_length = len(current_text)

            time.sleep(0.1)

        # Clean up
        if request_id in streaming_responses:
            del streaming_responses[request_id]
        if request_id in responses:
            del responses[request_id]

    return Response(stream_with_context(generate_stream()), content_type="text/event-stream")


def handle_regular_request(request_id, response_id, model):
    """Handle regular (non-streaming) response mode"""
    # Wait for the full response
    start_time = time.time()

    while time.time() - start_time < TIMEOUT:
        if request_id in responses:
            response_text = responses.pop(request_id)

            # Format OpenAI response
            response = {
                "id": response_id,
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": response_text}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": -1, "completion_tokens": -1, "total_tokens": -1},
            }

            return jsonify(response)

        time.sleep(0.1)

    # Timeout
    return jsonify({"error": "Response timeout"}), 504


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    # Get connection info safely
    try:
        rooms = socketio.server.manager.rooms.get("/", {})
        # Convert rooms dict to something safely serializable
        connections = {"count": len(rooms), "sids": list(rooms.keys()) if rooms else []}
    except Exception as e:
        logger.error(f"Error getting connection info: {str(e)}")
        connections = {"count": 0, "error": str(e)}

    return jsonify({"status": "ok", "version": "1.0", "connections": connections})


@app.route("/v1/models", methods=["GET"])
def list_models():
    """OpenAI-compatible models endpoint"""
    models = {
        "object": "list",
        "data": [{"id": "grok-3", "object": "model", "created": int(time.time()), "owned_by": "x.ai"}],
    }
    return jsonify(models)


if __name__ == "__main__":
    logger.info("Starting Grok3 Bridge server at http://localhost:5000")
    logger.info("Make sure to install the Firefox plugin and visit grok.com")

    socketio.run(app, host="localhost", port=5001, debug=True, allow_unsafe_werkzeug=True)
