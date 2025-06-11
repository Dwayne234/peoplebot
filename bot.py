import os
import json
import requests
from flask import Flask, request, make_response
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier

# Environment Variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
DO_AI_API_KEY = os.getenv("DO_AI_API_KEY")
DO_AI_ENDPOINT = os.getenv("DO_AI_ENDPOINT")

# Slack client and signature verifier
client = WebClient(token=SLACK_BOT_TOKEN)
verifier = SignatureVerifier(SLACK_SIGNING_SECRET)

# Flask app
app = Flask(__name__)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return make_response("Invalid request", 403)

    payload = request.json
    event = payload.get("event", {})

    # Only respond to app_mention events
    if event.get("type") == "app_mention":
        user = event.get("user")
        text = event.get("text")
        channel = event.get("channel")
        thread_ts = event.get("thread_ts") or event.get("ts")

        # Respond to thread with thinking emoji
        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=":mag: Processing your request..."
        )

        # Strip bot mention from text
        cleaned_text = text.split('>', 1)[-1].strip()

        # Call DigitalOcean AI Agent
        try:
            response = requests.post(
                DO_AI_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {DO_AI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={"input": cleaned_text}
            )
            response.raise_for_status()
            result = response.json()
            answer = result.get("output", "I'm not sure how to answer that yet. A People Team member will follow up. :cloud:")

        except Exception as e:
            answer = f":warning: Error contacting AI Agent: {str(e)}"

        # Reply in the same thread
        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=answer
        )

    return make_response("", 200)

@app.route("/", methods=["GET"])
def health_check():
    return "Bot is running!", 200

if __name__ == "__main__":
    app.run(debug=False, port=5000)
