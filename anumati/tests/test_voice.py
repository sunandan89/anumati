"""Sarvam voice (spec T13): natural notice audio that plays only after approval, and the spoken yes/no
hint that is off by default, needs Sarvam as a Processor, and stores nothing. Sarvam is mocked; no
network in CI. All sample data is fictional."""

import base64
import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from anumati import demo, voice
from anumati.api.v1 import device, notice
from anumati.api.v1 import voice as voice_api
from anumati.tests.test_console import user_with_role

MP3 = b"\xff\xf3\xc0fake-mp3-frame"


class FakeResponse:
	def __init__(self, payload, status=200):
		self.payload, self.status_code, self.ok = payload, status, 200 <= status < 300

	def json(self):
		return self.payload


SPEAKERS = []


def fake_sarvam(url, **kwargs):
	if url.endswith("text-to-speech"):
		assert "Kavita" not in json.dumps(kwargs.get("json"))  # notice text only
		SPEAKERS.append(kwargs["json"]["speaker"])
		return FakeResponse({"audios": [base64.b64encode(MP3).decode()]})
	return FakeResponse({"transcript": "हाँ जी, ठीक है", "language_code": "hi-IN"})


class TestVoice(FrappeTestCase):
	def setUp(self):
		frappe.conf.sarvam_api_key = "test-key-not-real"
		self.notice = demo.create_demo_programme()
		self.translation = frappe.db.get_value("Notice Translation", {"notice": self.notice, "language": "hi"})

	def tearDown(self):
		frappe.conf.pop("sarvam_api_key", None)
		frappe.db.set_single_value("Anumati Settings", "voice_listen_helper", 0)
		frappe.clear_document_cache("Anumati Settings", "Anumati Settings")

	def test_long_text_is_split_at_sentences_under_the_limit(self):
		text = "एक वाक्य। " * 400
		parts = voice.chunks(text)
		self.assertGreater(len(parts), 1)
		self.assertTrue(all(len(p) <= voice.CHUNK for p in parts))
		self.assertEqual(" ".join(parts).split(), text.split())

	def test_spoken_yes_no_or_unclear(self):
		for heard, want in (("haan ji", "yes"), ("हाँ जी, ठीक है", "yes"), ("nahi chahiye", "no"), ("नहीं", "no"),
		                    ("I don't agree", "unclear"), ("not okay", "unclear"), ("never", "no"),
		                    ("haan, koi dikkat nahi", "unclear"), ("", "unclear"), ("kya?", "unclear")):
			self.assertEqual(voice.meaning(heard), want, heard)

	def test_translation_audio_plays_only_after_approval(self):
		with patch("anumati.voice.requests.post", side_effect=fake_sarvam):
			out = voice.generate_notice_audio("Notice Translation", self.translation)
		doc = frappe.get_doc("Notice Translation", self.translation)
		self.assertEqual(doc.audio_file, out["audio_file"])
		self.assertEqual(doc.audio_file_male, out["audio_file_male"])
		self.assertIn("kavya", SPEAKERS)
		self.assertIn("rahul", SPEAKERS)
		self.assertTrue(doc.audio_machine_made)
		self.assertFalse(doc.audio_reviewed_by)
		programme = frappe.db.get_value("Notice Template", self.notice, "programme")
		self.assertIsNone(notice.get_active(programme, language="hi")["translation"]["audio_file"])
		self.assertIsNone(notice.get_active(programme, language="hi")["translation"]["audio_file_male"])
		voice.approve_notice_audio("Notice Translation", self.translation)
		served = notice.get_active(programme, language="hi")["translation"]
		self.assertEqual((served["audio_file"], served["audio_file_male"]), (out["audio_file"], out["audio_file_male"]))
		self.assertEqual(served["audio_machine_made"], 1, "the phone credits the machine voice")
		# Making it again needs a fresh approval.
		with patch("anumati.voice.requests.post", side_effect=fake_sarvam):
			voice.generate_notice_audio("Notice Translation", self.translation)
		self.assertIsNone(notice.get_active(programme, language="hi")["translation"]["audio_file"])

	def test_published_notice_gets_base_audio_after_approval(self):
		with patch("anumati.voice.requests.post", side_effect=fake_sarvam):
			voice.generate_notice_audio("Notice Template", self.notice)
		programme = frappe.db.get_value("Notice Template", self.notice, "programme")
		self.assertIsNone(notice.get_active(programme)["audio_file"])
		voice.approve_notice_audio("Notice Template", self.notice)
		self.assertTrue(notice.get_active(programme)["audio_file"])
		self.assertEqual(frappe.db.get_value("Notice Template", self.notice, "docstatus"), 1)

	def test_field_workers_cannot_make_or_approve_base_audio(self):
		frappe.set_user(user_with_role("Anumati Field Worker"))
		try:
			self.assertRaises(frappe.PermissionError, voice.approve_notice_audio, "Notice Template", self.notice)
			self.assertRaises(frappe.PermissionError, voice.generate_notice_audio, "Notice Template", self.notice)
		finally:
			frappe.set_user("Administrator")

	def test_spoken_helper_is_off_by_default_and_needs_sarvam_as_a_processor(self):
		clip = base64.b64encode(b"fake-m4a").decode()
		self.assertEqual(voice_api.hear(clip), {"enabled": False})
		self.assertFalse(device.register("VOICE-TEST-1")["voice_helper"])
		settings = frappe.get_single("Anumati Settings")
		settings.voice_listen_helper = 1
		self.assertRaises(frappe.ValidationError, settings.save)
		if not frappe.db.exists("Processor", "Sarvam AI"):
			frappe.get_doc({"doctype": "Processor", "processor_name": "Sarvam AI", "country": "India"}).insert()
		settings = frappe.get_single("Anumati Settings")  # fresh copy after the refused save
		settings.voice_listen_helper = 1
		settings.save()
		self.assertTrue(device.register("VOICE-TEST-1")["voice_helper"])
		files, errors = frappe.db.count("File"), frappe.db.count("Error Log")
		with patch("anumati.voice.requests.post", side_effect=fake_sarvam):
			out = voice_api.hear(clip, language="hi")
		self.assertEqual(out["meaning"], "yes")
		self.assertEqual((frappe.db.count("File"), frappe.db.count("Error Log")), (files, errors), "nothing is stored")

	def test_hear_rejects_oversized_or_garbled_clips(self):
		frappe.db.set_single_value("Anumati Settings", "voice_listen_helper", 1)
		frappe.clear_document_cache("Anumati Settings", "Anumati Settings")
		self.assertRaises(frappe.ValidationError, voice_api.hear, "not base64!!")
		big = base64.b64encode(b"x" * (voice_api.MAX_BYTES + 1)).decode()
		self.assertRaises(frappe.ValidationError, voice_api.hear, big)

	def test_missing_key_explains_what_to_do(self):
		frappe.conf.pop("sarvam_api_key", None)
		self.assertRaises(voice.VoiceError, voice.speak, "नमस्ते", "hi")

	def test_phone_is_told_which_voice_to_play(self):
		female = user_with_role("Anumati Field Worker")
		male = "voice.male.worker@example.com"
		if not frappe.db.exists("Gender", "Male"):  # created by the setup wizard on real sites
			frappe.get_doc({"doctype": "Gender", "gender": "Male"}).insert()
		if not frappe.db.exists("User", male):
			frappe.get_doc({"doctype": "User", "email": male, "first_name": "Ravi", "gender": "Male",
			                "send_welcome_email": 0, "roles": [{"role": "Anumati Field Worker"}]}).insert()
		for user, want in ((female, "female"), (male, "male")):
			frappe.set_user(user)
			try:
				self.assertEqual(device.register(f"VOICE-{want}")["voice"], want)
			finally:
				frappe.set_user("Administrator")

	def test_demo_site_gets_recorded_approved_notices_and_a_male_demo_worker(self):
		demo.create_field_worker()
		frappe.db.set_value("User", demo.FIELD_WORKER, "gender", None)
		for doctype in ("Notice Template", "Notice Translation"):  # start from no audio, whatever ran before
			for name in frappe.get_all(doctype, pluck="name"):
				frappe.db.set_value(doctype, name, {"audio_file": None, "audio_file_male": None, "audio_reviewed_by": None})
		SPEAKERS.clear()
		with patch("anumati.voice.requests.post", side_effect=fake_sarvam):
			done = demo.prepare_demo_voice()
		self.assertEqual(done["failed"], 0)
		self.assertGreaterEqual(done["made"] + done["already"], 6)  # 3 programmes x (notice + Hindi)
		self.assertEqual(frappe.db.get_value("User", demo.FIELD_WORKER, "gender"), "Male")
		for spec in demo.PROGRAMMES:
			out = notice.get_active(spec["code"], language="hi")
			self.assertTrue(out["audio_file"] and out["audio_file_male"], spec["code"])
			self.assertTrue(out["translation"]["audio_file_male"], spec["code"])
		made = len(SPEAKERS)
		with patch("anumati.voice.requests.post", side_effect=fake_sarvam):
			demo.prepare_demo_voice()
		self.assertEqual(len(SPEAKERS), made, "nothing is recorded twice")

	def test_demo_voice_does_nothing_without_a_key(self):
		frappe.conf.pop("sarvam_api_key", None)
		with patch("anumati.voice.requests.post", side_effect=AssertionError("must not call Sarvam")):
			demo.prepare_demo_voice()
		self.assertRaises(voice.VoiceError, demo.record_demo_audio)  # the button explains what is missing

	def test_nothing_records_on_its_own(self):
		# Sarvam is paid per use: recording happens only when someone presses a button.
		self.assertNotIn("prepare_demo_voice", json.dumps(frappe.get_hooks("scheduler_events") or {}))

	def test_a_very_long_sentence_keeps_its_place(self):
		text = "Short summary. " + "x" * 4500 + " End."
		parts = voice.chunks(text)
		self.assertEqual(parts[0], "Short summary.")
		self.assertTrue(all(len(p) <= voice.CHUNK for p in parts))
		self.assertEqual("".join(parts).replace(" ", ""), text.replace(" ", ""))

	def test_hand_attached_recording_is_a_person_recording_and_drops_the_old_approval(self):
		with patch("anumati.voice.requests.post", side_effect=fake_sarvam):
			voice.generate_notice_audio("Notice Translation", self.translation)
		voice.approve_notice_audio("Notice Translation", self.translation)
		doc = frappe.get_doc("Notice Translation", self.translation)
		doc.audio_file = "/private/files/recorded-by-our-team.mp3"
		doc.save()
		self.assertFalse(doc.audio_machine_made)
		self.assertFalse(doc.audio_reviewed_by)
		self.assertFalse(doc.audio_file_male)
		programme = frappe.db.get_value("Notice Template", self.notice, "programme")
		self.assertEqual(notice.get_active(programme, language="hi")["translation"]["audio_machine_made"], 0)

	def test_bundled_demo_audio_matches_the_notice_text_and_needs_no_sarvam(self):
		for doctype in ("Notice Template", "Notice Translation"):
			for name in frappe.get_all(doctype, pluck="name"):
				frappe.db.set_value(doctype, name, {"audio_file": None, "audio_file_male": None, "audio_reviewed_by": None})
		with patch("anumati.voice.requests.post", side_effect=AssertionError("must not call Sarvam")):
			attached = demo.attach_bundled_audio()
		self.assertEqual(attached, 6, "every demo notice and its Hindi translation has a shipped recording")
		for spec in demo.PROGRAMMES:
			out = notice.get_active(spec["code"], language="hi")
			self.assertTrue(out["audio_file"] and out["audio_file_male"], spec["code"])
			self.assertTrue(out["translation"]["audio_file"] and out["translation"]["audio_file_male"], spec["code"])
		# A notice whose text was edited never gets a shipped recording of the old text.
		frappe.db.set_value("Notice Translation", self.translation, {"audio_file": None, "summary": "बदला हुआ सार"})
		self.assertEqual(demo.attach_bundled_audio(), 0)
