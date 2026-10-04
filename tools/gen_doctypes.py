"""Generator for Anumati DocType JSON and the reviewed role matrix (config-first).

The JSON it writes is the source of truth Frappe loads; this script just keeps 28 DocTypes consistent.
Edit here, run `python3 tools/gen_doctypes.py` from the repo root, commit the JSON. Bump TS on every
schema change so `bench migrate` re-syncs the DocTypes. Editing a DocType in the Desk builder also
works; then update this file to match."""
import json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "anumati", "anumati", "doctype")
CREATED = "2026-09-27 10:00:00.000000"
TS = "2026-10-04 10:00:00.000000"  # bump on every schema change so migrate re-syncs

def sel(*opts):
    return "\n".join(opts)

CAPTURE_MODES = sel("self_digital", "self_worker_device", "assisted_verbal", "assisted_thumbprint",
                    "assisted_witnessed", "guardian_minor", "guardian_pwd", "paper")
VERIFY_METHODS = sel("server_otp", "device_sms_otp", "reverse_sms", "missed_call", "deferred", "evidence_only")
VERIFY_STATUS = sel("captured", "recorded", "confirmed", "unconfirmed", "evidence_only")
WITHDRAW_CH = ["field_worker", "slip", "sms", "missed_call", "ivr", "whatsapp", "web", "email", "community", "api", "ussd"]
EVENT_CH = sel("app", "hosted_page", "connector", *WITHDRAW_CH)
LANG_NOTE = "Link to Frappe's Language (code, e.g. hi, mr, en)"

# ---------------------------------------------------------------- roles
ADM, DPO, OPR, PM, FW, DEV, AUD, PRC, FUN, SM = (
    "Anumati Admin", "Anumati DPO", "Anumati Operator", "Anumati Programme Manager",
    "Anumati Field Worker", "Anumati Developer", "Anumati Auditor", "Anumati Processor Partner",
    "Anumati Funder Viewer", "System Manager")

LEVELS = {
    "F": dict(read=1, write=1, create=1, delete=1, report=1, export=1, print=1, email=1, share=1),
    "E": dict(read=1, write=1, create=1, report=1, print=1),
    "W": dict(read=1, write=1),                 # edit existing only
    "C": dict(read=1, create=1),                # insert-only ledgers / capture
    "R": dict(read=1, report=1, print=1),
    "X": dict(read=1, report=1, print=1, export=1),
    "r": dict(read=1),
    "S": dict(read=1, write=1, create=1, delete=1, report=1, print=1, submit=1, cancel=1, amend=1, export=1, email=1, share=1),
}

def perms(matrix, single=False):
    out = []
    for role, lvl in matrix.items():
        p = {"role": role, "permlevel": 0}
        for k in ("read", "write", "create", "delete", "report", "export", "print", "email", "share", "submit", "cancel", "amend"):
            p[k] = LEVELS[lvl].get(k, 0)
        if single:
            for k in ("create", "delete", "report", "export", "submit", "cancel", "amend"):
                p[k] = 0
        out.append(p)
    return out

# ---------------------------------------------------------------- field helpers
def F(fieldname, fieldtype, label=None, options=None, **kw):
    d = {"fieldname": fieldname, "fieldtype": fieldtype}
    if label is None and fieldtype not in ("Column Break",):
        label = fieldname.replace("_", " ").capitalize()
    if label is not None:
        d["label"] = label
    if options is not None:
        d["options"] = options
    for k, v in kw.items():
        d[k] = 1 if v is True else v
    return d

def sec(name, label=None, **kw):
    return F(name, "Section Break", label, **kw)

def col(name):
    return F(name, "Column Break")

def tab(name, label):
    return F(name, "Tab Break", label)

RO = dict(read_only=True, no_copy=True)
LEDGER = [
    sec("chain_section", "Signature and chain", collapsible=True),
    F("chain_seq", "Int", "Chain sequence", unique=True, **RO),
    F("key_id", "Data", "Signing key ID", **RO),
    col("chain_col"),
    F("prev_hash", "Data", "Previous hash", **RO),
    F("hash", "Data", "Hash", unique=True, **RO),
    F("signature", "Small Text", "Signature (Ed25519, base64)", **RO),
]

DOCTYPES = []

def doctype(name, fields, matrix=None, **props):
    DOCTYPES.append(dict(name=name, fields=fields, matrix=matrix or {}, props=props))

def child(name, fields, **props):
    DOCTYPES.append(dict(name=name, fields=fields, matrix={}, props=dict(istable=1, editable_grid=1, **props)))

# ================================================================ child tables
child("Language Row", [F("language", "Link", "Language", "Language", reqd=True, in_list_view=True)])
child("Programme Capture Mode", [F("capture_mode", "Select", "Capture mode", CAPTURE_MODES, reqd=True, in_list_view=True)])
child("Programme Verification Method", [F("verification_method", "Select", "Verification method", VERIFY_METHODS, reqd=True, in_list_view=True)])
child("Programme Withdrawal Channel", [
    F("channel", "Select", "Channel", sel(*WITHDRAW_CH), reqd=True, in_list_view=True),
    F("show_on_receipt", "Check", "Print on receipt", default="0", in_list_view=True,
      description="Receipts show the three cheapest routes for the programme"),
])
child("Data Category Row", [F("data_category", "Link", "Data category", "Data Category", reqd=True, in_list_view=True)])
child("Notice Purpose", [
    F("purpose", "Link", "Purpose", "Purpose", reqd=True, in_list_view=True),
    F("essential", "Check", "Essential", fetch_from="purpose.essential", read_only=True, in_list_view=True),
])
child("Notice Processor", [
    F("processor", "Link", "Processor", "Processor", reqd=True, in_list_view=True),
    F("purpose", "Link", "For purpose", "Purpose", in_list_view=True),
    F("country", "Data", "Country", default="India", in_list_view=True),
    F("role", "Data", "Role", in_list_view=True),
])
child("Processor Purpose", [F("purpose", "Link", "Purpose", "Purpose", reqd=True, in_list_view=True)])
child("Breach Purpose", [F("purpose", "Link", "Purpose", "Purpose", reqd=True, in_list_view=True)])
child("Campaign Channel", [F("channel", "Select", "Channel", sel("sms", "whatsapp", "ivr", "email", "field_visit"), reqd=True, in_list_view=True)])
child("Channel Provider Template", [F("message_template", "Link", "Message template", "Message Template", reqd=True, in_list_view=True)])
child("Audit Share Programme", [F("programme", "Link", "Programme", "Programme", reqd=True, in_list_view=True)])
child("Audit Share Access", [
    F("accessed_at", "Datetime", "Accessed at", in_list_view=True, read_only=True),
    F("ip_address", "Data", "IP address", in_list_view=True, read_only=True),
])
child("Notice Purpose Translation", [
    F("purpose", "Link", "Purpose", "Purpose", reqd=True, in_list_view=True),
    F("purpose_title", "Data", "Title (translated)", in_list_view=True),
    F("description", "Small Text", "Description (translated)", in_list_view=True),
])
child("Profile Question Label", [
    F("language", "Link", "Language", "Language", reqd=True, in_list_view=True),
    F("question", "Data", "Question (translated)", reqd=True, in_list_view=True),
    F("options", "Small Text", "Choices (translated)", in_list_view=True,
      description="One per line, in the same order as the English choices"),
])
child("Programme Profile Question", [
    F("question", "Link", "Question", "Profile Question", reqd=True, in_list_view=True),
    F("required", "Check", "Answer required", in_list_view=True,
      description="Off: the person may skip it"),
    F("is_sensitive", "Check", "Sensitive", fetch_from="question.is_sensitive", read_only=True, in_list_view=True),
])
child("Profile Answer", [
    F("programme", "Link", "Asked for", "Programme", in_list_view=True),
    F("question", "Link", "Question", "Profile Question", reqd=True, in_list_view=True),
    F("answer", "Data", "Answer", in_list_view=True),
])
child("Retention System", [F("source_system", "Link", "System told", "Source System", reqd=True, in_list_view=True)])

