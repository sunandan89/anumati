"""One-click field app setup for a pilot or a demo (Anumati Settings > Set up field app).

Creates, idempotently:
- Frappe Mobile Control's Mobile Configuration for Anumati Collect (if Mobile Control is installed);
- three fictional demo programmes (Village Health Camps = DEMO, After-school Learning Centres = EDU,
  Women's Self-Help Groups = SHG), each with four purposes, approved ROPA entries, a published notice and
  a reviewed Hindi translation, all through the stock Notice Publishing and ROPA Approval workflows;
- a test field worker user with the Anumati Field Worker and Mobile User roles.

Everything here is fictional sample data. Run it as Administrator (the workflows need the DPO role)."""

import secrets
import string

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow

PACKAGE = "org.anumati.collect"
MIN_VERSION = "1.0.0"
PROGRAMME = "DEMO"
FIELD_WORKER = "fieldworker.demo@example.com"

PURPOSES = (
	# code, title, description, essential, child_allowed
	("screen", "Health screening", "Blood pressure, sugar and anaemia checks, and a referral if needed.", 1, 1),
	("follow", "Follow-up calls", "A health worker calls to check on you after the camp.", 0, 1),
	("photos", "Photos and stories", "Photos of the camp for our reports, never with your name.", 0, 1),
	("research", "Anonymised research", "Test results without names, to plan health services in the district.", 0, 0),
)

# Rule 3 text shared by every demo notice (the organisation is fictional).
RULE3 = {
	"withdrawal_methods": "Reply STOP with your receipt code by SMS, give a missed call, or tell any worker.",
	"rights_text": "You can see, correct or delete your data, and name someone to act for you.",
	"board_complaint_route": "Data Protection Board of India",
	"dpo_contact": "Data Protection Officer, Demo Foundation (fictional)",
	"security_summary": "Encrypted on the phone and on the server; every consent is signed.",
}

HINDI = {
	"summary": "हम आपकी स्वास्थ्य जाँच करते हैं और ज़रूरत हो तो डॉक्टर के पास भेजते हैं।",
	"full_text": "नाम, उम्र, फ़ोन नंबर और जाँच के नतीजे। 24 महीने तक सुरक्षित रखे जाएँगे।",
	"label_yes_all": "सब के लिए हाँ",
	"label_no_all": "सब के लिए नहीं",
	"label_manage": "चुनें",
	"label_save": "आगे बढ़ें",
	"withdrawal_methods": "रसीद के कोड के साथ SMS में STOP भेजें, मिस्ड कॉल दें, या किसी भी कार्यकर्ता को बताएँ।",
	"rights_text": "आप अपना डेटा देख, सुधार या हटवा सकती हैं, और किसी को अपनी ओर से काम करने के लिए नामित कर सकती हैं।",
	"board_complaint_route": "भारत का डेटा संरक्षण बोर्ड",
	"dpo_contact": "डेटा संरक्षण अधिकारी, डेमो फ़ाउंडेशन (काल्पनिक)",
	"security_summary": "फ़ोन और सर्वर दोनों पर एन्क्रिप्टेड; हर सहमति पर डिजिटल हस्ताक्षर।",
}

