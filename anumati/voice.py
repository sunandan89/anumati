"""Natural voice with Sarvam AI (spec T13), an Indian speech provider.

1. Notice audio: a notice (or one of its translations) is read aloud by Sarvam's text-to-speech once, saved
   as an MP3 on the record, and marked machine-made. The field app plays it only after a reviewer
   approves it. Only the notice text is sent to Sarvam, never anyone's personal data.
2. Spoken yes/no helper: a worker's voice clip of someone saying "haan" is transcribed and read as yes,
   no or unclear, as a hint. Nothing is stored or logged, and it is off until the admin switches it on
   (which needs Sarvam listed as a Processor, since the person's voice is sent to them).

Plain HTTPS to api.sarvam.ai; the key comes from the site config (sarvam_api_key) or Anumati Settings."""

import base64
import re

import frappe
import requests
from frappe import _
from frappe.utils import cint, flt, strip_html

API = "https://api.sarvam.ai"
TTS_MODEL, STT_MODEL = "bulbul:v3", "saaras:v3"
CHUNK = 2000  # bulbul:v3 takes up to 2500 characters per request
LANGUAGES = {"hi": "hi-IN", "en": "en-IN", "mr": "mr-IN", "bn": "bn-IN", "gu": "gu-IN", "kn": "kn-IN",
             "ml": "ml-IN", "or": "od-IN", "pa": "pa-IN", "ta": "ta-IN", "te": "te-IN"}
RULE3 = ("withdrawal_methods", "rights_text", "board_complaint_route", "dpo_contact", "security_summary")
REVIEWERS = {"Anumati DPO", "Anumati Admin", "System Manager"}


class VoiceError(frappe.ValidationError):
	pass


def settings():
	return frappe.get_cached_doc("Anumati Settings")


def _key() -> str:
	key = frappe.conf.get("sarvam_api_key") or settings().get_password("sarvam_api_key", raise_exception=False)
	if not key:
		raise VoiceError(_("Sarvam is not set up. Add sarvam_api_key to the site config, or the key in Anumati Settings."))
	return key


def _post(path, **kwargs):
	try:
		r = requests.post(f"{API}/{path}", headers={"api-subscription-key": _key()}, timeout=90, **kwargs)
	except requests.RequestException:
		raise VoiceError(_("Could not reach Sarvam. Try again in a minute."))
	if r.status_code == 403 or r.status_code == 401:
		raise VoiceError(_("Sarvam refused the API key. Check it in the site config."))
	if not r.ok:
		# Sarvam's error text never contains our data back, but keep it out of logs anyway.
		frappe.log_error(title=f"Anumati: Sarvam {path} failed ({r.status_code})")
		raise VoiceError(_("Sarvam could not do this ({0}).").format(r.status_code))
	return r.json()


# ---------------------------------------------------------------- 1. notice audio
def chunks(text: str, size: int = CHUNK) -> list[str]:
	"""Split at sentence ends (., ।, ?, !) so no request is longer than the model allows."""
	parts, current = [], ""
	for sentence in re.split(r"(?<=[.।?!])\s+", text.strip()):
		while len(sentence) > size:
			parts.append(sentence[:size])
			sentence = sentence[size:]
		if len(current) + len(sentence) + 1 > size and current:
			parts.append(current)
			current = ""
		current = f"{current} {sentence}".strip()
	if current:
		parts.append(current)
	return parts


def speak(text: str, language: str, speaker: str | None = None, pace: float | None = None) -> bytes:
	"""MP3 of the text, in one piece (MP3 frames can simply be joined)."""
	code = LANGUAGES.get((language or "en").split("-")[0])
	if not code:
		raise VoiceError(_("Sarvam has no voice for language {0}.").format(language))
	s = settings()
	audio = b""
	for part in chunks(text):
		out = _post("text-to-speech", json={
			"text": part, "language_code": code, "model": TTS_MODEL, "output_audio_codec": "mp3",
			"speaker": speaker or s.voice_speaker or "priya", "pace": flt(pace or s.voice_pace or 1.0),
		})
		audio += base64.b64decode(out["audios"][0])
	return audio