# ================================================================ core
doctype("Anumati Settings", [
    sec("org_section", "Organisation"),
    F("org_legal_name", "Data", "Organisation legal name"),
    F("dpdp_role", "Select", "DPDP role", sel("Data Fiduciary", "Significant Data Fiduciary", "Data Processor"), default="Data Fiduciary"),
    F("residency", "Select", "Data residency", sel("India (hosted)", "India (dedicated)", "Self-hosted"), default="India (hosted)"),
    col("org_col"),
    F("dpo_name", "Data", "DPO name"),
    F("dpo_email", "Data", "DPO email", "Email"),
    F("dpo_phone", "Data", "DPO phone", "Phone"),
    F("default_languages", "Table MultiSelect", "Default languages", "Language Row"),
    F("rights_sla_days", "Int", "Rights request SLA (days)", default="30",
      description="Default response time for rights requests, pending counsel"),
    F("consent_record_retention_years", "Int", "Consent record retention (years)", default="7",
      description="Default 7 years, pending counsel. Programmes may override."),
    sec("signing_section", "Signing key", collapsible=True,
        description="Generated on install. The private key never leaves the server; a site-config key (anumati_signing_key) overrides it."),
    F("signing_key_id", "Data", "Active key ID", read_only=True),
    F("signing_public_key", "Small Text", "Active public key (base64)", read_only=True),
    F("signing_private_key", "Password", "Private key", hidden=True),
    col("signing_col"),
    F("retired_signing_keys", "JSON", "Retired public keys", read_only=True,
      description="Old keys stay here so events signed before a rotation still verify"),
    F("phone_hash_salt", "Password", "Phone hash salt", hidden=True),
    sec("chain_status_section", "Chain verification", collapsible=True),
    F("last_chain_check", "Datetime", "Last verified", read_only=True),
    F("last_chain_status", "Small Text", "Result", read_only=True),
    col("chain_status_col"),
    F("consent_anchor", "Small Text", "Consent chain checkpoint", read_only=True),
    F("audit_anchor", "Small Text", "Audit chain checkpoint", read_only=True),
    sec("voice_section", "Natural voice (Sarvam AI)", collapsible=True,
        description="Sarvam AI, an Indian company, turns notices into natural speech and can help recognise a spoken yes or no. Put the API key in the site config as sarvam_api_key, or in the field below."),
    F("sarvam_api_key", "Password", "Sarvam API key", description="Leave empty to use sarvam_api_key from the site config"),
    F("voice_female", "Select", "Woman's voice", sel("kavya", "priya", "neha", "ritu", "pooja", "simran", "shreya"),
      default="kavya", description="Played by women field workers"),
    F("voice_male", "Select", "Man's voice", sel("rahul", "amit", "rohan", "aditya", "kabir"),
      default="rahul", description="Played by men field workers (set Gender on the worker's User)"),
    F("voice_pace", "Float", "Speaking pace", default="0.9", description="1.0 is normal speed; slower is easier for older listeners"),
    col("voice_col"),
    F("voice_notice_audio", "Check", "Generate natural notice audio", default="1",
      description="Only the notice text is sent to Sarvam, never anyone's personal data. Audio is played in the field only after a reviewer approves it."),
    F("voice_listen_helper", "Check", "Help recognise a spoken yes or no",
      description="When a worker records someone saying yes, the clip is sent to Sarvam to suggest 'yes', 'no' or 'unclear'. The worker still decides; nothing is stored. Sends the person's voice to Sarvam, so first add Sarvam AI as a Processor with a signed data processing agreement and list it in your notices."),
], {ADM: "W", DPO: "r", SM: "W"}, issingle=1)

doctype("Programme", [
    tab("overview_tab", "Overview"),
    F("code", "Data", "Code", reqd=True, unique=True, description="Short, stable identifier used in APIs, e.g. MHU"),
    F("programme_name", "Data", "Programme name", reqd=True, in_list_view=True),
    F("status", "Select", "Status", sel("Draft", "Live", "Paused"), default="Draft", in_list_view=True, in_standard_filter=True),
    col("c1"),
    F("persona", "Select", "Persona", sel("beneficiary", "patient", "student", "employee", "member", "other"), default="beneficiary"),
    F("languages", "Table MultiSelect", "Languages", "Language Row"),
    tab("capture_tab", "Capture & verification"),
    sec("capture_section", "How people can consent, and how it is checked",
        description="Only the ticked ways show in the field app"),
    F("capture_modes", "Table", "Capture modes", "Programme Capture Mode"),
    col("c2"),
    F("verification_methods", "Table", "Verification methods", "Programme Verification Method"),
    sec("rules_section", "Rules"),
    F("allow_processing_before_confirm", "Check", "Allow processing before confirmation", default="1",
      description="Never applies to minors"),
    F("confirm_window_days", "Int", "Days before unconfirmed escalates", default="7"),
    F("sms_receipts", "Check", "Send SMS receipts", default="1",
      description="Needs an enabled SMS Channel Provider and approved Message Templates"),
    F("device_cache_ttl_hours", "Int", "Device consent cache TTL (hours)", default="24"),
    col("c3"),
    F("consent_validity_days", "Int", "Consent validity (days)", description="0 = no expiry; renewal campaign runs before expiry"),
    F("consent_record_retention_years", "Int", "Consent record retention (years)", default="7"),
    tab("withdrawal_tab", "Withdrawal channels"),
    sec("withdrawal_section", "Ways to withdraw", description="Withdrawing must be as easy as giving consent"),
    F("withdrawal_channels", "Table", "Withdrawal channels", "Programme Withdrawal Channel"),
    tab("profile_tab", "Extra questions"),
    sec("profile_section", "Questions about the person",
        description="Asked on the phone after the notice and choices. None are asked until you add them here. A question can be added only once the published notice mentions it (see each question's 'Notice must mention'). Reports show totals only."),
    F("profile_questions", "Table", "Questions to ask", "Programme Profile Question"),
], {ADM: "F", PM: "E", DPO: "R", OPR: "R", FW: "r", DEV: "r", SM: "F"},
    autoname="field:code", title_field="programme_name", search_fields="programme_name,status",
    show_title_field_in_link=1)