# Three fictional programmes of the kind NGOs run. DEMO keeps its code (the field app and sample data
# use it); only its display name changed from the earlier "Demo Health Camp (fictional)".
PROGRAMMES = (
	{
		"code": PROGRAMME, "name": "Village Health Camps", "persona": "beneficiary",
		"category": "Health readings", "retention": "24 months", "purposes": PURPOSES,
		"summary": "We screen your health and refer you to a doctor if needed.",
		"full_text": "Name, age, phone number and test results. Kept safely for 24 months.",
		"hindi": {"summary": HINDI["summary"], "full_text": HINDI["full_text"]},
		"verification": ("device_sms_otp", "deferred", "evidence_only"),
	},
	{
		"code": "EDU", "name": "After-school Learning Centres", "persona": "student",
		"category": "Learning records", "retention": "36 months",
		"purposes": (
			("attend", "Attendance and learning records", "Who comes to the centre and how their reading and maths improve.", 1, 1),
			("parents", "SMS updates to parents", "A short SMS to a parent about attendance and progress.", 0, 1),
			("photos", "Photos for our reports", "Photos of centre activities, never with the child's name.", 0, 1),
			("study", "Anonymised learning study", "Scores without names, to improve our teaching.", 0, 0),
		),
		"summary": "We run free after-school classes and keep simple records of each child's learning.",
		"full_text": "Child's name, age, class, school, a parent's phone number and test scores. Kept for 36 months.",
		"hindi": {"summary": "हम स्कूल के बाद मुफ़्त कक्षाएँ चलाते हैं और हर बच्चे की पढ़ाई का रिकॉर्ड रखते हैं।",
		          "full_text": "बच्चे का नाम, उम्र, कक्षा, स्कूल, माता/पिता का फ़ोन नंबर और टेस्ट के अंक। 36 महीने तक रखे जाएँगे।"},
		"verification": ("device_sms_otp", "deferred"),
	},
	{
		"code": "SHG", "name": "Women's Self-Help Groups", "persona": "member",
		"category": "Savings and loan records", "retention": "60 months",
		"purposes": (
			("savings", "Group savings and loan records", "Your savings, loans and repayments in the group's books.", 1, 0),
			("bank", "Share with the partner bank", "Your name and savings record go to the bank for a group loan.", 0, 0),
			("training", "Training reminders by SMS", "An SMS before each training session.", 0, 0),
			("survey", "Anonymised impact survey", "Answers without names, to show what the groups achieve.", 0, 0),
		),
		"summary": "We support self-help groups with savings records, bank loans and training.",
		"full_text": "Name, phone number, group, savings and loan amounts. Kept for 60 months.",
		"hindi": {"summary": "हम स्वयं सहायता समूहों को बचत रिकॉर्ड, बैंक ऋण और प्रशिक्षण में मदद करते हैं।",
		          "full_text": "नाम, फ़ोन नंबर, समूह, बचत और ऋण की राशि। 60 महीने तक रखे जाएँगे।"},
		"verification": ("device_sms_otp", "deferred", "evidence_only"),
	},
)
OLD_NAMES = {"Demo Health Camp (fictional)"}


def configure_mobile_app() -> bool:
	"""Switch on Frappe Mobile Control for Anumati Collect. Returns False if it isn't installed."""
	if not frappe.db.exists("DocType", "Mobile Configuration"):
		return False
	config = frappe.get_single("Mobile Configuration")
	changed = False
	for field, value in (("enabled", 1), ("package_name", PACKAGE)):
		if not config.get(field):
			config.set(field, value)
			changed = True
	if not config.get("minimum_app_version"):
		config.minimum_app_version = MIN_VERSION
		changed = True
	if changed:
		config.save(ignore_permissions=True)
	return True


def _ensure_language(code, name):
	if not frappe.db.exists("Language", code):
		frappe.get_doc({"doctype": "Language", "language_code": code, "language_name": name}).insert()
	frappe.db.set_value("Language", code, "enabled", 1)


def create_demo_programme() -> str:
	"""The fictional demo programmes, each with approved records of processing, a published notice and a
	reviewed Hindi translation. Returns the DEMO programme's notice name."""
	_ensure_language("en", "English")
	_ensure_language("hi", "Hindi")
	notices = [_programme(spec) for spec in PROGRAMMES]
	return notices[0]


