"""MSG91 adapter. Two MSG91 services:

- Flow API (default): the Message Template's "MSG91 template ID" is the flow/template registered against
  the DLT template; template variables are passed as var1..varN in the order the context lists them,
  plus named keys for flows that use names.
- SendOTP API (Message Template "Send via" = SendOTP): for an approved OTP template such as
  "Your OTP is ##OTP##". Anumati makes the code and passes it as `otp`, so it is still checked (and
  audited) by Anumati, never by MSG91.

The API key is the Channel Provider's, or `msg91_auth_key` in the site config."""

import frappe
import requests

API = "https://control.msg91.com/api/v5/flow"
OTP_API = "https://control.msg91.com/api/v5/otp"
VARS = ("code", "programme", "purposes", "date", "otp")
OTP_EXPIRY_MINUTES = 10


def _auth(provider) -> str:
	return provider.get_password("api_key", raise_exception=False) or frappe.conf.get("msg91_auth_key") or ""


def _mobile(phone_digits: str) -> str:
	return "91" + phone_digits if len(phone_digits) == 10 else phone_digits


def send(provider, phone_digits: str, template, context: dict) -> str | None:
	if template.get("send_via") == "SendOTP":
		return _send_otp(provider, phone_digits, template, context)
	recipient = {"mobiles": _mobile(phone_digits)}
	for i, key in enumerate(VARS, start=1):
		if context.get(key) is not None:
			recipient[f"var{i}"] = str(context[key])
			recipient[key] = str(context[key])
	response = requests.post(
		API,
		headers={"authkey": _auth(provider), "accept": "application/json", "content-type": "application/json"},
		json={"template_id": template.dlt_template_id, "short_url": "0", "recipients": [recipient]},
		timeout=10,
	)
	response.raise_for_status()
	data = response.json() if response.content else {}
	if data.get("type") == "error":
		raise RuntimeError("MSG91 rejected the message")
	return data.get("request_id") or data.get("message")


def _send_otp(provider, phone_digits: str, template, context: dict) -> str | None:
	if not context.get("otp"):
		raise ValueError("SendOTP templates carry only a one-time code")
	response = requests.post(
		OTP_API,
		headers={"authkey": _auth(provider), "accept": "application/json", "content-type": "application/json"},
		params={"template_id": template.dlt_template_id, "mobile": _mobile(phone_digits), "otp": str(context["otp"]),
		        "otp_expiry": OTP_EXPIRY_MINUTES},
		timeout=10,
	)
	response.raise_for_status()
	data = response.json() if response.content else {}
	if data.get("type") == "error":
		raise RuntimeError("MSG91 rejected the code")
	return data.get("request_id") or data.get("message")