doctype("Purpose", [
    F("programme", "Link", "Programme", "Programme", reqd=True, in_list_view=True, in_standard_filter=True),
    F("code", "Data", "Code", reqd=True),
    F("purpose_title", "Data", "Title", reqd=True, in_list_view=True),
    F("description", "Small Text", "Plain-language description"),
    col("c1"),
    F("essential", "Check", "Essential", description="Explained separately; never a toggle"),
    F("is_sensitive", "Check", "Sensitive"),
    F("child_allowed", "Check", "Allowed for minors", default="1",
      description="Off hides this purpose for minors (no profiling of children)"),
    F("needs_phone", "Check", "Needs the person's phone",
      description="E.g. calls or SMS reminders. Hidden in the field app when the person has no phone"),
    F("legal_basis", "Select", "Legal basis", sel("consent", "legitimate_use", "legal_obligation"), default="consent"),
    F("dpia_required", "Check", "DPIA required"),
    sec("data_section", "Data and retention"),
    F("data_categories", "Table MultiSelect", "Data categories", "Data Category Row"),
    F("retention_policy", "Link", "Retention policy", "Retention Policy"),
], {ADM: "F", DPO: "E", PM: "R", OPR: "R", FW: "r", DEV: "r", SM: "F"},
    autoname="format:{programme}-{code}", title_field="purpose_title", show_title_field_in_link=1,
    search_fields="purpose_title,programme")

doctype("Profile Question", [
    F("code", "Data", "Code", reqd=True, unique=True, description="Short, stable identifier, e.g. occupation"),
    F("question", "Data", "Question", reqd=True, in_list_view=True),
    F("answer_type", "Select", "Answer", sel("number", "year", "choice", "text"), default="choice", in_list_view=True),
    F("options", "Small Text", "Choices", description="One per line (for Answer = choice)", depends_on="eval:doc.answer_type=='choice'"),
    col("c1"),
    F("is_sensitive", "Check", "Sensitive", in_list_view=True, in_standard_filter=True,
      description="Caste, religion, health, disability and the like. Ask only when the work truly needs it"),
    F("notice_term", "Data", "Notice must mention", reqd=True,
      description="Word or phrase the published notice must contain before a programme can ask this, e.g. occupation"),
    F("is_standard", "Check", "From the library", read_only=True),
    sec("labels_section", "Other languages"),
    F("labels", "Table", "Translations", "Profile Question Label"),
], {ADM: "F", DPO: "E", PM: "E", OPR: "R", FW: "r", DEV: "r", SM: "F"},
    autoname="field:code", title_field="question", show_title_field_in_link=1, search_fields="question")

doctype("Notice Template", [
    tab("purposes_tab", "Purposes"),
    F("programme", "Link", "Programme", "Programme", reqd=True, in_standard_filter=True),
    F("programme_name", "Data", "Programme name", fetch_from="programme.programme_name", read_only=True, in_list_view=True),
    F("version", "Data", "Version", reqd=True, in_list_view=True, description="Semantic version, e.g. 4.0.0"),
    F("status", "Select", "Status", sel("Draft", "Published", "Retired"), default="Draft", read_only=True, in_list_view=True),
    col("c1"),
    F("material_change", "Check", "Material change", description="Starts a re-consent campaign when published"),
    F("cross_border_transfers", "Small Text", "Cross-border transfers", default="None"),
    sec("purposes_section", "Purposes"),
    F("purposes", "Table", "Purposes", "Notice Purpose", reqd=True),
    F("processors", "Table", "Processors and recipients", "Notice Processor"),
    tab("content_tab", "Notice content"),
    sec("content_section", "Notice content"),
    F("summary", "Small Text", "Summary"),
    F("full_text", "Text Editor", "Full text"),
    F("pictorial_card", "Attach Image", "Pictorial card", description="Shown on the field app's notice screen"),
    sec("notice_audio_section", "Audio notice (base language)"),
    F("audio_file", "Attach", "Audio notice (woman's voice)", allow_on_submit=True, read_only=True),
    F("audio_file_male", "Attach", "Audio notice (man's voice)", allow_on_submit=True, read_only=True),
    F("audio_machine_made", "Check", "Audio is machine-made", allow_on_submit=True, read_only=True,
      description="Machine-made audio is never played in the field until a reviewer approves it"),
    F("audio_reviewed_by", "Link", "Audio approved by", "User", allow_on_submit=True, read_only=True),
    tab("rule3_tab", "Rule 3 checklist"),
    sec("rule3_section", "Rule 3 contents", description="Every notice must say all of this"),
    F("withdrawal_methods", "Small Text", "How to withdraw consent"),
    F("rights_text", "Small Text", "How to exercise rights"),
    F("board_complaint_route", "Small Text", "How to complain to the Data Protection Board"),
    col("c2"),
    F("dpo_contact", "Small Text", "DPO or grievance contact"),
    F("security_summary", "Small Text", "Summary of security safeguards"),
    tab("preview_tab", "Phone preview"),
    F("phone_preview", "HTML", "Phone preview"),
    F("amended_from", "Link", "Amended From", "Notice Template", read_only=True, no_copy=True, print_hide=True),
], {ADM: "R", DPO: "S", PM: "R", OPR: "R", FW: "r", DEV: "r", SM: "S"},
    autoname="format:{programme}-v{version}", is_submittable=1, title_field="programme_name",
    track_changes=1)

doctype("Notice Translation", [
    F("notice", "Link", "Notice", "Notice Template", reqd=True, in_list_view=True),
    F("language", "Link", "Language", "Language", reqd=True, in_list_view=True, description=LANG_NOTE),
    F("machine_translated", "Check", "Machine translated"),
    col("c1"),
    F("reviewer", "Link", "Reviewer", "User", in_list_view=True),
    F("reviewed_on", "Date", "Reviewed on"),
    sec("text_section", "Text"),
    F("summary", "Small Text", "Summary"),
    F("full_text", "Text Editor", "Full text"),
    sec("labels_section", "Button labels", description="Must match the choices; Yes to all and No to all carry equal weight"),
    F("label_yes_all", "Data", "Yes to all"),
    F("label_no_all", "Data", "No to all"),
    col("c2"),
    F("label_manage", "Data", "Manage"),
    F("label_save", "Data", "Save"),
    sec("purposes_translation_section", "Uses (translated)",
        description="The names and descriptions of the uses, shown on the choices screen in this language. Leave a row out to show the English text."),
    F("purposes", "Table", "Uses", "Notice Purpose Translation"),
    sec("rule3_translation_section", "Rule 3 contents (translated)",
        description="Leave blank to show the notice's own text"),
    F("withdrawal_methods", "Small Text", "How to withdraw consent"),
    F("rights_text", "Small Text", "How to exercise rights"),
    F("board_complaint_route", "Small Text", "How to complain to the Data Protection Board"),
    col("c_r3"),
    F("dpo_contact", "Small Text", "DPO or grievance contact"),
    F("security_summary", "Small Text", "Summary of security safeguards"),
    sec("media_section", "Audio and picture card"),
    F("audio_file", "Attach", "Audio notice (woman's voice)"),
    F("audio_file_male", "Attach", "Audio notice (man's voice)", read_only=True),
    F("audio_machine_made", "Check", "Audio is machine-made",
      description="Machine-made audio is never played in the field until a reviewer approves it"),
    F("audio_reviewed_by", "Link", "Audio reviewed by", "User"),
    col("c3"),
    F("pictorial_card", "Attach Image", "Pictorial card"),
], {ADM: "F", DPO: "E", PM: "E", OPR: "R", FW: "r", SM: "F"},
    autoname="format:{notice}-{language}", track_changes=1)