def _programme(spec) -> str:
	code = spec["code"]
	if not frappe.db.exists("Programme", code):
		frappe.get_doc({
			"doctype": "Programme", "code": code, "programme_name": spec["name"], "persona": spec["persona"],
			"status": "Live", "languages": [{"language": "en"}, {"language": "hi"}],
			"verification_methods": [{"verification_method": m} for m in spec["verification"]],
		}).insert()
	elif frappe.db.get_value("Programme", code, "programme_name") in OLD_NAMES:
		frappe.db.set_value("Programme", code, "programme_name", spec["name"])
		for name in frappe.get_all("Notice Template", {"programme": code}, pluck="name"):
			frappe.db.set_value("Notice Template", name, "programme_name", spec["name"], update_modified=False)
	if not frappe.db.exists("Data Category", spec["category"]):
		frappe.get_doc({"doctype": "Data Category", "category_name": spec["category"]}).insert()

	for pcode, title, description, essential, child_allowed in spec["purposes"]:
		name = f"{code}-{pcode}"
		if not frappe.db.exists("Purpose", name):
			frappe.get_doc({
				"doctype": "Purpose", "programme": code, "code": pcode, "purpose_title": title,
				"description": description, "essential": essential, "child_allowed": child_allowed,
			}).insert()
		if not frappe.db.exists("ROPA Entry", {"purpose": name, "status": "Approved"}):
			ropa = frappe.get_doc({
				"doctype": "ROPA Entry", "purpose": name, "retention": spec["retention"],
				"safeguards": "Encrypted at rest and in transit; access by role",
				"data_categories": [{"data_category": spec["category"]}],
			}).insert()
			apply_workflow(ropa, "Approve")

	notice = frappe.db.get_value("Notice Template", {"programme": code, "status": "Published"}, "name")
	if not notice:
		doc = frappe.get_doc({
			"doctype": "Notice Template", "programme": code, "version": "1.0.0",
			"summary": spec["summary"], "full_text": spec["full_text"],
			"purposes": [{"purpose": f"{code}-{p[0]}"} for p in spec["purposes"]],
			**RULE3,
		}).insert()
		notice = apply_workflow(doc, "Publish").name

	existing = frappe.db.get_value("Notice Translation", {"notice": notice, "language": "hi"})
	if not existing:
		frappe.get_doc({
			"doctype": "Notice Translation", "notice": notice, "language": "hi",
			**HINDI, **spec["hindi"], "machine_translated": 0, "reviewer": frappe.session.user,
		}).insert()
	elif not frappe.db.get_value("Notice Translation", existing, "rights_text"):
		# Earlier demo translations predate the translated Rule 3 fields; fill them in.
		frappe.db.set_value("Notice Translation", existing, {k: v for k, v in HINDI.items() if k not in ("summary", "full_text")})
	return notice


def _password() -> str:
	alphabet = string.ascii_letters + string.digits
	core = "".join(secrets.choice(alphabet) for _ in range(12))
	return f"{core[:4]}-{core[4:8]}-{core[8:]}!7a"


def create_field_worker(password: str | None = None) -> str:
	"""A test field worker. Returns its password: the one given, or a fresh random one (shown once to the
	admin, never logged)."""
	if frappe.db.exists("User", FIELD_WORKER):
		user = frappe.get_doc("User", FIELD_WORKER)
	else:
		user = frappe.get_doc({
			"doctype": "User", "email": FIELD_WORKER, "first_name": "Ravi", "last_name": "(demo)",
			"send_welcome_email": 0, "user_type": "System User",
		})
		user.flags.no_welcome_mail = True
		user.insert(ignore_permissions=True)
	roles = ["Anumati Field Worker"] + (["Mobile User"] if frappe.db.exists("Role", "Mobile User") else [])
	user.add_roles(*roles)
	password = password or _password()
	user.new_password = password
	user.enabled = 1
	user.save(ignore_permissions=True)
	return password


