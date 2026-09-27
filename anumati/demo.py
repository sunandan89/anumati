"""One-click field app setup for a pilot or a demo (Anumati Settings > Set up field app).

Creates, idempotently:
- Frappe Mobile Control's Mobile Configuration for Anumati Collect (if Mobile Control is installed);
- a fictional demo programme (DEMO) with four purposes, approved ROPA entries, a published notice and a
  reviewed Hindi translation, all through the stock Notice Publishing and ROPA Approval workflows;
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

HINDI = {
	"summary": "हम आपकी स्वास्थ्य जाँच करते हैं और ज़रूरत हो तो डॉक्टर के पास भेजते हैं।",
	"full_text": "नाम, उम्र, फ़ोन नंबर और जाँच के नतीजे। 24 महीने तक सुरक्षित रखे जाएँगे।",
	"label_yes_all": "सब के लिए हाँ",
	"label_no_all": "सब के लिए नहीं",
	"label_manage": "चुनें",
	"label_save": "आगे बढ़ें",
}


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
	"""The fictional DEMO programme with a published notice. Returns the notice name."""
	_ensure_language("en", "English")
	_ensure_language("hi", "Hindi")
	if not frappe.db.exists("Programme", PROGRAMME):
		frappe.get_doc({
			"doctype": "Programme", "code": PROGRAMME, "programme_name": "Demo Health Camp (fictional)",
			"status": "Live", "languages": [{"language": "en"}, {"language": "hi"}],
			"verification_methods": [{"verification_method": m} for m in ("device_sms_otp", "deferred", "evidence_only")],
		}).insert()
	if not frappe.db.exists("Data Category", "Health readings"):
		frappe.get_doc({"doctype": "Data Category", "category_name": "Health readings"}).insert()

	for code, title, description, essential, child_allowed in PURPOSES:
		name = f"{PROGRAMME}-{code}"
		if not frappe.db.exists("Purpose", name):
			frappe.get_doc({
				"doctype": "Purpose", "programme": PROGRAMME, "code": code, "purpose_title": title,
				"description": description, "essential": essential, "child_allowed": child_allowed,
			}).insert()
		if not frappe.db.exists("ROPA Entry", {"purpose": name, "status": "Approved"}):
			ropa = frappe.get_doc({
				"doctype": "ROPA Entry", "purpose": name, "retention": "24 months",
				"safeguards": "Encrypted at rest and in transit; access by role",
				"data_categories": [{"data_category": "Health readings"}],
			}).insert()
			apply_workflow(ropa, "Approve")

	notice = frappe.db.get_value("Notice Template", {"programme": PROGRAMME, "status": "Published"}, "name")
	if not notice:
		doc = frappe.get_doc({
			"doctype": "Notice Template", "programme": PROGRAMME, "version": "1.0.0",
			"summary": "We screen your health and refer you to a doctor if needed.",
			"full_text": "Name, age, phone number and test results. Kept safely for 24 months.",
			"purposes": [{"purpose": f"{PROGRAMME}-{p[0]}"} for p in PURPOSES],
			"withdrawal_methods": "Reply STOP with your receipt code by SMS, give a missed call, or tell any worker.",
			"rights_text": "You can see, correct or delete your data, and name someone to act for you.",
			"board_complaint_route": "Data Protection Board of India",
			"dpo_contact": "Data Protection Officer, Demo Foundation (fictional)",
			"security_summary": "Encrypted on the phone and on the server; every consent is signed.",
		}).insert()
		notice = apply_workflow(doc, "Publish").name

	if not frappe.db.exists("Notice Translation", {"notice": notice, "language": "hi"}):
		frappe.get_doc({
			"doctype": "Notice Translation", "notice": notice, "language": "hi", **HINDI,
			"machine_translated": 0, "reviewer": frappe.session.user,
		}).insert()
	return notice


def _password() -> str:
	alphabet = string.ascii_letters + string.digits
	core = "".join(secrets.choice(alphabet) for _ in range(12))
	return f"{core[:4]}-{core[4:8]}-{core[8:]}!7a"


def create_field_worker() -> str:
	"""A test field worker. Returns a fresh password (shown once to the admin, never logged)."""
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
	password = _password()
	user.new_password = password
	user.enabled = 1
	user.save(ignore_permissions=True)
	return password


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


def after_migrate():
	"""Keep Mobile Configuration switched on for Anumati Collect once Mobile Control is installed."""
	try:
		configure_mobile_app()
	except Exception:
		frappe.log_error(title="Anumati: could not configure Mobile Control")
