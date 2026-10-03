"""Extra questions about the person (profile questions).

A library of common questions is installed on every migrate. Each programme switches on the ones it
needs (Programme > Extra questions); none are asked by default. A question can be switched on only once
the programme's published notice mentions it, so people are always told what is collected. Answers are
kept on the Data Principal and reported as totals only."""

import re

import frappe
from frappe import _

YES_NO = ("Yes", "No")

# code, question, answer type, choices, sensitive, notice term, Hindi question, Hindi choices
LIBRARY = (
	("age", "Age in years", "number", (), 0, "age", "उम्र (साल में)", ()),
	("gender", "Gender", "choice", ("Female", "Male", "Other", "Prefer not to say"), 0, "gender",
	 "लिंग", ("महिला", "पुरुष", "अन्य", "नहीं बताना चाहते")),
	("occupation", "Occupation", "choice",
	 ("Farming or farm labour", "Daily wage work", "Homemaker", "Self-employed", "Salaried job", "Student", "Not working", "Other"),
	 0, "occupation", "काम / पेशा",
	 ("खेती या खेत मज़दूरी", "दिहाड़ी मज़दूरी", "गृहिणी / घर का काम", "अपना काम", "नौकरी", "पढ़ाई", "कोई काम नहीं", "अन्य")),
	("education", "Education", "choice",
	 ("Never went to school", "Primary (1-5)", "Middle (6-8)", "Secondary (9-10)", "Higher secondary (11-12)", "Graduate or above"),
	 0, "education", "पढ़ाई",
	 ("कभी स्कूल नहीं गए", "प्राथमिक (1-5)", "माध्यमिक (6-8)", "हाई स्कूल (9-10)", "इंटर (11-12)", "स्नातक या उससे ऊपर")),
	("marital_status", "Marital status", "choice", ("Married", "Unmarried", "Widowed", "Separated", "Prefer not to say"),
	 0, "marital status", "वैवाहिक स्थिति", ("विवाहित", "अविवाहित", "विधवा / विधुर", "अलग रहते हैं", "नहीं बताना चाहते")),
	("household_size", "People in the household", "number", (), 0, "household", "घर में कितने लोग", ()),
	("children_under_5", "Children under 5 at home", "number", (), 0, "children", "घर में 5 साल से छोटे बच्चे", ()),
	("ration_card", "Ration card type", "choice", ("Antyodaya (AAY)", "Priority household (PHH/BPL)", "APL", "None"),
	 0, "ration card", "राशन कार्ड", ("अंत्योदय (AAY)", "प्राथमिकता परिवार (PHH/BPL)", "APL", "कोई नहीं")),
	("income_band", "Monthly household income", "choice",
	 ("Under ₹5,000", "₹5,000-10,000", "₹10,000-20,000", "Over ₹20,000", "Prefer not to say"),
	 0, "income", "घर की महीने की आमदनी", ("₹5,000 से कम", "₹5,000-10,000", "₹10,000-20,000", "₹20,000 से ज़्यादा", "नहीं बताना चाहते")),
	("land", "Land owned", "choice", ("None", "Under 1 acre", "1-5 acres", "Over 5 acres"), 0, "land",
	 "अपनी ज़मीन", ("नहीं", "1 एकड़ से कम", "1-5 एकड़", "5 एकड़ से ज़्यादा")),
	("house_type", "Type of house", "choice", ("Kachcha", "Semi-pucca", "Pucca"), 0, "house",
	 "घर कैसा है", ("कच्चा", "आधा पक्का", "पक्का")),
	("drinking_water", "Main drinking water source", "choice", ("Tap at home", "Hand pump", "Well", "Public tap", "Other"),
	 0, "drinking water", "पीने का पानी कहाँ से", ("घर में नल", "हैंडपंप", "कुआँ", "सार्वजनिक नल", "अन्य")),
	("toilet", "Toilet at home", "choice", YES_NO, 0, "toilet", "घर में शौचालय", ("हाँ", "नहीं")),
	("phone_type", "Kind of mobile phone", "choice", ("Smartphone", "Keypad phone", "No phone"), 0, "mobile phone",
	 "कैसा मोबाइल फ़ोन", ("स्मार्टफ़ोन", "बटन वाला फ़ोन", "फ़ोन नहीं")),
	("bank_account", "Has a bank account", "choice", YES_NO, 0, "bank account", "बैंक खाता है", ("हाँ", "नहीं")),
	("shg_member", "Member of a self-help group", "choice", YES_NO, 0, "self-help group", "स्वयं सहायता समूह की सदस्य", ("हाँ", "नहीं")),
	("pregnant", "Currently pregnant", "choice", ("Yes", "No", "Prefer not to say"), 1, "pregnancy",
	 "अभी गर्भवती हैं", ("हाँ", "नहीं", "नहीं बताना चाहते")),
	("disability", "Has a disability", "choice", ("No", "Seeing", "Hearing", "Movement", "Learning or intellectual", "Other", "Prefer not to say"),
	 1, "disability", "कोई विकलांगता", ("नहीं", "देखने में", "सुनने में", "चलने-फिरने में", "सीखने / समझने में", "अन्य", "नहीं बताना चाहते")),
	("social_category", "Social category", "choice", ("SC", "ST", "OBC", "General", "Prefer not to say"), 1, "social category",
	 "सामाजिक वर्ग", ("अनुसूचित जाति", "अनुसूचित जनजाति", "अन्य पिछड़ा वर्ग", "सामान्य", "नहीं बताना चाहते")),
	("religion", "Religion", "choice", ("Hindu", "Muslim", "Christian", "Sikh", "Buddhist", "Jain", "Other", "Prefer not to say"),
	 1, "religion", "धर्म", ("हिंदू", "मुस्लिम", "ईसाई", "सिख", "बौद्ध", "जैन", "अन्य", "नहीं बताना चाहते")),
)