SAMPLE_PEOPLE = (
	# ref suffix, name, language, flags
	("0001", "Sunita Devi", "hi", {}),
	("0002", "Meena Kumari", "hi", {"needs_assistance": 1}),
	("0003", "Radha Sharma", "en", {}),
	("0004", "Kavita Yadav", "hi", {"shared_phone": 1}),
	("0005", "Asha Verma", "hi", {"needs_assistance": 1}),
	("0006", "Pooja Singh", "en", {}),
	("0007", "Lakshmi Bai", "hi", {"no_phone": 1}),
	("0008", "Geeta Patel", "hi", {}),
	("0009", "Rekha Rani", "hi", {"needs_assistance": 1}),
	("0010", "Anita Kumari", "en", {}),
	("0011", "Savitri Devi", "hi", {"no_phone": 1}),
	("0012", "Nirmala Joshi", "hi", {}),
	("0013", "Priya Das", "hi", {"is_minor": 1}),
	("0014", "Kiran Mishra", "hi", {}),
	("0015", "Usha Gupta", "en", {}),
	("0016", "Shanti Kumari", "hi", {"needs_assistance": 1}),
	("0017", "Babita Rawat", "hi", {}),
	("0018", "Sarita Nayak", "hi", {"shared_phone": 1}),
	("0019", "Jyoti Chauhan", "en", {}),
	("0020", "Mamta Thakur", "hi", {"is_minor": 1}),
)
CAPTURE = ("assisted_thumbprint", "assisted_verbal", "self_worker_device", "assisted_witnessed")
VERIFY = (("device_sms_otp", "confirmed"), ("deferred", "recorded"), ("evidence_only", "evidence_only"))


