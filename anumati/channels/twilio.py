"""Twilio adapter: SMS and WhatsApp out, signature check for inbound webhooks (WhatsApp, voice).

Channel Provider fields: API key = Account SID, API secret = Auth Token, Sender ID = the Twilio number
(for the WhatsApp sandbox, +14155238886). Inbound webhooks are signed by Twilio with the Auth Token
(X-Twilio-Signature); Anumati also requires its own inbound secret in the URL."""

import base64
import hashlib
import hmac

import frappe
import requests

API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


def _address(number: str, channel: str) -> str:
	digits = "".join(ch for ch in number or "" if ch.isdigit())
	e164 = "+" + ("91" + digits if len(digits) == 10 else digits)
	return f"whatsapp:{e164}" if channel == "whatsapp" else e164


def send_text(provider, phone_digits: str, body: str, channel="sms") -> str | None:
	sid = provider.get_password("api_key")
	response = requests.post(
		API.format(sid=sid), auth=(sid, provider.get_password("api_secret")),
		data={"From": _address(provider.sender_id, channel), "To": _address(phone_digits, channel), "Body": body},
		timeout=10,
	)
	response.raise_for_status()
	return (response.json() if response.content else {}).get("sid")


def send(provider, phone_digits: str, template, context: dict) -> str | None:
	"""Gateway interface (same as msg91.send): render the approved template and send it."""
	channel = "whatsapp" if provider.provider_type == "WhatsApp" else "sms"
	return send_text(provider, phone_digits, frappe.render_template(template.body, context), channel)


def signature(auth_token: str, url: str, params: dict) -> str:
	"""Twilio's scheme: base64(HMAC-SHA1(auth_token, url + each POST param name+value, sorted by name))."""
	payload = url + "".join(f"{k}{params[k]}" for k in sorted(params))
	return base64.b64encode(hmac.new(auth_token.encode(), payload.encode(), hashlib.sha1).digest()).decode()


def check_signature(provider, params: dict):
	"""Reject a webhook that Twilio did not sign. The URL is the public site URL plus the path and query
	Twilio called, which is what Twilio signs."""
	token = provider.get_password("api_secret", raise_exception=False)
	given = frappe.get_request_header("X-Twilio-Signature") or ""
	url = frappe.utils.get_url() + frappe.request.full_path.rstrip("?") if frappe.request else ""
	if not (token and given and hmac.compare_digest(signature(token, url, params), given)):
		frappe.throw("Twilio signature missing or invalid", frappe.PermissionError)