def notice_script(doc) -> str:
	"""What the recording says: the summary, what is collected, each purpose (base notice only; a
	translation's own text covers them), and the Rule 3 contents."""
	notice = frappe.get_doc("Notice Template", doc.notice) if doc.doctype == "Notice Translation" else doc
	lines = [doc.summary, strip_html(doc.full_text or "")]
	if doc.doctype == "Notice Template":
		for row in doc.purposes:
			title, description, essential = frappe.db.get_value(
				"Purpose", row.purpose, ["purpose_title", "description", "essential"])
			lines.append(f"{title}{' (always needed)' if essential else ''}: {description or ''}")
	lines += [doc.get(k) or notice.get(k) for k in RULE3]
	return "\n".join(line.strip() for line in lines if line and line.strip())


def _language(doc) -> str:
	return doc.language if doc.doctype == "Notice Translation" else "en"


def _check(doctype, name, for_review=False):
	if doctype not in ("Notice Template", "Notice Translation"):
		frappe.throw(_("Audio can only be made for a notice or a notice translation."))
	doc = frappe.get_doc(doctype, name)
	if doctype == "Notice Template" or for_review:
		# The base notice is the DPO's; approving any audio is a reviewer's decision.
		if not REVIEWERS & set(frappe.get_roles()):
			raise frappe.PermissionError
	else:
		doc.check_permission("write")
	return doc


@frappe.whitelist(methods=["POST"])
def generate_notice_audio(doctype, name):
	"""Desk button: read the notice aloud with Sarvam, attach the MP3, mark it machine-made (not yet
	approved). Returns the file URL."""
	flag = settings().get("voice_notice_audio")
	if flag is not None and not cint(flag):  # on by default, including sites set up before the setting
		frappe.throw(_("Natural notice audio is switched off in Anumati Settings."))
	doc = _check(doctype, name)
	audio = speak(notice_script(doc), _language(doc))
	f = frappe.get_doc({
		"doctype": "File", "file_name": f"{frappe.scrub(name)}-{_language(doc)}-voice.mp3", "content": audio,
		"is_private": 1, "attached_to_doctype": doctype, "attached_to_name": name,
	}).insert(ignore_permissions=True)
	_save(doc, audio_file=f.file_url, audio_machine_made=1, audio_reviewed_by=None)
	return {"audio_file": f.file_url}


def _save(doc, **values):
	"""Audio fields may change on a published notice (allow on submit). A normal save keeps the change in
	the document history, which the audit chain seals; permissions were checked in _check."""
	doc.update(values)
	doc.flags.ignore_permissions = True
	doc.save()


@frappe.whitelist(methods=["POST"])
def approve_notice_audio(doctype, name):
	"""A reviewer has listened to the whole recording and it matches the text."""
	doc = _check(doctype, name, for_review=True)
	if not doc.audio_file:
		frappe.throw(_("There is no audio to approve."))
	_save(doc, audio_reviewed_by=frappe.session.user)
	return {"audio_reviewed_by": frappe.session.user}


# ---------------------------------------------------------------- 2. spoken yes / no
YES = {"haan", "haa", "han", "ha", "haanji", "hanji", "ji", "jee", "theek", "thik", "sahi", "manzoor",
       "manjoor", "bilkul", "zaroor", "jarur", "yes", "ok", "okay", "agree",
       "हाँ", "हां", "हा", "जी", "ठीक", "सही", "मंजूर", "मंज़ूर", "बिल्कुल", "बिलकुल", "ज़रूर", "जरूर",
       "ओके", "यस", "हाँजी", "हांजी"}
NO = {"nahi", "nahin", "nai", "na", "naa", "mat", "no", "nope", "disagree",
      "नहीं", "नही", "ना", "मत", "नो", "नहि"}


def meaning(transcript: str) -> str:
	"""'yes', 'no' or 'unclear'. Both kinds of word (e.g. "haan, koi dikkat nahi") is unclear: the worker
	decides."""
	words = set(re.findall(r"[\wऀ-ॿ]+", (transcript or "").casefold()))
	yes, no = bool(words & YES), bool(words & NO)
	return "yes" if yes and not no else "no" if no and not yes else "unclear"


def hear(audio: bytes, filename: str = "clip.m4a", language: str | None = None) -> dict:
	out = _post("speech-to-text", data={
		"model": STT_MODEL, "mode": "codemix",
		"language_code": LANGUAGES.get((language or "").split("-")[0], "unknown"),
	}, files={"file": (filename, audio)})
	transcript = out.get("transcript") or ""
	return {"transcript": transcript, "meaning": meaning(transcript)}
