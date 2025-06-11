import os
import requests
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier

app = Flask(__name__)

# Environment Variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
DO_AI_API_KEY = os.getenv("DO_AI_API_KEY")
DO_AI_ENDPOINT = os.getenv("DO_AI_ENDPOINT")

client = WebClient(token=SLACK_BOT_TOKEN)
verifier = SignatureVerifier(SLACK_SIGNING_SECRET)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    if not verifier.is_valid_request(request.get_data(), request.headers):
        return "Invalid request", 403

    payload = request.json

    # Slack verification challenge
    if payload.get("type") == "url_verification":
        return jsonify({"challenge": payload.get("challenge")})

    # Handle event
    event = payload.get("event", {})
    if event.get("type") == "app_mention" and not event.get("bot_id"):
        user_id = event.get("user")
        text = event.get("text")
        channel = event.get("channel")
        thread_ts = event.get("thread_ts") or event.get("ts")

        # Send debug reply
        client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=":mag: Processing your request..."
        )

        try:
            ai_response = requests.post(
                DO_AI_ENDPOINT,
                headers={"Authorization": f"Bearer {DO_AI_API_KEY}"},
                json={"input": text}
            )

            ai_response.raise_for_status()
            output = ai_response.json().get("output", {})
            answer = output.get("answer", "")

            if answer:
                client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=f"{answer} ✅"
                )
            else:
                client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=f"Hi <@{user_id}>! I'm not sure how to answer that yet. A People Team member will follow up. :cloud:"
                )
        except Exception as e:
            client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"⚠️ Error contacting AI Agent: {str(e)}"
            )

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
