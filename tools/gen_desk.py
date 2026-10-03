"""Generator for the Desk console (config-first, stock Frappe only).

Writes standard records that `bench migrate` loads: Workspaces, Number Cards, Dashboard Charts and
Module Onboarding (module folders), plus fixtures for the Custom HTML Block, Kanban Board, saved
List Filters and Custom DocPerm. Nothing here replaces a Frappe page or view.

Edit here, run `python3 tools/gen_desk.py` from the repo root, commit the JSON. Bump TS on every change."""
import json, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(REPO, "anumati", "anumati")
FIX = os.path.join(REPO, "anumati", "fixtures")
TS = "2026-10-01 10:00:00.000000"

ADM, DPO, OPR, PM, SM = "Anumati Admin", "Anumati DPO", "Anumati Operator", "Anumati Programme Manager", "System Manager"


def scrub(n):
    return n.lower().replace(" ", "_").replace("-", "_")


def write(folder, name, doc):
    path = os.path.join(MOD, folder, scrub(name))
    os.makedirs(path, exist_ok=True)
    open(os.path.join(path, "__init__.py"), "w").close()
    base = {"creation": TS, "docstatus": 0, "idx": 0, "modified": TS, "modified_by": "Administrator",
            "module": "Anumati", "name": name, "owner": "Administrator"}
    with open(os.path.join(path, scrub(name) + ".json"), "w") as fh:
        json.dump({**base, **doc}, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def fixture(name, rows):
    rows = [{**r, "modified": TS} for r in rows]
    with open(os.path.join(FIX, name + ".json"), "w") as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


# ---------------------------------------------------------------- number cards
def card(label, doctype, filters=(), dynamic=(), color="Blue", stats=False, total_of=None):
    write("number_card", label, {
        "doctype": "Number Card", "label": label, "type": "Document Type", "document_type": doctype,
        "function": "Sum" if total_of else "Count", **({"aggregate_function_based_on": total_of} if total_of else {}),
        "color": color, "is_public": 1, "is_standard": 1,
        "filters_json": json.dumps([[doctype, *f, False] for f in filters]),
        "dynamic_filters_json": json.dumps([[doctype, *f] for f in dynamic]),
        "show_percentage_stats": 1 if stats else 0, "stats_time_interval": "Weekly",
    })
    return label


OPEN = ["status", "not in", ["Closed", "Rejected"]]
CARDS = {
    # existing cards, rewritten so the whole console lives in one place
    "consents_week": card("Consents This Week", "Consent Event", [["action", "in", ["grant", "renew"]], ["creation", "Timespan", "this week"]], color="Green", stats=True),
    "withdrawals_week": card("Withdrawals This Week", "Consent Event", [["action", "=", "withdraw"], ["creation", "Timespan", "this week"]], color="Red", stats=True),
    "open_requests": card("Open Rights Requests", "Rights Request", [OPEN], color="Orange"),
    "unmatched": card("Unmatched Requests", "Rights Request", [["status", "=", "Unmatched"]], color="Red"),
    "heard": card("Notice Heard In Full", "Consent Event", [["notice_completed", "=", 1], ["creation", "Timespan", "this week"]], stats=True),
    # new
    "overdue": card("Overdue Requests", "Rights Request", [OPEN], dynamic=[["sla_due", "<", "frappe.datetime.get_today()"]], color="Red"),
    "unconfirmed": card("Waiting For Confirmation", "Consent State", [["status", "=", "granted"], ["verification_status", "=", "unconfirmed"]], color="Orange"),
    "consents_month": card("Consents This Month", "Consent Event", [["action", "in", ["grant", "renew"]], ["creation", "Timespan", "this month"]], color="Green", stats=True),
    "withdrawals_month": card("Withdrawals This Month", "Consent Event", [["action", "=", "withdraw"], ["creation", "Timespan", "this month"]], color="Red", stats=True),
    "refused_month": card("Refused This Month", "Consent Event", [["action", "=", "refuse"], ["creation", "Timespan", "this month"]], color="Grey"),
    "not_synced": card("Phones Not Synced", "Field Device", [["status", "=", "active"]], dynamic=[["last_sync", "<", "moment(frappe.datetime.get_today()).subtract(2, 'days').format('YYYY-MM-DD')"]], color="Orange"),
    "breaches": card("Open Breaches", "Breach Incident", [["status", "!=", "Closed"]], color="Red"),
    "unreviewed": card("Translations Not Reviewed", "Notice Translation", [["reviewer", "is", "not set"]], color="Orange"),
    "people": card("Beneficiaries", "Data Principal", [], color="Blue"),
    # Today's "consent posture" row (prototype NGO console dashboard)
    "recorded_30": card("Recorded (30 Days)", "Consent Event", [["creation", "Timespan", "last 30 days"]], color="Blue", stats=True),
    "confirmed": card("Confirmed", "Consent State", [["status", "=", "granted"], ["verification_status", "=", "confirmed"]], color="Green"),
    "evidence_only": card("Evidence Only", "Consent State", [["status", "=", "granted"], ["verification_status", "=", "evidence_only"]], color="Purple"),
    "to_sync": card("Waiting To Sync", "Field Device", [["status", "=", "active"]], color="Orange", total_of="pending_events"),
    "withdrawn_30": card("Withdrawn (30 Days)", "Consent Event", [["action", "=", "withdraw"], ["creation", "Timespan", "last 30 days"]], color="Red"),
}


# ---------------------------------------------------------------- charts
def chart(name, doctype, kind="Bar", group_by=None, filters=(), timeseries=False, color="#3E6B3A"):
    doc = {"doctype": "Dashboard Chart", "chart_name": name, "document_type": doctype, "type": kind,
           "is_public": 1, "is_standard": 1, "color": color, "use_report_chart": 0,
           "filters_json": json.dumps([[doctype, *f, False] for f in filters]), "dynamic_filters_json": "[]"}
    if timeseries:
        doc.update(chart_type="Count", based_on="creation", timeseries=1, time_interval="Weekly",
                   timespan="Last Quarter", number_of_groups=0)
    else:
        # Same counts as a stock Group By chart, but through the stock custom source "Anumati Breakdown"
        # (anumati/charts.py) so labels read as words, in the viewer's language. Its BREAKDOWNS table
        # holds the group-by field and filters; document_type stays set so chart permissions apply.
        doc.update(chart_type="Custom", source="Anumati Breakdown", timeseries=0, filters_json="[]",
                   number_of_groups=0)
    write("dashboard_chart", name, doc)
    return name


CHARTS = {
    "per_week": chart("Consent Events Per Week", "Consent Event", "Line", timeseries=True, color="#B4532A"),
    "by_purpose": chart("Agreed By Purpose", "Consent State", group_by="purpose", filters=[["status", "=", "granted"]]),
    "by_mode": chart("How People Consented", "Consent Event", "Donut", group_by="capture_mode", filters=[["action", "=", "grant"]]),
    "by_delivery": chart("How The Notice Was Given", "Consent Event", "Donut", group_by="notice_delivery", filters=[["action", "!=", "withdraw"]]),
    "by_worker": chart("Consents By Field Worker", "Consent Event", group_by="captured_by", filters=[["action", "=", "grant"]], color="#B4532A"),
    "by_language": chart("Consents By Language", "Consent Event", group_by="language", filters=[["action", "=", "grant"]]),
    "requests_by_type": chart("Requests By Type", "Rights Request", group_by="request_type", color="#B4532A"),
    "pipeline": chart("Verification Pipeline", "Consent State", group_by="verification_status", filters=[["status", "=", "granted"]], color="#7C8FD6"),
    "withdrawals_by_channel": chart("Withdrawals By Channel", "Consent Event", group_by="channel", filters=[["action", "=", "withdraw"]], color="#B4532A"),
}


# ---------------------------------------------------------------- custom HTML block, kanban, saved filters
NEEDS_ATTENTION = "Needs Attention"
ATTENTION_SCRIPT = r"""
// Needs attention: counts only, never names. Each line shows only if the viewer can read that list
// (checked from boot, so nobody sees a permission error) and something is waiting.
const today = frappe.datetime.get_today();
const items = [
	{ dt: "Rights Request", label: __("requests are past their due date"), tone: "red",
	  filters: { status: ["not in", ["Closed", "Rejected"]], sla_due: ["<", today] } },
	{ dt: "Rights Request", label: __("requests need matching to a person"), tone: "red",
	  filters: { status: "Unmatched" } },
	{ dt: "Breach Incident", label: __("breaches are open (72-hour clock)"), tone: "red",
	  filters: { status: ["!=", "Closed"] } },
	{ dt: "Consent State", label: __("consents are waiting for confirmation"), tone: "amber",
	  filters: { status: "granted", verification_status: "unconfirmed" } },
	{ dt: "Field Device", label: __("field phones have not synced for 2 days"), tone: "amber",
	  filters: { status: "active", last_sync: ["<", moment(today).subtract(2, "days").format("YYYY-MM-DD")] } },
	{ dt: "Notice Translation", label: __("translations are waiting for review"), tone: "amber",
	  filters: { reviewer: ["is", "not set"] } },
];
const list = root_element.querySelector(".anumati-attention-list");
// Nightly hash-chain check (Anumati Settings), for the DPO and Admin.
const chain = frappe.model.can_read("Anumati Settings")
	? Promise.all([
		frappe.db.get_single_value("Anumati Settings", "last_chain_check"),
		frappe.db.get_single_value("Anumati Settings", "last_chain_status"),
	]).catch(() => [null, null])
	: Promise.resolve(null);
const readable = items.filter((i) => frappe.model.can_read(i.dt));
Promise.all(readable.map((i) => frappe.db.count(i.dt, { filters: i.filters }).catch(() => 0))).then((counts) => {
	list.innerHTML = "";
	readable.forEach((item, n) => {
		if (!counts[n]) return;
		const row = document.createElement("a");
		row.className = "anumati-attention-row " + item.tone;
		row.href = "#";
		row.innerHTML = `<b>${counts[n]}</b> <span></span>`;
		row.querySelector("span").textContent = item.label;
		row.addEventListener("click", (e) => {
			e.preventDefault();
			frappe.route_options = item.filters;
			frappe.set_route("List", item.dt);
		});
		list.appendChild(row);
	});
	if (!list.children.length) list.innerHTML = `<div class="anumati-attention-none">${__("Nothing needs attention right now.")}</div>`;
	chain.then((c) => {
		if (!c) return;
		const [when, status] = c;
		const row = document.createElement("div");
		const failed = (status || "").includes("FAILED");
		row.className = "anumati-attention-row " + (failed ? "red" : when ? "green" : "amber");
		row.textContent = failed ? __("Hash chain check FAILED. Tell the DPO now.")
			: when ? __("Hash chain verified {0}", [frappe.datetime.prettyDate(when)])
			: __("Hash chain not checked yet (runs every night)");
		list.appendChild(row);
	});
});
"""
ATTENTION_HTML = """<div class="anumati-attention">
<div class="anumati-attention-title">Needs attention</div>
<div class="anumati-attention-list"><div class="anumati-attention-none">…</div></div>
</div>"""
ATTENTION_CSS = """.anumati-attention { padding: 4px 2px; }
.anumati-attention-title { font-weight: 600; font-size: var(--text-lg); margin-bottom: 8px; }
.anumati-attention-list { display: flex; flex-direction: column; gap: 6px; }
.anumati-attention-row { display: flex; gap: 8px; align-items: baseline; padding: 8px 12px; border-radius: 8px;
  text-decoration: none; color: var(--text-color); border-left: 4px solid var(--gray-400); background: var(--subtle-fg); }
.anumati-attention-row:hover { text-decoration: none; background: var(--control-bg); }
.anumati-attention-row.red { border-left-color: var(--red-500); }
.anumati-attention-row.amber { border-left-color: var(--yellow-500); }
.anumati-attention-row.green { border-left-color: var(--green-500); }
.anumati-attention-none { color: var(--text-muted); padding: 8px 0; }"""

PROGRAMMES_BLOCK = "Programmes At A Glance"
PROGRAMMES_HTML = """<div class="anumati-prog">
<div class="anumati-prog-title">Programmes</div>
<table><thead><tr><th>Programme</th><th>Live notice</th><th>Languages</th><th class="num">Recorded</th><th class="num">Confirmed</th><th>Status</th></tr></thead>
<tbody><tr><td colspan="6" class="muted">…</td></tr></tbody></table>
</div>"""
PROGRAMMES_SCRIPT = r"""
// One row per programme: live notice (and any draft), notice languages, consents recorded, share of
// current consents confirmed, status. Counts only. Shown to anyone who can read programmes and consents.
const body = root_element.querySelector("tbody");
const esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));
if (!frappe.model.can_read("Programme") || !frappe.model.can_read("Consent Event")) {
	root_element.querySelector(".anumati-prog").style.display = "none";
} else {
	frappe.db.get_list("Programme", { fields: ["name", "programme_name", "status"], order_by: "modified desc", limit: 20 }).then(async (progs) => {
		const readable = frappe.model.can_read("Consent State");
		const rows = await Promise.all(progs.map(async (p) => {
			const [notices, recorded, confirmed, granted] = await Promise.all([
				frappe.db.get_list("Notice Template", { filters: { programme: p.name, status: ["in", ["Published", "Draft"]] }, fields: ["name", "version", "status"], limit: 5 }),
				frappe.db.count("Consent Event", { filters: { programme: p.name } }),
				readable ? frappe.db.count("Consent State", { filters: { programme: p.name, status: "granted", verification_status: "confirmed" } }) : 0,
				readable ? frappe.db.count("Consent State", { filters: { programme: p.name, status: "granted" } }) : 0,
			]);
			const live = notices.find((n) => n.status === "Published");
			const draft = notices.find((n) => n.status === "Draft");
			let langs = [];
			if (live && frappe.model.can_read("Notice Translation")) {
				const tr = await frappe.db.get_list("Notice Translation", { filters: { notice: live.name }, fields: ["language"], limit: 20 });
				langs = ["English"].concat(tr.map((t) => t.language === "hi" ? "हिन्दी" : t.language === "mr" ? "मराठी" : t.language));
			}
			return { p, live, draft, langs, recorded, pct: granted ? Math.round((100 * confirmed) / granted) + "%" : "—" };
		}));
		body.innerHTML = rows.length ? rows.map(({ p, live, draft, langs, recorded, pct }) => `
			<tr data-name="${esc(p.name)}">
				<td><b>${esc(p.programme_name || p.name)}</b></td>
				<td>${live ? "v" + esc(live.version) : `<span class="muted">${__("None")}</span>`}${draft ? ` <span class="pill amber">v${esc(draft.version)} ${__("draft")}</span>` : ""}</td>
				<td>${esc(langs.join(", ")) || '<span class="muted">—</span>'}</td>
				<td class="num">${recorded.toLocaleString("en-IN")}</td>
				<td class="num">${pct}</td>
				<td><span class="pill ${p.status === "Live" ? "green" : "grey"}">${esc(__(p.status))}</span></td>
			</tr>`).join("") : `<tr><td colspan="6" class="muted">${__("No programmes yet.")}</td></tr>`;
		body.querySelectorAll("tr[data-name]").forEach((tr) => tr.addEventListener("click", () => frappe.set_route("Form", "Programme", tr.dataset.name)));
	});
}
"""
PROGRAMMES_CSS = """.anumati-prog-title { font-weight: 600; font-size: var(--text-lg); margin-bottom: 8px; }
.anumati-prog table { width: 100%; border-collapse: collapse; font-size: var(--text-md); }
.anumati-prog th { text-align: left; font-weight: 500; color: var(--text-muted); padding: 8px 10px; border-bottom: 1px solid var(--border-color); }
.anumati-prog td { padding: 10px; border-bottom: 1px solid var(--border-color); }
.anumati-prog tr[data-name] { cursor: pointer; }
.anumati-prog tr[data-name]:hover td { background: var(--subtle-fg); }
.anumati-prog .num { text-align: right; }
.anumati-prog .muted { color: var(--text-muted); }
.anumati-prog .pill { padding: 2px 10px; border-radius: 999px; font-size: var(--text-sm); font-weight: 500; }
.anumati-prog .pill.green { background: var(--green-100); color: var(--green-700); }
.anumati-prog .pill.amber { background: var(--yellow-100); color: var(--yellow-700); }
.anumati-prog .pill.grey { background: var(--gray-100); color: var(--gray-700); }"""

REQUESTS_BOARD = "Requests"
KANBAN_COLUMNS = [("Open", "Blue"), ("Unmatched", "Red"), ("In Progress", "Orange"),
                  ("Awaiting Acknowledgement", "Purple"), ("Closed", "Green"), ("Rejected", "Gray")]

LIST_FILTERS = [
    ("Consent Event", "Consents this week", [["Consent Event", "creation", "Timespan", "this week", False]]),
    ("Consent Event", "Withdrawals", [["Consent Event", "action", "=", "withdraw", False]]),
    ("Consent Event", "Refused all", [["Consent Event", "action", "=", "refuse", False]]),
    ("Consent Event", "Guardian consents", [["Consent Event", "capture_mode", "in", ["guardian_minor", "guardian_pwd"], False]]),
    ("Consent Event", "Notice not heard in full", [["Consent Event", "notice_completed", "=", 0, False]]),
    ("Consent State", "Waiting for confirmation", [["Consent State", "verification_status", "=", "unconfirmed", False]]),
    ("Data Principal", "Minors", [["Data Principal", "is_minor", "=", 1, False]]),
    ("Data Principal", "Shared phone", [["Data Principal", "shared_phone", "=", 1, False]]),
    ("Data Principal", "Needs help to read", [["Data Principal", "needs_assistance", "=", 1, False]]),
    ("Rights Request", "Unmatched", [["Rights Request", "status", "=", "Unmatched", False]]),
    ("Rights Request", "Open withdrawals", [["Rights Request", "request_type", "=", "withdrawal", False],
                                           ["Rights Request", "status", "not in", ["Closed", "Rejected"], False]]),
    ("Field Device", "Lost or wiped", [["Field Device", "status", "in", ["lost", "wipe_queued", "wiped"], False]]),
]

# The stock Access Log and View Log (who opened a name or evidence) are System Manager only. The DPO
# needs to read them; the stock way is Role Permissions (Custom DocPerm). The System Manager row
# repeats Frappe's own, because a custom permission set replaces the standard one.
LOG_PERMS = [
    ("Access Log", SM, dict(read=1, report=1, export=1, print=1, email=1, share=1, delete=1)),
    ("Access Log", DPO, dict(read=1, report=1, export=1)),
    ("View Log", SM, dict(read=1, report=1, export=1, print=1, email=1, share=1)),
    ("View Log", DPO, dict(read=1, report=1, export=1)),
]


# ---------------------------------------------------------------- onboarding
ONBOARDING = "Anumati"
STEPS = [
    ("Organisation and DPO", "Update Settings", "Anumati Settings",
     "Legal name, the DPO's contact and default languages. These print on every notice."),
    ("First programme", "Create Entry", "Programme",
     "A programme is one activity, like a health camp. Say which ways of giving consent it allows."),
    ("Purposes and records of processing", "Create Entry", "ROPA Entry",
     "One record per purpose. The DPO approves each one; a notice cannot publish without them."),
    ("Publish the notice in English and Hindi", "Create Entry", "Notice Template",
     "The Rule 3 checklist says what is missing. A named person reviews each translation."),
    ("Add field workers", "Create Entry", "User",
     "Give each worker the Anumati Field Worker and Mobile User roles, then switch on Mobile Configuration."),
    ("Connect SMS (optional for the pilot)", "Create Entry", "Channel Provider",
     "Receipts, STOP and missed calls. Keys go in the form's password fields, never in chat or email."),
]


def onboarding():
    names = []
    for title, action, ref, desc in STEPS:
        write("onboarding_step", title, {
            "doctype": "Onboarding Step", "title": title, "action": action, "action_label": "Open",
            "reference_document": ref, "is_single": 1 if action == "Update Settings" else 0,
            "description": desc, "is_complete": 0, "is_skipped": 0, "show_full_form": 1,
            "show_form_tour": 0, "validate_action": 0,
        })
        names.append(title)
    write("module_onboarding", ONBOARDING, {
        "doctype": "Module Onboarding", "title": "Set up Anumati",
        "subtitle": "Six steps, about 20 minutes. Each opens the right form.",
        "success_message": "Anumati is set up. Field workers can sign in to the app.",
        "documentation_url": "https://github.com/sunandan89/anumati/blob/main/docs/setup-guide.md",
        "is_complete": 0, "allow_roles": [{"role": ADM}, {"role": SM}],
        "steps": [{"step": s} for s in names],
    })


# ---------------------------------------------------------------- workspaces
class WS:
    def __init__(self, name, seq, icon, roles):
        self.name, self.seq, self.icon, self.roles = name, seq, icon, roles
        self.blocks, self.links, self.shortcuts, self.cards, self.charts, self.custom = [], [], [], [], [], []

    def _block(self, kind, data):
        self.blocks.append({"id": f"{scrub(self.name)[:6]}{len(self.blocks)}", "type": kind, "data": data})

    def header(self, text):
        self._block("header", {"text": f'<span class="h4"><b>{text}</b></span>', "col": 12})
        return self

    def spacer(self):
        self._block("spacer", {"col": 12})
        return self

    def onboarding(self):
        self._block("onboarding", {"onboarding_name": ONBOARDING, "col": 12})
        return self

    def attention(self, col=12):
        return self.block(NEEDS_ATTENTION, col)

    def block(self, name, col=12):
        self._block("custom_block", {"custom_block_name": name, "col": col})
        self.custom.append({"custom_block_name": name, "label": name})
        return self

    def numbers(self, *labels, col=3):
        for label in labels:
            self._block("number_card", {"number_card_name": label, "col": col})
            self.cards.append({"label": label, "number_card_name": label})
        return self

    def chart(self, name, col=12):
        self._block("chart", {"chart_name": name, "col": col})
        self.charts.append({"chart_name": name, "label": name})
        return self

    def shortcut(self, label, link_to=None, url=None, color="Grey", stats=None, fmt=None, view="List"):
        s = {"label": label, "color": color, "stats_filter": json.dumps(stats or [])}
        if url:
            s.update(type="URL", url=url)
        else:
            s.update(type="DocType", link_to=link_to, doc_view=view)
        if fmt:
            s["format"] = fmt
        self._block("shortcut", {"shortcut_name": label, "col": 3})
        self.shortcuts.append(s)
        return self

    def card(self, label, *doctypes, col=4):
        self._block("card", {"card_name": label, "col": col})
        self.links.append({"type": "Card Break", "label": label, "link_count": len(doctypes),
                           "hidden": 0, "is_query_report": 0, "onboard": 0})
        for d in doctypes:
            dt, label_ = d if isinstance(d, tuple) else (d, d)
            # "Report:<name>" links a report instead of a DocType list.
            report = dt.startswith("Report:")
            self.links.append({"type": "Link", "label": label_, "link_to": dt.removeprefix("Report:"),
                               "link_type": "Report" if report else "DocType", "link_count": 0, "hidden": 0,
                               "is_query_report": 1 if report else 0, "onboard": 0})
        return self

    def emit(self):
        write("workspace", self.name, {
            "doctype": "Workspace", "label": self.name, "title": self.name, "icon": self.icon,
            "public": 1, "is_hidden": 0, "hide_custom": 1, "for_user": "", "parent_page": "",
            "sequence_id": float(self.seq), "content": json.dumps(self.blocks),
            "links": self.links, "shortcuts": self.shortcuts, "number_cards": self.cards,
            "charts": self.charts, "custom_blocks": self.custom, "quick_lists": [],
            "roles": [{"role": r} for r in self.roles],
        })


DESK = [OPR, PM, DPO, ADM, SM]
WORKSPACES = {
    # section: who sees it in the sidebar (DocType permissions still decide what they can open or change)
    "Today": DESK,
    "Beneficiaries": DESK,
    "Programmes": [PM, DPO, ADM, SM],
    "Analytics": [PM, DPO, ADM, SM],
    "Notices and Compliance": [PM, DPO, ADM, SM],
    "Setup": [ADM, SM],
}
BOARD_URL = "/app/rights-request/view/kanban/" + REQUESTS_BOARD


def workspaces():
    r = WORKSPACES
    (WS("Today", 1, "home", r["Today"])
        .onboarding()
        .numbers(CARDS["recorded_30"], CARDS["confirmed"], CARDS["evidence_only"], col=4)
        .numbers(CARDS["to_sync"], CARDS["withdrawn_30"], CARDS["open_requests"], col=4)
        .chart(CHARTS["pipeline"], 4).chart(CHARTS["withdrawals_by_channel"], 4).attention(4)
        .block(PROGRAMMES_BLOCK)
        .shortcut("Requests board", url=BOARD_URL, color="Orange")
        .shortcut("Inbox", "Rights Request", color="Orange", stats=[["Rights Request", "status", "not in", ["Closed", "Rejected"]]], fmt="{} open")
        .shortcut("Find a receipt", "Consent Event", color="Green")
        .shortcut("Beneficiaries", "Data Principal", color="Blue")
        .chart(CHARTS["per_week"])
        .card("Requests", "Rights Request", "Purge Request", "Propagation Ack")
        .emit())
    (WS("Beneficiaries", 2, "users", r["Beneficiaries"])
        .numbers(CARDS["people"], CARDS["consents_week"], CARDS["unconfirmed"], CARDS["withdrawals_week"])
        .shortcut("Beneficiaries", "Data Principal", color="Blue")
        .shortcut("Consents", "Consent Event", color="Green")
        .shortcut("Waiting for confirmation", "Consent State", color="Orange",
                  stats=[["Consent State", "verification_status", "=", "unconfirmed"]], fmt="{} waiting")
        .shortcut("Guardians", "Guardian Link", color="Purple")
        .shortcut("Turned 18: renew consent", "Data Principal", color="Orange",
                  stats=[["Data Principal", "renewal_due", "=", 1]], fmt="{} to renew")
        .card("People", ("Data Principal", "Beneficiary"), ("Guardian Link", "Guardian"),
              ("Report:Profile Answer Totals", "About the people (totals)"))
        .card("Consent records", ("Consent Event", "Consent"), ("Consent State", "Current consent per purpose"),
              ("Verification Attempt", "Confirmation attempt"))
        .emit())
    (WS("Programmes", 3, "folder-normal", r["Programmes"])
        .numbers(CARDS["consents_week"], CARDS["not_synced"])
        .shortcut("Programmes", "Programme", color="Green")
        .shortcut("Re-consent", "Campaign", color="Orange")
        .shortcut("Field phones", "Field Device", color="Blue")
        .shortcut("Extra questions", "Profile Question", color="Purple")
        .card("Programmes", "Programme", ("Campaign", "Re-consent campaign"),
              ("Profile Question", "Extra questions library"), ("Report:Profile Answer Totals", "Extra questions: totals"))
        .card("Field team", ("Field Device", "Field phone"))
        .emit())
    (WS("Analytics", 4, "dashboard", r["Analytics"])
        .numbers(CARDS["consents_month"], CARDS["withdrawals_month"], CARDS["refused_month"], CARDS["heard"])
        .chart(CHARTS["per_week"])
        .chart(CHARTS["by_purpose"], 6).chart(CHARTS["by_mode"], 6)
        .chart(CHARTS["by_delivery"], 6).chart(CHARTS["by_language"], 6)
        .chart(CHARTS["by_worker"], 6).chart(CHARTS["requests_by_type"], 6)
        .emit())
    (WS("Notices and Compliance", 5, "lock", r["Notices and Compliance"])
        .numbers(CARDS["breaches"], CARDS["unreviewed"], CARDS["overdue"])
        .shortcut("Notices", "Notice Template", color="Green")
        .shortcut("Breaches", "Breach Incident", color="Red", stats=[["Breach Incident", "status", "!=", "Closed"]], fmt="{} open")
        .shortcut("Records of processing", "ROPA Entry", color="Blue")
        .shortcut("Audit log", "Audit Entry", color="Grey")
        .card("Notices", ("Notice Template", "Notice"), ("Notice Translation", "Translation"), "Purpose",
              "Message Template")
        .card("Records and risk", ("ROPA Entry", "Records of processing and DPIA"), "Data Category",
              "Retention Policy", "Processor", "Purge Request")
        .card("Incidents and audit", ("Breach Incident", "Breach"), ("Audit Entry", "Audit log"),
              ("Access Log", "Access log (names and evidence)"), ("View Log", "Record views"), "Audit Share")
        .emit())
    (WS("Setup", 6, "setting-gear", r["Setup"])
        .onboarding()
        .card("Organisation", "Anumati Settings", ("User", "Team"), "Role")
        .card("Messaging", ("Channel Provider", "SMS and messaging"), "Message Template")
        .card("Connected systems", "Source System", ("Mobile Configuration", "Field app"), "Funder Link")
        .emit())


def fixtures():
    fixture("custom_html_block", [{
        "doctype": "Custom HTML Block", "name": NEEDS_ATTENTION, "private": 0,
        "html": ATTENTION_HTML, "script": ATTENTION_SCRIPT.strip() + "\n", "style": ATTENTION_CSS, "roles": [],
    }, {
        "doctype": "Custom HTML Block", "name": PROGRAMMES_BLOCK, "private": 0,
        "html": PROGRAMMES_HTML, "script": PROGRAMMES_SCRIPT.strip() + "\n", "style": PROGRAMMES_CSS, "roles": [],
    }])
    fixture("kanban_board", [{
        "doctype": "Kanban Board", "name": REQUESTS_BOARD, "kanban_board_name": REQUESTS_BOARD,
        "reference_doctype": "Rights Request", "field_name": "status", "private": 0, "show_labels": 1,
        "filters": "[]", "fields": json.dumps(["request_type", "channel", "sla_due", "assigned_to"]),
        "columns": [{"doctype": "Kanban Board Column", "column_name": c, "status": "Active", "indicator": i, "order": "[]"}
                    for c, i in KANBAN_COLUMNS],
    }])
    fixture("list_filter", [{
        "doctype": "List Filter", "name": f"anumati-{scrub(dt)}-{scrub(label)}", "filter_name": label,
        "reference_doctype": dt, "for_user": "", "filters": json.dumps(f),
    } for dt, label, f in LIST_FILTERS])
    fixture("custom_docperm", [{
        "doctype": "Custom DocPerm", "name": f"anumati-{scrub(parent)}-{scrub(role)}", "parent": parent,
        "role": role, "permlevel": 0,
        **{k: p.get(k, 0) for k in ("read", "write", "create", "delete", "submit", "cancel", "amend",
                                    "report", "export", "import", "print", "email", "share", "if_owner",
                                    "set_user_permissions", "select")},
    } for parent, role, p in LOG_PERMS])


if __name__ == "__main__":
    onboarding()
    workspaces()
    fixtures()
    with open(os.path.join(REPO, "anumati", "tests", "workspace_roles.json"), "w") as fh:
        json.dump(WORKSPACES, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("workspaces", len(WORKSPACES), "cards", len(CARDS), "charts", len(CHARTS))