def ensure_library():
	"""Install the standard questions. Ones already there, and custom questions, are left alone."""
	with_hindi = frappe.db.exists("Language", "hi")
	for code, question, kind, options, sensitive, term, hi_q, hi_opts in LIBRARY:
		if frappe.db.exists("Profile Question", code):
			continue
		doc = frappe.get_doc({
			"doctype": "Profile Question", "code": code, "question": question, "answer_type": kind,
			"options": "\n".join(options), "is_sensitive": sensitive, "notice_term": term, "is_standard": 1,
			"labels": [{"language": "hi", "question": hi_q, "options": "\n".join(hi_opts)}] if with_hindi else [],
		})
		doc.flags.ignore_permissions = True
		doc.insert()


def published_notice(programme: str):
	return frappe.db.get_value(
		"Notice Template", {"programme": programme, "docstatus": 1, "status": "Published"}, order_by="creation desc"
	)


def notice_text(notice: str) -> str:
	"""Everything the base notice says, lower-cased, without HTML: what a question's term is checked against."""
	doc = frappe.get_doc("Notice Template", notice)
	parts = [doc.summary or "", doc.full_text or ""]
	for row in doc.purposes:
		p = frappe.db.get_value("Purpose", row.purpose, ["purpose_title", "description"], as_dict=True) or {}
		parts += [p.get("purpose_title") or "", p.get("description") or ""]
	return re.sub(r"<[^>]+>", " ", " ".join(parts)).lower()


def mentions(text: str, term: str) -> bool:
	"""Whole words only, so "age" is not found in "village" or "message"."""
	term = (term or "").strip().lower()
	return bool(term) and re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text) is not None


def validate_programme(doc):
	"""Programme.validate: each switched-on question must be mentioned in the published notice."""
	rows = doc.get("profile_questions") or []
	if not rows:
		return
	seen = set()
	for row in rows:
		if row.question in seen:
			frappe.throw(_("{0} is listed twice").format(row.question))
		seen.add(row.question)
	notice = published_notice(doc.name) if not doc.is_new() else None
	if not notice:
		frappe.throw(_("Publish a notice for this programme before asking extra questions: people must be told what is collected."))
	text = notice_text(notice)
	missing = []
	for row in rows:
		term, label = frappe.db.get_value("Profile Question", row.question, ["notice_term", "question"])
		if not mentions(text, term):
			missing.append(f"{label} (“{term}”)")
	if missing:
		frappe.throw(_("Add these to the notice first, then publish it again: {0}").format(", ".join(missing)),
		             title=_("Not in the notice"))
	sensitive = [r.question for r in rows if frappe.db.get_value("Profile Question", r.question, "is_sensitive")]
	if sensitive:
		frappe.msgprint(_("Sensitive questions switched on: {0}. Ask them only if the work truly needs them; reports show totals only.")
		                .format(", ".join(sensitive)), indicator="orange", alert=True)


def for_notice(programme: str, notice: str, language: str | None = None) -> list[dict]:
	"""The questions a programme asks, for the phone, in the notice's language where a translation exists.
	A question the live notice no longer mentions is left out."""
	rows = frappe.get_all("Programme Profile Question", {"parent": programme, "parenttype": "Programme"},
	                      ["question", "required"], order_by="idx asc")
	if not rows:
		return []
	text = notice_text(notice)
	out = []
	for r in rows:
		q = frappe.get_doc("Profile Question", r.question)
		if not mentions(text, q.notice_term):
			continue
		options = [o.strip() for o in (q.options or "").split("\n") if o.strip()]
		label = next((row for row in q.labels if language and row.language == language), None)
		shown = [o.strip() for o in (label.options or "").split("\n") if o.strip()] if label else []
		out.append({
			"code": q.code, "question": label.question if label else q.question, "answer_type": q.answer_type,
			# Stored answers are always the English choice, so totals add up across languages.
			"options": [{"value": v, "label": shown[i] if i < len(shown) else v} for i, v in enumerate(options)],
			"required": 1 if r.required else 0, "sensitive": 1 if q.is_sensitive else 0,
		})
	return out


def save_answers(doc, programme: str | None, answers: dict):
	"""Put a person's answers on their Data Principal (replacing earlier answers to the same questions).

	Answers come from phones that may have captured offline days ago, against an older list of
	questions or choices. One out-of-date answer must never stop the consent itself from syncing, so:
	a question that no longer exists, or a number that isn't one, is skipped; a choice that is no longer
	on the list is kept as given (it was on the list the person was shown)."""
	if not answers:
		return
	for code, value in answers.items():
		q = frappe.db.get_value("Profile Question", code, ["answer_type", "options"], as_dict=True)
		if not q:
			continue
		value = "" if value is None else str(value).strip()[:140]
		if value and q.answer_type in ("number", "year") and not value.isdigit():
			continue
		doc.set("profile_answers", [a for a in doc.get("profile_answers") or [] if a.question != code])
		if value:
			doc.append("profile_answers", {"programme": programme, "question": code, "answer": value})