doctype("Data Principal", [
    tab("overview_tab", "Overview"),
    F("principal_ref", "Data", "Beneficiary ID", unique=True, in_list_view=True,
      description="ID from the host system, e.g. MHU-004211. Never a name or phone number."),
    F("full_name", "Password", "Name (encrypted)", description="Stored encrypted; not searchable"),
    F("phone", "Password", "Phone (encrypted)"),
    F("phone_hash", "Data", "Phone hash", read_only=True, search_index=True, no_copy=True,
      description="Salted HMAC of the normalised number; used for lookups"),
    F("name_index", "Small Text", "Name search codes", read_only=True, hidden=True, no_copy=True, print_hide=True,
      description="One salted code per word of the name, for whole-word search; the name itself stays encrypted"),
    F("email", "Data", "Email", "Email"),
    col("c1"),
    F("preferred_language", "Link", "Preferred language", "Language", in_list_view=True, in_standard_filter=True),
    F("persona", "Select", "Persona", sel("beneficiary", "patient", "student", "employee", "member", "other"), default="beneficiary"),
    F("date_of_birth", "Date", "Date of birth"),
    F("birth_year", "Int", "Year of birth", description="Enough for children: consent is renewed by the person at 18"),
    F("adult_on", "Date", "Turns 18 by", read_only=True, no_copy=True,
      description="From the date of birth, or 31 December of the year they turn 18"),
    F("age_band", "Select", "Age band", sel("", "under_18", "18_plus", "unknown")),
    F("phone_owner_relation", "Select", "Phone owner", sel("self", "spouse", "parent", "child", "sibling", "relative", "neighbour", "field_worker", "other"), default="self"),
    tab("flags_tab", "Needs & lifecycle"),
    sec("flags_section", "Segment flags"),
    F("is_minor", "Check", "Minor (under 18)", in_standard_filter=True),
    F("pwd_guarded", "Check", "Person with disability, lawful guardian"),
    F("needs_assistance", "Check", "Needs help to read the notice"),
    col("c2"),
    F("shared_phone", "Check", "Shared phone", in_standard_filter=True),
    F("no_phone", "Check", "No phone"),
    F("renewal_due", "Check", "Turned 18: renew consent", read_only=True, in_standard_filter=True,
      description="Set on the day a child turns 18. Their guardian's consent stops counting until they consent themselves"),
    sec("lifecycle_section", "Lifecycle"),
    F("relationship_ended_on", "Date", "Relationship ended on",
      description="Cessation: starts retention clocks that run from 'relationship ended'"),
    col("c3"),
    F("merged_into", "Link", "Merged into", "Data Principal", read_only=True),
    tab("profile_tab", "About the person"),
    sec("profile_section", "Answers to extra questions", description="Reports show totals only"),
    F("profile_answers", "Table", "Answers", "Profile Answer"),
    tab("nominee_tab", "Nominees"),
    sec("nominee_section", "Nominees"),
    F("nominees", "Table", "Nominees", "Nominee"),
], {ADM: "F", DPO: "E", OPR: "E", PM: "R", FW: "E", SM: "F"},
    autoname="hash", title_field="principal_ref", search_fields="principal_ref", show_title_field_in_link=1,
    track_changes=1)

doctype("Guardian Link", [
    F("principal", "Link", "Beneficiary", "Data Principal", reqd=True, in_list_view=True),
    F("guardian", "Link", "Guardian", "Data Principal", reqd=True, in_list_view=True),
    F("guardian_type", "Select", "Guardian type", sel("parent", "legal_guardian", "family_pwd", "court", "committee"), reqd=True, in_list_view=True),
    F("relation", "Data", "Relation"),
    col("c1"),
    F("authority_ref", "Data", "Order number",
      description="Number of the order that appointed the guardian (Local Level Committee, court or other authority). "
                  "Needed for every guardian except a parent"),
    F("evidence", "Attach", "Order or document photo", description="Photo of the appointment order, when one was taken"),
    F("id_document", "Attach", "Guardian's ID photo", description="Optional; the proof when the guardian has no phone"),
    F("verification_method", "Select", "Verification method", sel("device_sms_otp", "server_otp", "digilocker", "document", "witness")),
    F("verified_on", "Datetime", "Verified on"),
    F("valid_until", "Date", "Valid until", description="For minors: 18th birthday plus grace period"),
], {ADM: "F", DPO: "E", OPR: "E", FW: "E", PM: "R", SM: "F"}, autoname="hash", track_changes=1)

