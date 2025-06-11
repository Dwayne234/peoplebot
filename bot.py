import os
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier
import requests

app = Flask(__name__)

# Load from environment variables (set on App Platform)
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
DO_AI_ENDPOINT = os.getenv("DO_AI_ENDPOINT")
DO_AI_API_KEY = os.getenv("DO_AI_API_KEY")

client = WebClient(token=SLACK_BOT_TOKEN)
verifier = SignatureVerifier(SLACK_SIGNING_SECRET)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return "Invalid request", 403

    payload = request.json

    # Echo back the Slack URL verification challenge
    if "type" in payload and payload["type"] == "url_verification":
        return jsonify({"challenge": payload["challenge"]})

    # Handle message events
    if "event" in payload:
        event = payload["event"]
        if event.get("type") == "message" and not event.get("bot_id"):
            user_id = event.get("user")
            thread_ts = event.get("thread_ts") or event.get("ts")
            text = event.get("text")
            channel = event.get("channel")

            # Only respond if it's in a thread
            if thread_ts != event.get("ts"):
                # Call the /agent route
                response = requests.post(
                    "http://localhost:5000/agent",
                    json={"text": text, "user_id": user_id}
                )

                result = response.json()
                client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=f"{result['text']} ✅"
                )

    return "OK", 200

@app.route("/agent", methods=["POST"])
def agent():
    data = request.json
    user_message = data.get("text")
    user_id = data.get("user_id")

    try:
        agent_response = requests.post(
            DO_AI_ENDPOINT,
            headers={"Authorization": f"Bearer {DO_AI_API_KEY}"},
            json={"input": user_message}
        )

        agent_response.raise_for_status()
        response_json = agent_response.json()
        output = response_json.get("output", {})
        answer = output.get("answer", "")

        if answer:
            return jsonify({"text": f"{answer}"})
        else:
            return jsonify({"text": f"Hi <@{user_id}>! I'm not sure how to answer that yet. A People Team member will follow up. :cloud:"})
    except Exception as e:
        return jsonify({"text": f"Hi <@{user_id}>! There was an error contacting the AI Agent. :warning:\nError: {e}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
