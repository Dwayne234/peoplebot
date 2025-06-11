import os
import logging
import requests
from flask import Flask, request, jsonify
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

# Load environment variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
DO_AI_API_KEY = os.getenv("DO_AI_API_KEY")
DO_AI_ENDPOINT = os.getenv("DO_AI_ENDPOINT")

# Validate environment
if not SLACK_BOT_TOKEN or not SLACK_SIGNING_SECRET or not DO_AI_API_KEY or not DO_AI_ENDPOINT:
    raise ValueError("Missing environment variables.")

# Slack App setup
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
handler = SlackRequestHandler(app)

# Flask App
flask_app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.event("app_mention")
def handle_app_mention(body, say):
    try:
        user = body["event"]["user"]
        thread_ts = body["event"].get("thread_ts") or body["event"]["ts"]
        user_message = body["event"]["text"]

        say(text=":mag: Processing your request...", thread_ts=thread_ts)

        # Send message to DigitalOcean AI Agent
        headers = {
            "Authorization": f"Bearer {DO_AI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": user_message,
        }

        response = requests.post(DO_AI_ENDPOINT, headers=headers, json=payload)

        if response.status_code == 200:
            ai_reply = response.json().get("output", "I'm not sure how to respond.")
            say(text=ai_reply + " ☁️", thread_ts=thread_ts)
        else:
            error_msg = f":warning: Error contacting AI Agent: {response.status_code} {response.reason}"
            logging.error(error_msg)
            say(text=error_msg, thread_ts=thread_ts)

    except Exception as e:
        logging.exception("Unhandled exception in app_mention handler.")
        say(text=":warning: Oops! Something went wrong. A People Team member will follow up. ☁️", thread_ts=thread_ts)

# Slack route
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

# Health check route
@flask_app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})

# Start Flask app on correct port for DO App Platform
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)