doctype("Consent Event", [
    tab("summary_tab", "Summary"),
    F("summary_html", "HTML", "Summary"),
    sec("record_section", "Record"),
    F("event_uuid", "Data", "Event UUID", reqd=True, unique=True,
      description="Client-generated; sync is idempotent on this"),
    F("short_code", "Data", "Receipt code", read_only=True, search_index=True, no_copy=True, in_list_view=True,
      description="Printed on receipts and slips; derived from the signed hash"),
    F("action", "Select", "Action", sel("grant", "withdraw", "refuse", "renew"), reqd=True, in_list_view=True, in_standard_filter=True),
    F("principal", "Link", "Beneficiary", "Data Principal", reqd=True, in_list_view=True),
    F("programme", "Link", "Programme", "Programme", reqd=True, in_list_view=True, in_standard_filter=True),
    F("notice", "Link", "Notice", "Notice Template"),
    F("notice_version", "Data", "Notice version"),
    F("language", "Link", "Language", "Language"),
    F("notice_delivery", "Select", "How the notice was given",
      sel("", "recording", "phone_voice", "read_aloud", "read_on_screen"), in_standard_filter=True,
      description="Coaching data, not signed: reviewed recording, phone voice, worker read it, or read on screen"),
    F("notice_completed", "Check", "Notice heard or read in full", in_standard_filter=True),
    col("c1"),
    F("purposes_granted", "JSON", "Purposes granted"),
    F("purposes_denied", "JSON", "Purposes denied"),
    F("capture_mode", "Select", "How consent was given", CAPTURE_MODES, in_standard_filter=True),
    F("channel", "Select", "Channel", EVENT_CH),
    F("captured_by", "Link", "Recorded by", "User", in_standard_filter=True),
    F("guardian_link", "Link", "Guardian link", "Guardian Link"),
    F("source_system", "Link", "Source system", "Source System"),
    tab("evidence_tab", "Evidence"),
    sec("evidence_section", "Evidence"),
    F("witness", "Password", "Witness (encrypted)", description="Name and relation; stored encrypted"),
    F("witness_digest", "Data", "Witness digest", read_only=True, no_copy=True,
      description="SHA-256 of the witness text; this, not the text, is signed"),
    F("evidence", "JSON", "Evidence files", description='List of {"file": ..., "sha256": ..., "kind": ...}'),
    col("c2"),
    F("verification_method", "Select", "Verification method", sel("", *VERIFY_METHODS.split("\n"))),
    F("verification_status", "Select", "Confirmation when recorded", VERIFY_STATUS, default="recorded",
      description="Later confirmation lives in Verification Attempt and Consent State; this event never changes"),
    tab("device_tab", "Device & time"),
    sec("device_section", "Device and time"),
    F("device_id", "Data", "Device ID"),
    F("device_time", "Datetime", "Device time"),
    F("server_time", "Datetime", "Server time", read_only=True),
    col("c3"),
    F("ip_address", "Data", "IP address", description="Optional; offline captures have none"),
    F("gps", "Data", "GPS (lat,long)"),
    tab("proof_tab", "Proof"),
    *LEDGER,
], {ADM: "X", DPO: "X", OPR: "R", PM: "R", FW: "C", SM: "C"},
    autoname="field:event_uuid", in_create=1, sort_field="creation", sort_order="DESC",
    title_field="short_code", show_title_field_in_link=1, search_fields="short_code,principal")

doctype("Consent State", [
    F("principal", "Link", "Beneficiary", "Data Principal", reqd=True, in_list_view=True),
    F("programme", "Link", "Programme", "Programme", reqd=True, in_standard_filter=True),
    F("purpose", "Link", "Purpose", "Purpose", reqd=True, in_list_view=True, in_standard_filter=True),
    col("c1"),
    F("status", "Select", "Status", sel("granted", "withdrawn", "refused", "not_asked", "expired"), reqd=True, in_list_view=True, in_standard_filter=True),
    F("verification_status", "Select", "Confirmation", VERIFY_STATUS, in_list_view=True, in_standard_filter=True),
    F("last_event", "Link", "Last event", "Consent Event"),
    F("updated", "Datetime", "Updated"),
], {ADM: "R", DPO: "R", OPR: "R", PM: "R", FW: "r", DEV: "r", SM: "F"},
    autoname="format:{principal}-{purpose}", in_create=1,
    description="Projection of Consent Events for fast enforcement. Rebuilt from events; never edited by hand.")

doctype("Verification Attempt", [
    F("consent_event", "Link", "Consent event", "Consent Event", reqd=True, in_list_view=True),
    F("verification_method", "Select", "Method", VERIFY_METHODS, reqd=True, in_list_view=True),
    F("channel", "Select", "Channel", sel("sms", "whatsapp", "ivr", "missed_call", "device_sms", "in_person")),
    F("result", "Select", "Result", sel("pending", "confirmed", "failed", "expired"), default="pending", in_list_view=True),
    col("c1"),
    F("sent_at", "Datetime", "Sent at"),
    F("delivered_at", "Datetime", "Delivered at"),
    F("code_hash", "Data", "Code hash"),
    F("response", "Small Text", "Response"),
], {ADM: "R", DPO: "R", OPR: "E", FW: "C", PM: "R", SM: "F"}, autoname="hash")

# ================================================================ rights, channels, governance
doctype("Rights Request", [
    tab("request_tab", "Request"),
    F("request_type", "Select", "Type", sel("withdrawal", "access", "correction", "erasure", "grievance", "nomination"), default="grievance", reqd=True, in_list_view=True, in_standard_filter=True),
    F("channel", "Select", "Channel", sel(*WITHDRAW_CH), default="email", reqd=True, in_list_view=True),
    F("status", "Select", "Status", sel("Open", "Unmatched", "In Progress", "Awaiting Acknowledgement", "Closed", "Rejected"), default="Open", in_list_view=True, in_standard_filter=True),
    F("received_on", "Datetime", "Received on", default="now", reqd=True, description="SLA clock starts here, not at match"),
    F("sla_due", "Date", "Due by", in_list_view=True, description="Received on + the SLA days in Anumati Settings, unless set"),
    F("subject", "Data", "Subject"),
    col("c1"),
    F("matched_principal", "Link", "Beneficiary", "Data Principal", in_standard_filter=True),
    F("match_confidence", "Percent", "Match confidence"),
    F("candidates", "Small Text", "Possible matches", read_only=True,
      description="Beneficiary IDs sharing the sender's number; use 'Who is this for?' to pick one"),
    F("assigned_to", "Link", "Assigned to", "User", in_standard_filter=True),
    F("paper_trail_number", "Data", "Paper-trail number", description="Printed on slips so offline requests reconcile"),
    F("linked_event", "Link", "Resulting consent event", "Consent Event", read_only=True),
    sec("sender_section", "Sender", collapsible=True),
    F("raised_by", "Data", "Sender email", "Email", description="Set when the request arrives by email"),
    F("sender_hash", "Data", "Sender phone hash", read_only=True, search_index=True,
      description="Salted hash of the sender's number; the number itself is not stored"),
    tab("detail_tab", "Details"),
    sec("detail_section", "Details"),
    F("raw_payload", "Long Text", "Raw payload", description="As received from the channel"),
    F("resolution", "Small Text", "Resolution"),
    F("evidence", "Attach", "Evidence"),
], {ADM: "F", DPO: "F", OPR: "E", FW: "C", PM: "R", SM: "F"},
    autoname="format:RQ-{#####}", track_changes=1, sort_field="creation", sort_order="DESC",
    email_append_to=1, subject_field="subject", sender_field="raised_by", has_web_view=0, title_field="subject")

doctype("Channel Provider", [
    F("provider_name", "Data", "Name", reqd=True, unique=True),
    F("provider_type", "Select", "Type", sel("SMS", "WhatsApp", "IVR", "Missed Call", "Email"), reqd=True, in_list_view=True),
    F("provider", "Select", "Provider", sel("MSG91", "Gupshup", "Glific", "Exotel", "SMTP", "Other"), reqd=True, in_list_view=True),
    F("enabled", "Check", "Enabled", default="1", in_list_view=True),
    F("pooled", "Check", "Pooled (Dhwani) account", description="Off = the organisation's own account (BYO)"),
    col("c1"),
    F("sender_id", "Data", "Sender ID / number"),
    F("dlt_entity_id", "Data", "DLT entity ID"),
    sec("credentials_section", "Credentials", description="Stored encrypted. Enter them here, never in chat or email."),
    F("api_key", "Password", "API key"),
    F("api_secret", "Password", "API secret"),
    F("webhook_secret", "Password", "Inbound webhook secret", description="Used to check HMAC on inbound callbacks"),
    sec("templates_section", "Templates"),
    F("templates", "Table MultiSelect", "Message templates", "Channel Provider Template"),
], {ADM: "F", SM: "F"}, autoname="field:provider_name")

