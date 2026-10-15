// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE
//
// /my-consent: the self-service page. Plain JavaScript on Frappe's website styles; every call goes to
// anumati.selfservice (signed in by an HttpOnly cookie, so this script never sees a token). All text comes
// translated from the server (window.anumati_ss.t); anything from the server is inserted as text, never HTML.

(function () {
	const C = window.anumati_ss || { t: {} };
	const T = (k, ...a) => (C.t[k] || k).replace(/\{(\d)\}/g, (_, n) => a[n] ?? "");
	const root = document.getElementById("anumati-ss");
	if (!root) return;
	const S = { phone: "", home: null, i: 0, person: null, tab: "choices", pending: {}, notice: "" };

	// ---------------------------------------------------------------- server
	async function call(method, args = {}, httpMethod = "POST") {
		const body = new URLSearchParams();
		Object.entries(args).forEach(([k, v]) => body.append(k, typeof v === "object" ? JSON.stringify(v) : v));
		const headers = { Accept: "application/json", "X-Frappe-CSRF-Token": window.csrf_token || (window.frappe && frappe.csrf_token) || "" };
		const res = await fetch(`/api/method/anumati.selfservice.${method}`, {
			method: httpMethod, credentials: "same-origin", headers, body,
		});
		let data = {};
		try { data = await res.json(); } catch (e) { /* not JSON */ }
		if (res.status === 401) { S.home = null; render_sign_in(); throw new Error(T("see_or_change")); }
		if (!res.ok) throw new Error(server_message(data) || T("error"));
		return data.message;
	}
	function server_message(data) {
		try {
			const msgs = JSON.parse(data._server_messages || "[]").map((m) => JSON.parse(m).message);
			return msgs.length ? strip(msgs.join(" ")) : "";
		} catch (e) { return ""; }
	}
	const strip = (html) => { const d = document.createElement("div"); d.innerHTML = html; return d.textContent; };

	// ---------------------------------------------------------------- tiny DOM helpers
	function h(tag, attrs = {}, ...kids) {
		const el = document.createElement(tag);
		Object.entries(attrs || {}).forEach(([k, v]) => {
			if (v === false || v == null) return;
			if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
			else if (k === "class") el.className = v;
			else el.setAttribute(k, v === true ? "" : v);
		});
		kids.flat().forEach((k) => k != null && k !== false && el.append(k instanceof Node ? k : document.createTextNode(String(k))));
		return el;
	}
	const show = (...nodes) => { root.replaceChildren(...nodes); window.scrollTo(0, 0); };
	const alertBox = (text, tone = "info") => text ? h("div", { class: `ss-alert ss-${tone}`, role: tone === "error" ? "alert" : "status" }, text) : null;
	const field = (label, input, help) => h("div", { class: "form-group" }, h("label", {}, label), input, help ? h("small", { class: "form-text text-muted" }, help) : null);
	const button = (text, onclick, cls = "btn-primary") => h("button", { type: "button", class: `btn ${cls} btn-block`, onclick }, text);
	const link = (text, onclick) => h("button", { type: "button", class: "btn btn-link ss-link", onclick }, text);
	const date = (s) => (s ? new Date(s.replace(" ", "T")).toLocaleDateString(document.documentElement.lang || undefined, { day: "numeric", month: "short", year: "numeric" }) : "");
	function busy(btn, fn) {
		return async (...a) => {
			if (btn) btn.disabled = true;
			try { await fn(...a); } catch (e) { flash(e.message, "error"); } finally { if (btn) btn.disabled = false; }
		};
	}
	function flash(text, tone = "info") {
		const old = root.querySelector(".ss-flash");
		if (old) old.remove();
		const box = alertBox(text, tone);
		box.classList.add("ss-flash");
		root.prepend(box);
		window.scrollTo(0, 0);
	}
	function footer() {
		return h("div", { class: "ss-footer" }, T("help"), C.helpline ? ` ${C.helpline}` : "",
			C.dpo_email ? h("div", {}, T("dpo", C.dpo_email)) : null);
	}

	// ---------------------------------------------------------------- sign in
	function render_sign_in(note) {
		const phone = h("input", { class: "form-control", type: "tel", inputmode: "numeric", autocomplete: "tel", maxlength: 14, placeholder: T("mobile_ph"), value: S.phone });
		const go = button(T("send_code"));
		go.onclick = busy(go, async () => {
			S.phone = phone.value;
			const r = await call("start", { phone: phone.value });
			if (!r.sent) return flash(T("not_set_up"), "warn");
			render_code(r.to);
		});
		show(alertBox(note, "info"), h("h3", {}, T("see_or_change")), h("p", { class: "text-muted" }, T("intro")),
			field(T("mobile"), phone, T("mobile_help")), go,
			h("div", { class: "text-center" }, link(T("no_phone"), () => render_receipt_sign_in())),
			h("p", { class: "small text-muted ss-gap" }, T("privacy")), footer());
		phone.focus();
	}
	function render_code(to) {
		const code = h("input", { class: "form-control ss-otp", type: "text", inputmode: "numeric", autocomplete: "one-time-code", maxlength: 6 });
		const go = button(T("continue"));
		go.onclick = busy(go, async () => {
			const r = await call("verify", { phone: S.phone, code: code.value });
			if (!r.signed_in) return flash(T("tries_left", r.tries_left), "error");
			after_sign_in(r);
		});
		show(h("h3", {}, T("enter_code")), h("p", { class: "text-muted" }, T("code_sent", to)),
			field(T("enter_code"), code), go, h("div", { class: "text-center" }, link(T("change_number"), () => render_sign_in())), footer());
		code.focus();
	}
	function render_receipt_sign_in() {
		const code = h("input", { class: "form-control", type: "text", autocapitalize: "characters", placeholder: "AN-7K2Q9C", maxlength: 12 });
		const year = h("input", { class: "form-control", type: "number", inputmode: "numeric", min: 1900, max: 2100 });
		const go = button(T("continue"));
		go.onclick = busy(go, async () => after_sign_in(await call("code_login", { code: code.value, year: year.value })));
		show(h("h3", {}, T("use_receipt")), h("p", { class: "text-muted" }, T("receipt_help")),
			field(T("receipt_code"), code), field(T("birth_year"), year), go,
			h("div", { class: "text-center" }, link(T("back"), () => render_sign_in())), footer());
		code.focus();
	}
	function after_sign_in(home) {
		S.home = home;
		if (home.choose) return render_choose(home.choose);
		if (!home.people || !home.people.length) return show(alertBox(T("nobody"), "warn"), sign_out_link(), footer());
		if (home.people.length === 1) return open_person(0);
		render_people();
	}
	function render_choose(list) {
		show(h("h3", {}, T("who_are_you")), h("p", { class: "text-muted" }, T("who_are_you_help")),
			...list.map((p) => {
				const year = h("input", { class: "form-control", type: "number", inputmode: "numeric", placeholder: T("birth_year") });
				const go = h("button", { type: "button", class: "btn btn-primary" }, T("continue"));
				go.onclick = busy(go, async () => after_sign_in(await call("choose", { i: p.i, year: year.value })));
				return h("div", { class: "ss-card" }, h("b", {}, p.name), h("div", { class: "ss-row" }, year, go));
			}), sign_out_link(), footer());
	}
	function render_people() {
		const rel = { self: T("rel_self"), child: T("rel_child"), guarded: T("rel_guarded") };
		show(h("h3", {}, T("who_for")),
			...S.home.people.map((p) => h("button", { type: "button", class: "ss-card ss-who", onclick: () => open_person(p.i) },
				h("span", { class: "ss-avatar" }, (p.name || "?")[0]), h("span", {}, h("b", {}, p.name), h("small", { class: "d-block text-muted" }, rel[p.relation])), h("span", { class: "ss-chev" }, "›"))),
			sign_out_link(), footer());
	}
	function sign_out_link() {
		return h("div", { class: "text-center" }, link(T("sign_out"), async () => {
			await call("sign_out");
			S.home = null; S.person = null; S.phone = "";
			render_sign_in(T("signed_out"));
		}));
	}

	// ---------------------------------------------------------------- one person
	async function open_person(i, tab) {
		S.i = i; S.tab = tab || S.tab || "choices"; S.pending = {};
		S.person = await call("overview", { i });
		render_person();
	}
	function render_person(note) {
		const p = S.person;
		const tabs = [["choices", T("tab_choices")], ["history", T("tab_history")], ["requests", T("tab_requests")]];
		const body = { choices: choices_tab, history: history_tab, requests: requests_tab }[S.tab]();
		show(
			alertBox(note, "ok"),
			h("div", { class: "ss-head" }, h("b", {}, p.name),
				S.home.people.length > 1 ? h("button", { type: "button", class: "btn btn-sm btn-default", onclick: render_people }, T("switch_person")) : null,
				h("button", { type: "button", class: "btn btn-sm btn-default", onclick: async () => { await call("sign_out"); render_sign_in(T("signed_out")); } }, T("sign_out"))),
			h("div", { class: "ss-tabs", role: "tablist" }, tabs.map(([k, label]) => h("button", {
				type: "button", role: "tab", "aria-selected": String(S.tab === k), class: S.tab === k ? "on" : "",
				onclick: () => { S.tab = k; render_person(); },
			}, label))),
			p.mode === "code" ? alertBox(T("code_mode_note"), "warn") : null,
			body, footer());
	}

	// My choices: one card per programme; essential uses are never a toggle.
	function choices_tab() {
		if (!S.person.programmes.length) return h("p", { class: "text-muted" }, T("no_history"));
		return h("div", {}, S.person.programmes.map((prog) => {
			const rows = prog.uses.map((u) => {
				if (u.essential) {
					return h("div", { class: "ss-use" }, h("div", { class: "ss-use-t" }, h("b", {}, u.title), h("small", {}, T("needed"))),
						h("span", { class: "ss-chip" }, T("required")));
				}
				const on = u.status === "granted";
				const key = `${prog.programme}|${u.code}`;
				const checked = key in S.pending ? S.pending[key] : on;
				const canTick = on || prog.can_turn_on;
				const box = h("input", { type: "checkbox", class: "ss-check", checked, disabled: !canTick || prog.left, "aria-label": u.title,
					onchange: (e) => { if (e.target.checked === on) delete S.pending[key]; else S.pending[key] = e.target.checked; } });
				const state = on ? T("on") : u.status === "not_asked" ? T("not_asked") : T("off");
				return h("label", { class: "ss-use" }, h("div", { class: "ss-use-t" }, h("b", {}, u.title),
					h("small", {}, state), u.description ? h("small", { class: "ss-desc" }, u.description) : null), box);
			});
			const save = button(T("save_changes"));
			save.onclick = () => confirm_save(prog);
			return h("div", { class: "ss-card" },
				h("b", { class: "ss-prog" }, prog.name), prog.code ? h("small", { class: "d-block text-muted" }, T("agreed_on", prog.code)) : null,
				prog.left ? alertBox(T("left_note"), "warn") : null,
				!prog.left && !prog.can_turn_on && prog.why_not && S.person.mode !== "code" ? h("small", { class: "d-block text-muted" }, prog.why_not) : null,
				rows, prog.left ? null : [save, h("div", { class: "text-center" }, h("button", { type: "button", class: "btn btn-link ss-danger-link", onclick: () => render_leave(prog) }, T("leave_programme")))]);
		}));
	}
	function confirm_save(prog) {
		const changes = Object.entries(S.pending).filter(([k]) => k.startsWith(prog.programme + "|"));
		if (!changes.length) return flash(T("nothing_changed"));
		const title = (code) => prog.uses.find((u) => u.code === code).title;
		const on = changes.filter(([, v]) => v).map(([k]) => k.split("|")[1]);
		const off = changes.filter(([, v]) => !v).map(([k]) => k.split("|")[1]);
		const yes = h("button", { type: "button", class: "btn btn-primary" }, T("yes_save"));
		const modal = h("div", { class: "ss-modal", role: "dialog", "aria-modal": "true" }, h("div", { class: "ss-dialog" },
			h("h4", {}, T("confirm_title")),
			off.length ? h("p", {}, h("b", {}, T("will_stop") + ": "), off.map(title).join(", ")) : null,
			on.length ? h("p", {}, h("b", {}, T("will_start") + ": "), on.map(title).join(", ")) : null,
			h("p", { class: "small text-muted" }, T("confirm_note")),
			h("div", { class: "ss-row ss-end" }, h("button", { type: "button", class: "btn btn-default", onclick: () => modal.remove() }, T("cancel")), yes)));
		yes.onclick = busy(yes, async () => {
			const r = await call("save_choices", { i: S.i, programme: prog.programme, turn_on: on, turn_off: off });
			modal.remove();
			S.pending = {}; S.person = r;
			render_person(T("saved", r.codes.join(", ")));
		});
		document.body.append(modal);
		yes.focus();
	}
	function render_leave(prog) {
		const tick = h("input", { type: "checkbox", class: "ss-check" });
		const go = button(T("leave_button"), null, "btn-danger");
		go.onclick = busy(go, async () => {
			const r = await call("leave", { i: S.i, programme: prog.programme, confirm: tick.checked ? 1 : 0 });
			S.person = r;
			render_person(T("left_done", r.code));
		});
		show(h("h3", {}, T("leave_title", prog.name)), h("p", { class: "text-muted" }, S.person.name),
			alertBox(T("leave_warn"), "error"),
			h("ul", { class: "small" }, prog.uses.filter((u) => u.status === "granted").map((u) => h("li", {}, u.title))),
			h("p", { class: "small text-muted" }, T("leave_keep")),
			h("label", { class: "ss-use" }, tick, h("b", {}, T("leave_understand"))), go,
			h("div", { class: "text-center" }, link(T("go_back"), () => render_person())), footer());
	}

	// History: every agreement and change, newest first, each with its receipt.
	function history_tab() {
		const items = S.person.history;
		if (!items.length) return h("p", { class: "text-muted" }, T("no_history"));
		return h("div", { class: "ss-timeline" }, items.map((e) => {
			const lines = [];
			if (e.agreed.length) lines.push(`${T("agreed")}: ${e.agreed.join(", ")}`);
			if (e.said_no.length) lines.push(`${T("said_no")}: ${e.said_no.join(", ")}`);
			if (e.stopped.length) lines.push(`${T("stopped")}: ${e.stopped.join(", ")}`);
			const url = `/api/method/anumati.selfservice.receipt?i=${encodeURIComponent(S.i)}&event=${encodeURIComponent(e.id)}`;
			return h("div", { class: `ss-event ss-${e.action}` },
				h("b", {}, e.programme), lines.map((l) => h("div", {}, l)),
				h("small", { class: "text-muted d-block" }, `${date(e.at)} · ${e.how} · ${e.code}`),
				h("a", { href: url, class: "small", target: "_blank", rel: "noopener" }, "⤓ " + T("download")));
		}));
	}

	// Requests: two doors (a rights / support request, or a grievance), and the conversation on each one.
	function requests_tab() {
		const door = (icon, cls, title, help, onclick) => h("button", { type: "button", class: "ss-card ss-who", onclick },
			h("span", { class: `ss-avatar ${cls}` }, icon), h("span", {}, h("b", {}, title), h("small", { class: "d-block text-muted" }, help)), h("span", { class: "ss-chev" }, "›"));
		const list = S.person.requests;
		return h("div", {},
			door("⇄", "ss-blue", T("rights_request"), T("rights_request_help"), render_ask),
			door("!", "ss-red", T("grievance"), T("grievance_help"), render_complain),
			h("div", { class: "ss-label" }, T("raised_by_you")),
			list.length ? list.map(request_card) : h("p", { class: "text-muted" }, T("no_requests")));
	}
	function request_card(r) {
		const text = h("textarea", { class: "form-control", rows: 2, placeholder: T("add_more"), maxlength: 2000 });
		const send = h("button", { type: "button", class: "btn btn-default btn-sm" }, T("send"));
		send.onclick = busy(send, async () => {
			S.person = await call("write", { i: S.i, request: r.id, text: text.value });
			render_person();
		});
		const tone = { request_answered: "ok", request_closed: "ok", cannot_do: "", waiting_for_person: "warn" }[r.status] ?? "info";
		const grievance = r.kind === "grievance";
		const title = grievance ? T("grievance") : T("type_" + r.type);
		const answer = (m, k) => grievance && r.outcome && m.from === "office" && k === r.messages.map((x) => x.from).lastIndexOf("office") && r.status !== "working_on_it";
		const respond = (solved) => async () => {
			S.person = await call("respond", { i: S.i, grievance_name: r.id, solved: solved ? 1 : 0 });
			render_person(solved ? T("thanks_closed") : T("sent_to_dpo"));
		};
		return h("div", { class: "ss-card" },
			h("div", { class: "ss-row" }, h("b", {}, title), h("span", { class: `ss-chip ss-${tone}` }, T("st_" + r.status))),
			h("small", { class: "text-muted d-block" }, [grievance ? T("cat_" + r.type) : null, r.id, T("reply_by", date(r.reply_by))].filter(Boolean).join(" · ")),
			grievance && r.with_dpo && !["request_answered", "request_closed"].includes(r.status) ? h("small", { class: "d-block ss-dpo" }, T("with_dpo")) : null,
			r.messages.map((m, k) => h("div", { class: `ss-msg ss-${m.from}` },
				h("small", { class: "text-muted d-block" }, `${m.from === "you" ? T("you") : T("office")} · ${date(m.at)}`),
				answer(m, k) ? h("b", { class: "d-block" }, r.outcome) : null, m.text)),
			r.can_respond ? h("div", { class: "ss-gap" }, h("b", { class: "d-block" }, T("did_it_solve")),
				button(T("yes_solved"), respond(true)),
				r.can_say_not_happy ? button(T("not_happy"), respond(false), "btn-default") : null) : null,
			grievance && r.board_route ? alertBox(T("board_route"), "warn") : null,
			["request_closed", "cannot_do"].includes(r.status) ? null : [field(T("write_to_us"), text), send]);
	}
	function render_complain() {
		const cats = ["used_without_consent", "did_not_stop", "wrong_details", "shared_or_leaked", "staff_behaviour", "request_not_answered", "something_else"];
		const category = h("select", { class: "form-control" }, h("option", { value: "" }, T("choose")), cats.map((c) => h("option", { value: c }, T("cat_" + c))));
		const mine = S.person.requests.filter((r) => r.kind === "request");
		const about = h("select", { class: "form-control" }, h("option", { value: "" }, T("choose")), mine.map((r) => h("option", { value: r.id }, `${r.id} · ${T("type_" + r.type)}`)));
		const aboutField = field(T("which_request"), about);
		aboutField.hidden = true;
		category.onchange = () => { aboutField.hidden = category.value !== "request_not_answered"; };
		const details = h("textarea", { class: "form-control", rows: 4, placeholder: T("hindi_or_english"), maxlength: 2000 });
		const photo = h("input", { type: "file", class: "form-control-file", accept: "image/jpeg,image/png,application/pdf" });
		const go = button(T("send_grievance"));
		go.onclick = busy(go, async () => {
			let data = null;
			const f = photo.files && photo.files[0];
			if (f) {
				if (f.size > 3 * 1024 * 1024) throw new Error(T("photo_too_big"));
				data = await new Promise((ok, no) => { const rd = new FileReader(); rd.onload = () => ok(rd.result); rd.onerror = no; rd.readAsDataURL(f); });
			}
			const r = await call("complain", { i: S.i, category: category.value, details: details.value, about_request: about.value, ...(data ? { photo: data } : {}) });
			S.person = r; S.tab = "requests";
			render_person(T("grievance_sent", r.grievance, date(r.reply_by)));
		});
		show(h("h3", {}, T("make_grievance")), h("p", { class: "text-muted" }, `${S.person.name} · ${T("we_reply_within", C.grievance_days)}`),
			field(T("what_about"), category), aboutField, field(T("what_happened"), details),
			field(T("photo"), photo, T("photo_help")), go,
			h("div", { class: "text-center" }, link(T("go_back"), () => render_person())), footer());
	}
	function render_ask() {
		const types = [
			["withdrawal", T("req_stop"), T("req_stop_help")], ["access", T("req_access"), T("req_access_help")],
			["correction", T("req_correction")], ["erasure", T("req_erasure")], ["nomination", T("req_nomination"), T("req_nomination_help")],
		];
		let picked = "access";
		const details = h("textarea", { class: "form-control", rows: 3, placeholder: T("hindi_or_english"), maxlength: 2000 });
		const go = button(T("send_request"));
		go.onclick = busy(go, async () => {
			if (picked === "withdrawal") { S.tab = "choices"; return render_person(); }
			const r = await call("ask", { i: S.i, request_type: picked, details: details.value });
			S.person = r; S.tab = "requests";
			render_person(T("request_sent", r.request, date(r.reply_by)));
		});
		show(h("h3", {}, T("rights_request")), h("p", { class: "text-muted" }, `${S.person.name} · ${T("we_reply_within", C.reply_days)}`),
			h("div", { class: "ss-card", role: "radiogroup" }, types.map(([k, label, help]) => h("label", { class: "ss-use" },
				h("input", { type: "radio", name: "ss-type", value: k, checked: k === picked, onchange: () => { picked = k; } }),
				h("div", { class: "ss-use-t" }, h("b", {}, label), help ? h("small", {}, help) : null)))),
			field(T("anything_to_add"), details), go,
			h("div", { class: "text-center" }, link(T("go_back"), () => render_person())), footer());
	}

	// ---------------------------------------------------------------- start
	call("home").then((home) => (home && home.signed_in ? after_sign_in(home) : render_sign_in())).catch(() => render_sign_in());
})();
