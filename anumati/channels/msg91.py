"""MSG91 adapter (Flow API). The Message Template's "DLT template ID" field holds the MSG91 flow/template
id registered against the DLT template; template variables are passed as var1..varN in the order the
context lists them, plus named keys for flows that use names."""

import requests

API = "https://control.msg91.com/api/v5/flow"
VARS = ("code", "programme", "purposes", "date", "otp", "status", "board_route")  # append only: DLT flows are numbered


def send(provider, phone_digits: str, template, context: dict) -> str | None:
	recipient = {"mobiles": "91" + phone_digits if len(phone_digits) == 10 else phone_digits}
	for i, key in enumerate(VARS, start=1):
		if context.get(key) is not None:
			recipient[f"var{i}"] = str(context[key])
			recipient[key] = str(context[key])
	response = requests.post(
		API,
		headers={"authkey": provider.get_password("api_key"), "accept": "application/json",
		         "content-type": "application/json"},
		json={"template_id": template.dlt_template_id, "short_url": "0", "recipients": [recipient]},
		timeout=10,
	)
	response.raise_for_status()
	data = response.json() if response.content else {}
	if data.get("type") == "error":
		raise RuntimeError("MSG91 rejected the message")
	return data.get("request_id") or data.get("message")