doctype("Processor", [
    F("processor_name", "Data", "Name", reqd=True, unique=True),
    F("contact_name", "Data", "Contact name"),
    F("contact_email", "Data", "Contact email", "Email"),
    F("country", "Data", "Country", default="India"),
    col("c1"),
    F("dpa_reference", "Data", "DPA reference"),
    F("dpa_file", "Attach", "DPA document"),
    F("due_diligence_done", "Check", "Privacy due diligence done"),
    sec("integration_section", "Integration"),
    F("webhook_url", "Data", "Webhook URL", "URL"),
    F("webhook_secret", "Password", "Webhook secret"),
    F("purposes", "Table MultiSelect", "Purposes", "Processor Purpose"),
], {ADM: "F", DPO: "E", PM: "R", OPR: "R", PRC: "r", SM: "F"}, autoname="field:processor_name", track_changes=1)

doctype("Propagation Ack", [
    F("processor", "Link", "Processor", "Processor", in_list_view=True),
    F("source_system", "Link", "Source system", "Source System"),
    F("reference_doctype", "Link", "Reference type", "DocType", reqd=True),
    F("reference_name", "Dynamic Link", "Reference", "reference_doctype", reqd=True, in_list_view=True),
    F("status", "Select", "Status", sel("Pending", "Sent", "Acknowledged", "Completed", "Failed", "Overdue"), default="Pending", in_list_view=True),
    col("c1"),
    F("sent_at", "Datetime", "Sent at"),
    F("acked_at", "Datetime", "Acknowledged at"),
    F("completed_at", "Datetime", "Completed at"),
    F("evidence_hash", "Data", "Evidence hash", description="Proof of action from the partner"),
    F("deletion_reference", "Data", "Deletion reference"),
    F("response", "Small Text", "Response"),
], {ADM: "R", DPO: "E", OPR: "E", PRC: "r", SM: "F"}, autoname="hash", track_changes=1)

doctype("Campaign", [
    F("campaign_name", "Data", "Name", reqd=True, in_list_view=True),
    F("campaign_type", "Select", "Type", sel("true_up", "re_consent", "renewal", "majority_transfer"), reqd=True, in_list_view=True),
    F("campaign_trigger", "Select", "Trigger", sel("manual", "material_notice_change", "turning_18", "validity_expiry", "retention_notice"), default="manual"),
    F("status", "Select", "Status", sel("Draft", "Scheduled", "Running", "Completed", "Cancelled"), default="Draft", in_list_view=True),
    col("c1"),
    F("programme", "Link", "Programme", "Programme", reqd=True),
    F("notice", "Link", "Notice", "Notice Template"),
    F("deadline", "Date", "Deadline"),
    F("fallback_outcome", "Select", "If no response or refusal", sel("no_processing", "erase", "legitimate_use", "legal_retention", "hold_for_review")),
    sec("audience_section", "Audience and channels"),
    F("audience", "Small Text", "Audience"),
    F("source_file", "Attach", "Import file"),
    F("channels", "Table", "Channels", "Campaign Channel"),
    sec("stats_section", "Progress"),
    F("principals_imported", "Int", "Imported", read_only=True),
    F("sent", "Int", "Sent", read_only=True),
    col("c2"),
    F("opted_in", "Int", "Opted in", read_only=True),
    F("refused", "Int", "Refused", read_only=True),
    F("no_response", "Int", "No response", read_only=True),
], {ADM: "F", DPO: "E", PM: "E", OPR: "R", SM: "F"}, autoname="hash", title_field="campaign_name", track_changes=1)

doctype("Retention Policy", [
    F("policy_name", "Data", "Name", reqd=True, unique=True),
    F("data_category", "Link", "Data category", "Data Category", in_list_view=True),
    F("duration_value", "Int", "Keep for", reqd=True, in_list_view=True),
    F("duration_unit", "Select", "Unit", sel("days", "months", "years"), default="months", reqd=True, in_list_view=True),
    col("c1"),
    F("start_event", "Select", "Clock starts at", sel("collection", "withdrawal", "relationship_ended"), reqd=True, in_list_view=True),
    F("action_at_expiry", "Select", "At the end", sel("erase", "anonymise", "ask_processor_to_erase", "legal_hold_then_review"), reqd=True, in_list_view=True),
    F("advance_notice_days", "Int", "Advance notice (days)", default="30"),
    sec("systems_section", "Systems told"),
    F("systems", "Table MultiSelect", "Systems told", "Retention System"),
], {ADM: "F", DPO: "E", PM: "R", SM: "F"}, autoname="field:policy_name", track_changes=1)

doctype("Data Category", [
    F("category_name", "Data", "Name", reqd=True, unique=True),
    F("is_sensitive", "Check", "Sensitive", in_list_view=True),
    F("description", "Small Text", "Description"),
], {ADM: "F", DPO: "E", PM: "R", OPR: "r", FW: "r", SM: "F"}, autoname="field:category_name")

doctype("Purge Request", [
    F("principal", "Link", "Beneficiary", "Data Principal", reqd=True, in_list_view=True),
    F("purpose", "Link", "Purpose", "Purpose", in_list_view=True),
    F("data_category", "Link", "Data category", "Data Category"),
    F("purge_action", "Select", "Action", sel("hard_purge", "anonymise", "legal_hold"), default="hard_purge", reqd=True),
    F("status", "Select", "Status", sel("Scheduled", "Notified", "Requested", "Acknowledged", "Completed", "On Hold"), default="Scheduled", in_list_view=True),
    col("c1"),
    F("due_on", "Date", "Deadline", reqd=True),
    F("notified_on", "Datetime", "Beneficiary told on"),
    F("purged_on", "Datetime", "Purged on"),
    F("rights_request", "Link", "Rights request", "Rights Request"),
    F("retention_policy", "Link", "Retention policy", "Retention Policy"),
    sec("hold_section", "Legal hold"),
    F("legal_hold", "Check", "Legal hold"),
    F("hold_reason", "Small Text", "Reason"),
], {ADM: "F", DPO: "E", OPR: "E", SM: "F"}, autoname="format:PRG-{#####}", track_changes=1,
    description="System acknowledgements are tracked in Propagation Ack. A purpose with no linked system still creates a DPO task.")

