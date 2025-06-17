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

def select_emoji_prefix(user_message: str, ai_reply: str) -> str:
    """
    Return appropriate emoji prefix based on user message or AI response context.
    """

    msg = user_message.lower()

    # Mapping based on your legend and use cases
    if any(word in msg for word in ["help", "human", "agent", "verify", "follow up", "question"]):
        # Ask human to help or verify
        return "⚡️ "  # Thunderbolt (Human help needed)

    if any(word in msg for word in ["email", "contact", "message"]):
        return "✉️ "  # Envelope (Email related)

    if any(word in msg for word in ["phone", "call", "ring"]):
        return "📞 "  # Telephone (Phone call related)

    if any(word in msg for word in ["calendar", "meeting", "appointment", "schedule"]):
        return "📅 "  # Calendar

    if any(word in msg for word in ["vacation", "leave", "pto", "time off", "holiday"]):
        return "🏖️ "  # Beach with umbrella (Vacation/leave)

    if any(word in msg for word in ["birthday", "congratulations", "congrats", "baby", "celebrate"]):
        return "🎉 "  # Party popper (Celebration)

    if any(word in msg for word in ["error", "problem", "issue", "fail", "not working"]):
        return "⚠️ "  # Warning (Error)

    if any(word in msg for word in ["waiting", "thinking", "processing", "loading", "wait"]):
        return "🔍 "  # Magnifying glass (Processing)

    if any(word in msg for word in ["approved", "confirmed", "yes", "ok", "done", "success"]):
        return "✅ "  # Checkmark (Success)

    if any(word in msg for word in ["declined", "no", "cancel", "denied"]):
        return "❌ "  # Cross mark (Negative)

    if any(word in msg for word in ["info", "information", "policy", "document", "handbook", "guide"]):
        return "📄 "  # Document (Information)

    if any(word in msg for word in ["cloud", "system", "platform", "digitalocean"]):
        return "☁️ "  # Cloud (Default)

    # Default fallback emoji
    return "☁️ "

@app.event("app_mention")
def handle_app_mention(body, say):
    try:
        user = body["event"]["user"]
        thread_ts = body["event"].get("thread_ts") or body["event"]["ts"]
        raw_text = body["event"]["text"]

        # Clean bot mention from message text
        bot_user_id = body["authorizations"][0]["user_id"]
        cleaned_text = re.sub(f"<@{bot_user_id}>", "", raw_text).strip()

        # Processing message with magnifying glass emoji
        say(text="🔍 Processing your request...", thread_ts=thread_ts)

        # Prepare headers and payload for DO AI Agent
        headers = {
            "Authorization": f"Bearer {DO_AI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": cleaned_text,
        }

        response = requests.post(DO_AI_ENDPOINT, headers=headers, json=payload)

        if response.status_code == 200:
            response_data = response.json()
            ai_reply = response_data.get("output") or response_data.get("message") or "I'm not sure how to respond."

            emoji_prefix = select_emoji_prefix(cleaned_text, ai_reply)
            say(text=f"{emoji_prefix}{ai_reply}", thread_ts=thread_ts)

        else:
            error_msg = f"⚠️ Error contacting AI Agent: {response.status_code} {response.reason}"
            logging.error(f"{error_msg} — Response: {response.text}")
            say(text=f"{error_msg}\nDetails: {response.text}", thread_ts=thread_ts)

    except Exception as e:
        logging.exception("Unhandled exception in app_mention handler.")
        say(text="⚡️ Oops! Something went wrong. A People Team member will follow up. ☁️", thread_ts=thread_ts)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

@flask_app.route("/", methods=["GET", "POST"])
def health_check():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)
