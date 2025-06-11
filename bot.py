import os
import requests
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

# Environment Variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
DO_AI_API_KEY = os.getenv("DO_AI_API_KEY")
DO_AI_ENDPOINT = os.getenv("DO_AI_ENDPOINT")

# Slack App Initialization
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)

# Flask Server
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

# Listen for mentions in thread
@app.event("app_mention")
def handle_mention_events(body, say, logger):
    try:
        event = body.get("event", {})
        user = event.get("user")
        thread_ts = event.get("thread_ts") or event.get("ts")
        text = event.get("text")

        say(text=":mag: Processing your request...", thread_ts=thread_ts)

        prompt = text.replace(f"<@{event.get('bot_id', '')}>", "").strip()

        headers = {
            "Authorization": f"Bearer {DO_AI_API_KEY}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            f"{DO_AI_ENDPOINT}/invoke",
            headers=headers,
            json={"input": prompt},
            timeout=30
        )

        if response.status_code == 200:
            ai_response = response.json().get("output", "No response from AI.")
            say(text=ai_response, thread_ts=thread_ts)
        else:
            logger.error(f"AI error: {response.status_code} - {response.text}")
            say(text=f":warning: Error contacting AI Agent: {response.status_code} - {response.reason}", thread_ts=thread_ts)

    except Exception as e:
        logger.error(f"Exception: {e}")
        say(text=f":warning: An error occurred: {e}", thread_ts=thread_ts)

# Flask route for Slack events
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

# Flask health check endpoint
@flask_app.route("/", methods=["GET"])
def health_check():
    return "OK", 200

# Entry point for App Platform (use port 8080 and host 0.0.0.0)
if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=8080)