doctype("ROPA Entry", [
    F("purpose", "Link", "Purpose", "Purpose", reqd=True, unique=True, in_list_view=True),
    F("status", "Select", "Status", sel("Draft", "Approved", "Retired"), default="Draft", read_only=True, in_list_view=True,
      description="Set by the ROPA workflow; only the DPO approves"),
    F("data_categories", "Table MultiSelect", "Data categories", "Data Category Row"),
    F("data_subjects", "Small Text", "Data principals concerned"),
    col("c1"),
    F("recipients", "Small Text", "Recipients"),
    F("retention", "Data", "Retention"),
    F("safeguards", "Small Text", "Safeguards"),
    sec("dpia_section", "Data protection impact assessment"),
    F("dpia_required", "Check", "DPIA required", fetch_from="purpose.dpia_required", fetch_if_empty=True),
    F("dpia_necessity", "Small Text", "Why this is needed"),
    F("dpia_minimisation", "Small Text", "Minimisation"),
    col("c2"),
    F("dpia_risks", "Small Text", "Risks"),
    F("dpia_safeguards", "Small Text", "Safeguards"),
    F("dpia_residual_risk", "Select", "Residual risk", sel("", "Low", "Medium", "High")),
    sec("signoff_section", "DPO approval"),
    F("dpo_approval", "Check", "I have reviewed this assessment and approve the purpose",
      description="Required before a DPO can approve a record that needs a DPIA. Who approved and when is in the document history."),
], {ADM: "R", DPO: "F", PM: "R", AUD: "r", SM: "F"}, autoname="hash", title_field="purpose", track_changes=1)

doctype("Breach Incident", [
    tab("incident_tab", "Incident"),
    F("breach_type", "Select", "What kind", sel("data_leak", "lost_device", "phishing", "ransomware", "unauthorised_access"), reqd=True, in_list_view=True),
    F("detected_on", "Datetime", "Discovered", reqd=True, in_list_view=True),
    F("programme", "Link", "Programme", "Programme"),
    F("status", "Select", "Status", sel("Assessing", "Contained", "Notifying", "Reported", "Closed"), default="Assessing", in_list_view=True),
    col("c1"),
    F("principals_affected", "Int", "People possibly affected"),
    F("field_device", "Link", "Field device", "Field Device", depends_on="eval:doc.breach_type=='lost_device'"),
    F("purposes_affected", "Table MultiSelect", "Purposes affected", "Breach Purpose"),
    sec("detail_section", "What happened"),
    F("description", "Small Text", "Description"),
    tab("steps_tab", "72-hour steps"),
    sec("steps_section", "Steps (72-hour clock)"),
    F("contained_on", "Datetime", "Contained"),
    F("risk_assessed_on", "Datetime", "Risk assessed"),
    F("principals_notified_on", "Datetime", "Affected people told"),
    F("notifications_sent", "Int", "Notifications sent", read_only=True),
    col("c2"),
    F("board_intimated_on", "Datetime", "Board intimated"),
    F("board_report_on", "Datetime", "Detailed Board report"),
    F("dpb_report", "Attach", "Board report file"),
    F("closed_on", "Datetime", "Closed"),
], {ADM: "F", DPO: "F", SM: "F"}, autoname="format:BR-{###}", track_changes=1)

doctype("Audit Entry", [
    F("action", "Select", "Action", sel("insert", "update", "submit", "cancel", "delete", "other"), reqd=True, in_list_view=True, in_standard_filter=True),
    F("ref_doctype", "Link", "Document type", "DocType", in_list_view=True, in_standard_filter=True),
    F("ref_name", "Data", "Document"),
    F("actor", "Link", "Actor", "User", in_list_view=True),
    F("logged_at", "Datetime", "Action time", read_only=True),
    col("c1"),
    F("source_doctype", "Select", "Sealed from", sel("Version", "Deleted Document"), read_only=True),
    F("source_name", "Data", "Source record", unique=True, read_only=True),
    F("before_hash", "Data", "Before hash", read_only=True),
    F("after_hash", "Data", "After hash", read_only=True),
    F("remarks", "Small Text", "Remarks", read_only=True, description="Never contains personal data"),
    *LEDGER,
], {ADM: "R", DPO: "X", AUD: "r", SM: "R"},
    autoname="hash", in_create=1,
    description="Frappe Version and Deleted Document records, sealed into a signed hash chain every few minutes.", sort_field="creation", sort_order="DESC")

# ================================================================ v0.2.1
doctype("Source System", [
    F("system_name", "Data", "Name", reqd=True, unique=True),
    F("system_type", "Select", "Type", sel("Collect", "ODK", "CommCare", "Frappe", "OpenMRS", "Web", "API"), reqd=True, in_list_view=True),
    F("programme", "Link", "Programme", "Programme", in_list_view=True),
    F("enabled", "Check", "Enabled", default="1"),
    col("c1"),
    F("api_user", "Link", "API user", "User", description="The API key belongs to this user; scopes come from its roles"),
    F("purge_endpoint", "Data", "Purge endpoint", "URL"),
], {ADM: "F", DEV: "E", DPO: "R", SM: "F"}, autoname="field:system_name", track_changes=1)

doctype("System Usage Log", [
    F("source_system", "Link", "Source system", "Source System", in_list_view=True),
    F("principal", "Link", "Beneficiary", "Data Principal", in_list_view=True),
    F("purpose", "Link", "Purpose", "Purpose", in_list_view=True),
    F("checked_at", "Datetime", "Checked at"),
    F("result", "Select", "Result", sel("allow", "deny"), in_list_view=True),
], {ADM: "R", DPO: "R", DEV: "r", SM: "R"}, autoname="hash", in_create=1)

doctype("Message Template", [
    F("template_event", "Select", "Event", sel("receipt", "confirmation", "deferred_confirmation", "withdrawal_confirmation", "otp", "reminder", "renewal", "retention_notice", "breach_notice", "rights_update"), reqd=True, in_list_view=True),
    F("channel", "Select", "Channel", sel("sms", "whatsapp", "ivr", "email"), reqd=True, in_list_view=True),
    F("language", "Link", "Language", "Language", reqd=True, in_list_view=True),
    col("c1"),
    F("dlt_template_id", "Data", "MSG91 template ID", description="The MSG91 template (flow) ID, registered against the DLT template"),
    F("send_via", "Select", "Send via", sel("Flow", "SendOTP"), default="Flow", depends_on="eval:doc.channel=='sms'",
      description="SendOTP: MSG91's OTP service, for an approved OTP template (the code is still made and checked by Anumati)"),
    F("approved", "Check", "Approved", in_list_view=True),
    sec("body_section"),
    F("body", "Small Text", "Body", reqd=True),
], {ADM: "F", DPO: "E", PM: "E", OPR: "R", SM: "F"}, autoname="format:{template_event}-{channel}-{language}", track_changes=1)

child("Nominee", [
    F("nominee_name", "Password", "Name (encrypted)", in_list_view=True),
    F("relation", "Data", "Relation", in_list_view=True),
    F("contact", "Password", "Contact (encrypted)"),
    F("evidence", "Attach", "Evidence"),
    F("nominated_on", "Date", "Nominated on", in_list_view=True),
])

