import os
import json
import requests
from flask import Flask, request, make_response
from slack_sdk.web import WebClient
from slack_sdk.signature import SignatureVerifier

app = Flask(__name__)

# Slack credentials
slack_token = os.environ["SLACK_BOT_TOKEN"]
signing_secret = os.environ["SLACK_SIGNING_SECRET"]
client = WebClient(token=slack_token)
signature_verifier = SignatureVerifier(signing_secret)

# DO MCP AI Agent credentials from environment variables
DO_AI_ENDPOINT = os.environ.get("DO_AI_ENDPOINT")
DO_AI_API_KEY = os.environ.get("DO_AI_API_KEY")

# Keywords to auto-answer with canned responses
TRIGGER_KEYWORDS = ["vacation policy", "pto", "time off", "leave policy"]

@app.route("/", methods=["GET"])
def index():
    return "OK", 200

@app.route("/slack/events", methods=["POST"])
def slack_events():
    if not signature_verifier.is_valid_request(request.get_data(), request.headers):
        return make_response("Invalid request signature", 403)

    data = request.json

    # Slack challenge verification
    if "challenge" in data:
        return make_response(data["challenge"], 200, {"content_type": "application/json"})

    if data.get("event", {}).get("type") == "app_mention":
        event = data["event"]
        user = event.get("user")
        channel = event.get("channel")
        thread_ts = event.get("ts")
        text = event.get("text", "")

        # Ask DigitalOcean AI Agent
        answer = ask_ai_agent(text)

        if answer:
            client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"Hi <@{user}>! Here's what I found:\n\n{answer}"
            )
            client.reactions_add(channel=channel, name="white_check_mark", timestamp=thread_ts)
        else:
            client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"Hi <@{user}>! I'm not sure how to answer that yet. A People Team member will follow up. ☁️"
            )
            client.reactions_add(channel=channel, name="cloud", timestamp=thread_ts)

    return make_response("OK", 200)

def ask_ai_agent(question: str) -> str:
    if not DO_AI_ENDPOINT or not DO_AI_API_KEY:
        return "AI agent configuration is missing."

    try:
        headers = {
            "Authorization": f"Bearer {DO_AI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {"input": question}
        response = requests.post(DO_AI_ENDPOINT, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            return data.get("output", "Sorry, I couldn’t understand that.")
        else:
            print(f"Error from AI Agent: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception during AI call: {e}")
        return None

# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
