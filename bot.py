import os
import logging
import re
import requests
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

# Load environment variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
DO_AI_API_KEY = os.getenv("DO_AI_API_KEY")
DO_AI_ENDPOINT = os.getenv("DO_AI_ENDPOINT")

# Validate environment
if not SLACK_BOT_TOKEN or not SLACK_SIGNING_SECRET or not DO_AI_API_KEY or not DO_AI_ENDPOINT:
    raise ValueError("Missing one or more required environment variables.")

# Slack App setup
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
handler = SlackRequestHandler(app)

# Flask App setup
flask_app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Classify message for emoji
def classify_emoji(content):
    content = content.lower()
    if "i'm not sure" in content or "unsure" in content:
        return "speech_balloon"
    elif "please contact" in content or "human" in content or "escalate" in content:
        return "zap"
    elif "congratulations" in content or "thank you" in content:
        return "confetti_ball"
    elif "policy" in content or "benefit" in content:
        return "page_facing_up"
    else:
        return "a"

@app.event("app_mention")
def handle_app_mention(body, say, client):
    try:
        user = body["event"]["user"]
        thread_ts = body["event"].get("thread_ts") or body["event"]["ts"]
        raw_text = body["event"]["text"]
        bot_user_id = body["authorizations"][0]["user_id"]
        cleaned_text = re.sub(f"<@{bot_user_id}>", "", raw_text).strip()

        if not cleaned_text:
            say(text=":warning: Please include a question or comment.", thread_ts=thread_ts)
            return

        say(text=":mag: Processing your request...", thread_ts=thread_ts)

        headers = {
            "Authorization": f"Bearer {DO_AI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "messages": [{"role": "user", "content": cleaned_text}]
        }

        response = requests.post(DO_AI_ENDPOINT, headers=headers, json=payload)

        if response.status_code == 200:
            response_data = response.json()
            content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "I'm not sure how to respond.")
            posted = say(text=content, thread_ts=thread_ts)

            # React to the message
            emoji = classify_emoji(content)
            client.reactions_add(
                channel=body["event"]["channel"],
                name=emoji,
                timestamp=posted["ts"]
            )
        else:
            error_msg = f":warning: Error contacting AI Agent: {response.status_code} {response.reason}"
            logging.error(f"{error_msg} — Response: {response.text}")
            say(text=f"{error_msg}\nDetails: {response.text}", thread_ts=thread_ts)

    except Exception as e:
        logging.exception("Unhandled exception in app_mention handler.")
        say(text=":warning: Oops! Something went wrong. A People Team member will follow up. :cloud:", thread_ts=thread_ts)

# Slack events route
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

# Health check route
@flask_app.route("/", methods=["GET", "POST"])
def health_check():
    return "OK", 200

# Start Flask app on port 8080
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)