# ================================================================ v0.3
doctype("Field Device", [
    F("device_id", "Data", "Device ID", reqd=True, unique=True),
    F("user", "Link", "User", "User", in_list_view=True),
    F("status", "Select", "Status", sel("active", "logged_out", "wipe_queued", "wiped", "lost"), default="active", in_list_view=True),
    col("c1"),
    F("app_version", "Data", "App version"),
    F("last_sync", "Datetime", "Last sync", in_list_view=True),
    F("pending_events", "Int", "Pending events"),
    F("model", "Data", "Phone model"),
    sec("lost_section", "Lost or stolen", collapsible=True),
    F("reported_lost_on", "Datetime", "Reported lost on", read_only=True),
    F("reported_lost_by", "Link", "Reported lost by", "User", read_only=True),
    col("c2"),
    F("wiped_on", "Datetime", "Wipe sent on", read_only=True,
      description="When the phone was told to wipe itself; it signs out and deletes its data"),
], {ADM: "F", PM: "E", DPO: "R", FW: "r", SM: "F"}, autoname="field:device_id", track_changes=1)

doctype("Audit Share", [
    F("period_from", "Date", "Period from", reqd=True),
    F("period_to", "Date", "Period to", reqd=True),
    F("programmes", "Table MultiSelect", "Programmes", "Audit Share Programme"),
    col("c1"),
    F("expires_on", "Datetime", "Expires on", reqd=True, in_list_view=True),
    F("revoked", "Check", "Revoked", in_list_view=True),
    F("names_hidden", "Check", "Names hidden", default="1", read_only=True, description="Always on"),
    F("token_hash", "Data", "Token hash", read_only=True, no_copy=True),
    sec("access_section", "Every view is logged"),
    F("access_log", "Table", "Access log", "Audit Share Access", read_only=True),
], {DPO: "F", ADM: "R", SM: "F"}, autoname="hash", track_changes=1)

doctype("Funder Link", [
    F("funder_name", "Data", "Funder", reqd=True, in_list_view=True),
    F("contact_name", "Data", "Contact name"),
    F("contact_email", "Data", "Contact email", "Email"),
    F("grantee_consent", "Check", "Grantee agrees to share", in_list_view=True,
      description="Off by default. Aggregate numbers only, never beneficiary data."),
    F("expires_on", "Date", "Link expires on"),
    col("c1"),
    F("share_programmes", "Check", "Programmes"),
    F("share_confirmed_rate", "Check", "Confirmed rate"),
    F("share_requests_on_time", "Check", "Requests on time"),
    F("share_chain_status", "Check", "Chain status"),
    F("share_languages", "Check", "Reviewed languages"),
], {ADM: "F", DPO: "E", FUN: "r", SM: "F"}, autoname="hash", title_field="funder_name", track_changes=1)



# ---------------------------------------------------------------- emit
def scrub(n):
    return n.lower().replace(" ", "_").replace("-", "_")

CONTROLLER = '''# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

from frappe.model.document import Document


class {cls}(Document):
\tpass
'''

# Connections shown on the form dashboard (stock Frappe "Document Links").
LINKS = {
    "Programme": [("Setup", "Purpose", "programme"), ("Setup", "Notice Template", "programme"),
                  ("Consent", "Consent Event", "programme"), ("Consent", "Campaign", "programme"),
                  ("Integration", "Source System", "programme")],
    "Purpose": [("Governance", "ROPA Entry", "purpose"), ("Governance", "Purge Request", "purpose")],
    "Notice Template": [("Content", "Notice Translation", "notice"), ("Consent", "Consent Event", "notice")],
    "Data Principal": [("Consent", "Consent Event", "principal"), ("Consent", "Consent State", "principal"),
                       ("Consent", "Guardian Link", "principal"), ("Rights", "Rights Request", "matched_principal"),
                       ("Rights", "Purge Request", "principal")],
    "Consent Event": [("Verification", "Verification Attempt", "consent_event")],
    "Processor": [("Routing", "Propagation Ack", "processor")],
    "Field Device": [("Incidents", "Breach Incident", "field_device")],
}

NO_VERSION = {"Consent Event", "Audit Entry", "Consent State", "System Usage Log", "Verification Attempt"}
TRACK_VIEWS = {"Data Principal", "Guardian Link", "Consent Event", "Rights Request"}

def emit():
    counts = {"doctype": 0, "child": 0}
    for dt in DOCTYPES:
        name, fields, props = dt["name"], dt["fields"], dt["props"]
        folder = os.path.join(ROOT, scrub(name))
        os.makedirs(folder, exist_ok=True)
        istable = props.get("istable")
        counts["child" if istable else "doctype"] += 1
        d = {
            "actions": [],
            "allow_rename": 0,
            "creation": CREATED,
            "doctype": "DocType",
            "engine": "InnoDB",
            "field_order": [f["fieldname"] for f in fields],
            "fields": fields,
            "index_web_pages_for_search": 0,
            "links": [{"group": g, "link_doctype": dt, "link_fieldname": f} for g, dt, f in LINKS.get(name, [])],
            "modified": TS,
            "modified_by": "Administrator",
            "module": "Anumati",
            "name": name,
            "owner": "Administrator",
            "permissions": perms(dt["matrix"], single=bool(props.get("issingle"))),
            "sort_field": props.pop("sort_field", "modified"),
            "sort_order": props.pop("sort_order", "DESC"),
            "states": [],
        }
        auto = props.get("autoname")
        if auto:
            d["naming_rule"] = {"hash": "Random"}.get(auto) or ("By fieldname" if auto.startswith("field:") else "Expression")
        if not istable and name not in NO_VERSION:
            d["track_changes"] = 1
        if name in TRACK_VIEWS:
            d["track_views"] = 1  # stock View Log = PII access log (who opened which record)
        d.update(props)
        with open(os.path.join(folder, scrub(name) + ".json"), "w") as fh:
            json.dump(d, fh, indent=1, sort_keys=True, ensure_ascii=False)
            fh.write("\n")
        open(os.path.join(folder, "__init__.py"), "w").close()
        py = os.path.join(folder, scrub(name) + ".py")
        if not os.path.exists(py):
            with open(py, "w") as fh:
                fh.write(CONTROLLER.format(cls=name.replace(" ", "")))
    print(counts)

if __name__ == "__main__":
    emit()
    matrix = {}
    for dt in DOCTYPES:
        if dt["props"].get("istable"):
            continue
        single = bool(dt["props"].get("issingle"))
        matrix[dt["name"]] = {p["role"]: sorted(k for k, v in p.items() if v == 1 and k != "permlevel")
                              for p in perms(dt["matrix"], single)}
    with open(os.path.join(REPO, "anumati", "tests", "role_matrix.json"), "w") as fh:
        json.dump(matrix, fh, indent=1, sort_keys=True)
        fh.write("\n")
