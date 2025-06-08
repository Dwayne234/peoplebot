import os
from flask import Flask, request, make_response
from slack_sdk.web import WebClient
from slack_sdk.signature import SignatureVerifier
import json

app = Flask(__name__)

slack_token = os.environ["SLACK_BOT_TOKEN"]
client = WebClient(token=slack_token)
signature_verifier = SignatureVerifier(os.environ["SLACK_SIGNING_SECRET"])

# Define what questions your bot should respond to
TRIGGER_KEYWORDS = ["vacation policy", "pto", "time off", "leave policy"]

@app.route("/", methods=["GET"])
def index():
    return "OK", 200

@app.route("/slack/events", methods=["POST"])
def slack_events():
    if not signature_verifier.is_valid_request(request.get_data(), request.headers):
        return make_response("Invalid request signature", 403)

    data = request.json
    if "challenge" in data:
        return make_response(data["challenge"], 200, {"content_type": "application/json"})

    # Respond to messages
    if data.get("event", {}).get("type") == "app_mention":
        event = data["event"]
        user = event.get("user")
        channel = event.get("channel")
        thread_ts = event.get("ts")
        text = event.get("text", "").lower()

        response_sent = False
        for keyword in TRIGGER_KEYWORDS:
            if keyword in text:
                client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=f"Hi <@{user}>! Here's what I found about *{keyword}*: … (custom answer)"
                )
                # ✅ Reaction = answered
                client.reactions_add(channel=channel, name="white_check_mark", timestamp=thread_ts)
                response_sent = True
                break

        if not response_sent:
            client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"Hi <@{user}>! I'm not sure how to answer that yet. A People Team member will follow up shortly. ☁️"
            )
            # ☁️ Reaction = escalate to human
            client.reactions_add(channel=channel, name="cloud", timestamp=thread_ts)

    return make_response("OK", 200)

# Run the app when this script is executed
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


