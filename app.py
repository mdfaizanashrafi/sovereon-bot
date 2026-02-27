from flask import Flask, request
import requests
import os
from supabase import create_client

app = Flask(__name__)

# Environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# Webhook Verification
# -----------------------------
@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403


# -----------------------------
# Receive Instagram Messages
# -----------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if data.get("object") == "instagram":
        for entry in data.get("entry", []):
            for messaging in entry.get("messaging", []):
                if "message" in messaging:
                    sender_id = messaging["sender"]["id"]
                    text = messaging["message"].get("text", "")
                    response = generate_response(text)

                    send_message(sender_id, response)
                    log_conversation(sender_id, text, response)

    return "OK", 200


# -----------------------------
# OpenRouter AI
# -----------------------------
def generate_response(user_message):

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "meta-llama/llama-3.1-8b-instruct",
        "messages": [
            {"role": "system", "content": "You are a professional Instagram assistant. Keep responses short and friendly."},
            {"role": "user", "content": user_message}
        ]
    }

    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload
    )

    return r.json()["choices"][0]["message"]["content"]


# -----------------------------
# Send Instagram Message
# -----------------------------
def send_message(recipient_id, message):
    url = "https://graph.facebook.com/v18.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message},
        "messaging_type": "RESPONSE"
    }
    params = {"access_token": PAGE_ACCESS_TOKEN}

    requests.post(url, json=payload, params=params)


# -----------------------------
# Save Conversation
# -----------------------------
def log_conversation(user_id, message, response):
    supabase.table("conversations").insert({
        "user_id": user_id,
        "message": message,
        "response": response
    }).execute()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)