def create_sample_data() -> dict:
	"""Twenty fictional beneficiaries of the DEMO programme with consents captured by the test field worker:
	grants and refusals across capture and verification methods, two minors with guardians, a few
	withdrawals and rights requests. Names carry "(sample)"; phone numbers start with 555, which no Indian
	mobile number does, so nothing can ever reach a real person. Idempotent: people who already exist are skipped."""
	import uuid
	from datetime import timedelta

	from frappe.utils import now_datetime

	from anumati.api.v1 import consent, principal, rights

	create_demo_programme()
	if not frappe.db.exists("User", FIELD_WORKER):
		create_field_worker()
	optional = [p[0] for p in PURPOSES if not p[3]]
	made = {"people": 0, "consents": 0, "withdrawals": 0, "requests": 0}
	admin = frappe.session.user
	frappe.set_user(FIELD_WORKER)  # capture as the field worker, with a field worker's permissions
	try:
		for i, (suffix, name, lang, flags) in enumerate(SAMPLE_PEOPLE):
			ref = f"{PROGRAMME}-{suffix}"
			if frappe.db.exists("Data Principal", {"principal_ref": ref}):
				continue
			is_minor = flags.get("is_minor")
			phone = None if flags.get("no_phone") else ("5550000004" if flags.get("shared_phone") else f"55500{i:05d}")
			principal.upsert(ref, full_name=f"{name} (sample)", phone=phone, preferred_language=lang,
			                 persona="beneficiary", age_band="under_18" if is_minor else "18_plus", **flags)
			made["people"] += 1
			when = now_datetime() - timedelta(days=28 - i, hours=i % 7)
			granted = ["screen"] + [c for j, c in enumerate(optional) if (i + j) % 3 != 0]
			if is_minor:
				granted = [c for c in granted if c != "research"]
				guardian_ref = f"{ref}-G"
				principal.upsert(guardian_ref, full_name=f"Guardian of {name} (sample)", preferred_language=lang)
				link = frappe.get_doc({
					"doctype": "Guardian Link",
					"principal": frappe.db.get_value("Data Principal", {"principal_ref": ref}),
					"guardian": frappe.db.get_value("Data Principal", {"principal_ref": guardian_ref}),
					"guardian_type": "parent", "relation": "Mother", "verification_method": "document",
				}).insert()
			denied = [c for c in optional if c not in granted and not (is_minor and c == "research")]
			method, status = VERIFY[i % len(VERIFY)]
			refused_all = i in (6, 16)
			art = consent.record({
				"event_uuid": str(uuid.uuid4()), "principal_ref": ref, "programme": PROGRAMME,
				"action": "refuse" if refused_all else "grant",
				"purposes_granted": [] if refused_all else granted,
				"purposes_denied": optional if refused_all else denied,
				"language": lang, "channel": "app", "device_id": "DEMO-PHONE-01",
				"device_time": when.strftime("%Y-%m-%d %H:%M:%S"),
				"capture_mode": "guardian_minor" if is_minor else CAPTURE[i % len(CAPTURE)],
				"verification_method": "evidence_only" if not phone else method,
				"verification_status": "evidence_only" if not phone else status,
				"witness": "ASHA worker (sample)" if flags.get("needs_assistance") else None,
				"guardian_link": link.name if is_minor else None,
			})
			made["consents"] += 1
			if i in (3, 11, 18):
				consent.withdraw(ref, PROGRAMME, channel="field_worker", event_uuid=str(uuid.uuid4()),
				                 device_id="DEMO-PHONE-01",
				                 device_time=(when + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"))
				made["withdrawals"] += 1
			if i in (8, 14):
				rights.submit("access" if i == 8 else "correction", "field_worker", principal_ref=ref,
				              payload=f"Asked in person; consent {art['short_code']} (sample)")
				made["requests"] += 1
	finally:
		frappe.set_user(admin)
	return made


@frappe.whitelist(methods=["POST"])
def add_sample_data():
	"""Anumati Settings > Add sample data. System Managers only."""
	frappe.only_for("System Manager")
	return create_sample_data()


@frappe.whitelist(methods=["POST"])
def setup_field_app():
	"""Anumati Settings > Set up field app. System Managers only."""
	frappe.only_for("System Manager")
	mobile = configure_mobile_app()
	notice = create_demo_programme()
	password = create_field_worker()
	return {
		"mobile_control": mobile,
		"programme": PROGRAMME,
		"notice": notice,
		"user": FIELD_WORKER,
		"password": password,
		"site": frappe.local.site,
		"message": None if mobile else _("Frappe Mobile Control is not installed on this site yet. Install it, then run this again."),
	}


def set_demo_genders():
	"""The demo field worker (Ravi) is a man, so his phone plays the man's recording."""
	for gender in ("Male", "Female"):
		if not frappe.db.exists("Gender", gender):
			frappe.get_doc({"doctype": "Gender", "gender": gender}).insert(ignore_permissions=True)
	if frappe.db.exists("User", FIELD_WORKER) and not frappe.db.get_value("User", FIELD_WORKER, "gender"):
		frappe.db.set_value("User", FIELD_WORKER, "gender", "Male")


DEMO_NOTE = ("Demo audio approved automatically for this fictional demo programme. Listen to it in the "
             "Audio notice box; real programmes always need a person to approve their audio.")


def _demo_targets():
	for spec in PROGRAMMES:
		notice = frappe.db.get_value("Notice Template", {"programme": spec["code"], "status": "Published"}, "name")
		if notice:
			yield ("Notice Template", notice)
			for t in frappe.get_all("Notice Translation", {"notice": notice}, pluck="name"):
				yield ("Notice Translation", t)


def attach_bundled_audio() -> int:
	"""Demo sites only: attach the demo recordings shipped with the app (tools/gen_demo_audio.py), in the
	woman's and man's voice, and approve them. No Sarvam call. A clip is used only when this site's notice
	text is exactly the text it was recorded from, so an edited notice never gets the wrong audio."""
	import json
	import os

	from anumati import voice

	if not frappe.db.exists("Programme", PROGRAMME):
		return 0
	folder = frappe.get_app_path("anumati", "public", "demo_audio")
	manifest_path = os.path.join(folder, "manifest.json")
	if not os.path.exists(manifest_path):
		return 0
	with open(manifest_path) as fh:
		manifest = json.load(fh)
	attached = 0
	for doctype, name in _demo_targets():
		doc = frappe.get_doc(doctype, name)
		entry = manifest.get(voice.script_hash(voice.notice_script(doc)))
		if doc.audio_file or not entry:
			continue
		urls = {}
		for gender, field in (("female", "audio_file"), ("male", "audio_file_male")):
			with open(os.path.join(folder, entry[gender]), "rb") as fh:
				urls[field] = frappe.get_doc({
					"doctype": "File", "file_name": entry[gender], "content": fh.read(), "is_private": 1,
					"attached_to_doctype": doctype, "attached_to_name": name,
				}).insert(ignore_permissions=True).file_url
		voice._save(doc, **urls, audio_machine_made=1, audio_reviewed_by="Administrator")
		doc.add_comment("Comment", _(DEMO_NOTE))
		attached += 1
	return attached


@frappe.whitelist(methods=["POST"])
def record_demo_audio():
	"""Anumati Settings > Record demo audio (Sarvam). Starts recording in the background (about a minute
	per notice) and tells the person who pressed it when it is done."""
	frappe.only_for(["System Manager", "Anumati Admin"])
	if not frappe.db.exists("Programme", PROGRAMME):
		frappe.throw(_("There are no demo programmes on this site. Run Set up field app first."))
	from anumati import voice

	voice._key()  # a clear message now if the Sarvam key is missing
	frappe.enqueue("anumati.demo.prepare_demo_voice", queue="long", timeout=1800, notify=frappe.session.user,
	               job_id="anumati-demo-voice", deduplicate=True)
	return {"started": True}


def prepare_demo_voice(notify: str | None = None) -> dict:
	"""Demo sites only (the fictional DEMO programme exists): record every demo notice and its Hindi
	translation in the woman's and man's voice and approve them, so the demo works end to end. Real
	programmes are never touched: their audio is made and approved by a person in Desk. Skips anything
	that already has audio, so pressing the button again only fills gaps."""
	done = {"made": 0, "already": 0, "failed": 0}
	if not frappe.db.exists("Programme", PROGRAMME):
		return done
	set_demo_genders()
	from anumati import voice

	done["already"] += attach_bundled_audio()  # shipped recordings first: free and instant
	try:
		voice._key()
	except voice.VoiceError:
		return done  # no key yet
	for spec in PROGRAMMES:
		notice = frappe.db.get_value("Notice Template", {"programme": spec["code"], "status": "Published"}, "name")
		if not notice:
			continue
		targets = [("Notice Template", notice)] + [
			("Notice Translation", t) for t in frappe.get_all("Notice Translation", {"notice": notice}, pluck="name")]
		for doctype, name in targets:
			if frappe.db.get_value(doctype, name, "audio_file"):
				done["already"] += 1
				continue
			try:
				voice.generate_notice_audio(doctype, name)
				voice.approve_notice_audio(doctype, name)
				frappe.get_doc(doctype, name).add_comment("Comment", _(DEMO_NOTE))
				if not frappe.flags.in_test:
					frappe.db.commit()  # keep each paid recording even if a later one fails
				done["made"] += 1
			except Exception:
				if not frappe.flags.in_test:
					frappe.db.rollback()
				frappe.log_error(title="Anumati: demo notice audio could not be made")
				done["failed"] += 1
				break  # stop at the first failure; pressing the button again retries
		else:
			continue
		break
	if notify:
		ok = not done["failed"]
		frappe.publish_realtime("msgprint", {
			"title": _("Demo audio ready") if ok else _("Demo audio stopped"),
			"indicator": "green" if ok else "orange",
			"message": _("{0} notices recorded and approved, {1} already had audio.").format(done["made"], done["already"])
			+ ("" if ok else " " + _("Sarvam could not record one of them; see Error Log, then press the button again.")),
		}, user=notify)
	return done


def after_migrate():
	"""On every migrate (each Frappe Cloud deploy or "Migrate" action):
	- keep Mobile Configuration switched on for Anumati Collect once Mobile Control is installed;
	- if the site config has `anumati_demo_password` (set in the Frappe Cloud dashboard, never in the repo),
	  create the DEMO programme and the test field worker with that password. Remove the key to stop."""
	try:
		configure_mobile_app()
	except Exception:
		frappe.log_error(title="Anumati: could not configure Mobile Control")
	# Demo voice set-up calls Sarvam, so it runs from the hourly scheduler, never during a deploy.
	try:
		if frappe.db.exists("Programme", PROGRAMME):
			set_demo_genders()
			attach_bundled_audio()  # recordings shipped with the app; no Sarvam call during a deploy
	except Exception:
		frappe.log_error(title="Anumati: could not set up the demo field worker or demo audio")
	password = frappe.conf.get("anumati_demo_password")
	if not password:
		return
	try:
		create_demo_programme()
		create_field_worker(str(password))
	except Exception:
		frappe.log_error(title="Anumati: demo setup from site config failed")
