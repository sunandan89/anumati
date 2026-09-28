"""One Sarvam chat completion, to check the API key works. Run from the repo root:
    python3 tools/sarvam_hello.py
Reads SARVAM_API_KEY from the environment, or from .env in the repo root. Never prints the key."""
import os

from sarvamai import SarvamAI

ENV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

key = os.environ.get("SARVAM_API_KEY")
if not key and os.path.exists(ENV):
    for line in open(ENV):
        name, _, value = line.strip().partition("=")
        if name == "SARVAM_API_KEY":
            key = value.strip().strip('"').strip("'")
if not key:
    raise SystemExit("SARVAM_API_KEY is not set. Put it in .env (SARVAM_API_KEY=...) and run again.")

client = SarvamAI(api_subscription_key=key)
reply = client.chat.completions(
    model="sarvam-105b-conversations",
    messages=[{"role": "user", "content": "Namaste! Ek line mein batao: aap kaun ho?"}],
)
print(reply.choices[0].message.content)
