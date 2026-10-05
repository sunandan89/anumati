"""Journey strips for the product guide: stopping a use, leaving, a slip from someone not on the phone, other
requests, and Add a use or rejoin. Each strip is several phone screens left to right with a caption per step.
People, codes and numbers are fictional.

    pip install playwright && python3 tools/guide_journeys.py   (CHROME=/path/to/chrome to use a local Chromium)

Writes docs/guide/wireframes/j*.png. Reuses the CSS and helpers of tools/guide_wireframes.py; keep both in step
with the app's screens."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guide_wireframes as g  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

OUT = g.OUT
bar, foot = g.bar, g.foot

EXTRA = """
.strip{display:flex;align-items:flex-start;gap:0;padding:20px 24px 28px;background:#EFE5D3;font-family:'Noto Sans','Noto Sans Devanagari',sans-serif;color:#2A2118}
.step{display:flex;flex-direction:column;gap:10px;align-items:center;width:390px}
.cap{font-size:15px;line-height:1.35;text-align:left;width:390px;min-height:62px}
.cap b{color:#B4532A}
.arrow{font-size:34px;color:#B4532A;padding:0 10px;margin-top:380px}
.title{font-size:26px;font-weight:700;padding:22px 24px 0;background:#EFE5D3;font-family:'Noto Sans',sans-serif;color:#2A2118}
.sub{font-size:16px;padding:4px 24px 0;background:#EFE5D3;color:#5C4F40;font-family:'Noto Sans',sans-serif}
.phone{box-shadow:0 6px 24px rgba(0,0,0,.18);border-radius:18px}
.dlg{position:absolute;left:24px;right:24px;top:220px;background:#FFFDF8;border-radius:20px;padding:20px;display:flex;flex-direction:column;gap:12px;box-shadow:0 8px 30px rgba(0,0,0,.25)}
.dlg .h1{font-size:19px;font-weight:600}
.dim{opacity:.35}
.desk{width:390px;height:800px;background:#F4F5F6;border-radius:18px;box-shadow:0 6px 24px rgba(0,0,0,.18);overflow:hidden;font-family:Inter,'Noto Sans',sans-serif;position:relative}
.desk .top{background:#fff;border-bottom:1px solid #E2E6E9;padding:12px 16px;font-weight:600;font-size:15px}
.desk .pad{padding:14px 16px;display:flex;flex-direction:column;gap:10px;font-size:13.5px}
.desk .dbox{background:#fff;border:1px solid #E2E6E9;border-radius:8px;padding:10px 12px;display:flex;flex-direction:column;gap:6px}
.desk .pill{display:inline-block;font-size:12px;padding:2px 8px;border-radius:10px;background:#E8F5E9;color:#2E7D32}
.desk .pill.red{background:#FDECEA;color:#C62828}.desk .pill.blue{background:#E3F2FD;color:#1565C0}
.desk .btn{background:#171717;color:#fff;border-radius:6px;padding:7px 12px;font-size:13px;align-self:flex-start}
.desk .ck{display:flex;gap:8px;align-items:center}
.desk .cb{width:15px;height:15px;border:1.5px solid #8D99A6;border-radius:3px}
.desk .cb.on{background:#171717;border-color:#171717}
.desk .lbl{font-size:12px;color:#6B7785}
.hl{outline:3px solid #B4532A;outline-offset:2px;border-radius:12px}
"""


def phone(body):
    return f'<div class="phone">{body}</div>'


def step(cap, screen):
    return f'<div class="step"><div class="cap">{cap}</div>{screen}</div>'


def strip(name, title, sub, steps):
    arrow = '<div class="arrow">→</div>'
    html = (f'<div class="title">{title}</div><div class="sub">{sub}</div>'
            f'<div class="strip">{arrow.join(steps)}</div>')
    return name, html


def tile(ic, t, d, hl=False):
    return f'<div class="tile{" hl" if hl else ""}"><span class="ic">{ic}</span><div><div class="t">{t}</div><div class="d">{d}</div></div></div>'


def sw(title, sub, on, red=False):
    c = ' style="color:#9E2F24"' if red else ""
    return f'<div class="p"><div><div class="t">{title}</div><div class="d"{c}>{sub}</div></div><span class="sw{" on" if on else ""}"></span></div>'


def person(name, meta, match=""):
    m = f'<div class="muted" style="color:#3E6B3A">{match}</div>' if match else ""
    return f'<div class="card" style="border-color:#B4532A"><b>{name}</b><div class="muted">{meta}</div>{m}</div>'


def locked(title):
    return (f'<div class="p req"><div><div class="t">🔒 {title}</div><div class="d">Needed for the programme. '
            'To stop it, they leave the programme.</div></div></div>')


LEAVE = '<div class="out" style="color:#9E2F24;border-color:#9E2F24">⎋ Leave the programme</div>'
OTHER = '<div class="muted">Other requests: See or correct my data · Delete my data · Complaint</div>'
HOME = bar("Namaste, Ravi", "Village Health Camps") + '<div class="body">' + "".join([
    tile("+", "Take new consent", "Self, assisted or guardian"),
    tile("×", "Stop a use or leave", "In person, slip or letter", hl=True),
    tile("＋", "Add a use or rejoin", "A new use, a change of mind, or rejoining"),
    tile("⌕", "Find beneficiary", "Status offline; stop or add a use"),
]) + "</div>"
SCR = bar("Stop a use or leave", "Withdrawal or request")
SLIP = '<div class="check"><span class="box"></span><div>They gave a paper slip or letter</div></div>'
SLIP_ON = ('<div class="check"><span class="box on"></span><div>They gave a paper slip or letter</div></div>'
           '<div class="field"><span>Paper slip number (optional)</span><b>SLIP-0042</b></div>')


def sw_off(title):
    return (f'<div class="p" style="opacity:.6"><div><div class="t">{title}</div><div class="d" style="color:#9E2F24">Will stop</div></div>'
            '<span class="sw"></span></div>')


def code_box(code):
    return f'<div class="muted">Withdrawal code — write it on their slip</div><div class="code" style="font-size:24px">{code}</div>'



def dialog(title, body, actions):
    return f'<div class="dlg"><div class="h1">{title}</div>{body}<div class="row" style="justify-content:flex-end;gap:14px">{actions}</div></div>'


def cta(label):
    return f'<span class="cta" style="padding:9px 16px;font-size:14px">{label}</span>'


def link(label):
    return f'<span class="link" style="text-decoration:none">{label}</span>'


STRIPS = []

# 1. Stop some uses, found by the family phone number
STRIPS.append(strip(
    "j1-stop-some-uses", "Journey 1: stop some uses (in person, found by phone)",
    "Radha tells Ravi at the camp she doesn't want follow-up calls any more. He finds her by the family phone number.",
    [
        step("<b>1.</b> Home → <b>Stop a use or leave</b>.", phone(HOME)),
        step("<b>2.</b> Type the phone number. Everyone on that number appears, with <b>whose number</b> matched. Tap Radha.",
             phone(SCR + '<div class="body"><div class="field"><span>Receipt code, name, ID or phone</span><b>55500 01234</b></div>'
                   + person("Radha S. (sample)", "VHC-4XK2M9 · AN-7K2Q9C", "Their number")
                   + '<div class="card"><b>Meena S. (sample, child)</b><div class="muted">VHC-8PQ3R1 · AN-M4D2X7</div><div class="muted" style="color:#3E6B3A">Guardian\'s number (Mother)</div></div>'
                   + '<div class="card"><b>Raju S. (sample, child)</b><div class="muted">VHC-2LK9T5 · AN-R8Z6P3</div><div class="muted" style="color:#3E6B3A">Guardian\'s number (Mother)</div></div></div>')),
        step("<b>3.</b> Her uses that are on are switches. Switch off <b>Follow-up calls</b>. The essential use is locked. The slip box is at the bottom. The button says exactly what will happen.",
             phone(SCR + '<div class="body">' + person("Radha S. (sample)", "VHC-4XK2M9 · AN-7K2Q9C", "Their number")
                   + '<div class="row" style="font-weight:400"><span class="muted">Switch off what they no longer agree to</span><span class="link">Stop all</span></div>'
                   + sw("Follow-up calls", "Will stop", False, red=True) + sw("Photos and stories", "On", True)
                   + locked("Health screening") + LEAVE + OTHER + SLIP + "</div>" + foot("Stop 1 use for Radha S. (sample)"))),
        step("<b>4.</b> <b>Withdrawal noted</b>: what stopped and a <b>withdrawal code</b> for her slip. <b>Send by SMS</b> with the code, in her language (to the parent, for a child). On sync: signed, consent check says no, closed request in the inbox.",
             phone(SCR + '<div class="body dim">' + person("Radha S. (sample)", "VHC-4XK2M9") + "</div>"
                   + dialog("Withdrawal noted", '<div style="font-size:14px">Stopped: Follow-up calls</div>' + code_box("AN-W5K7RD")
                            + '<div class="muted">It takes effect on this phone now and reaches the office on sync.</div>',
                            link("Send by SMS") + cta("OK")))),
    ]))

# 2. Leave the programme
STRIPS.append(strip(
    "j2-leave-programme", "Journey 2: leave the programme",
    "Sunita moves away and asks to stop everything, including health screening.",
    [
        step("<b>1.</b> Find Sunita (name, code or phone). Tap <b>Leave the programme</b>.",
             phone(SCR + '<div class="body">' + person("Sunita D. (sample)", "VHC-6TR2W8 · AN-9QH4LM")
                   + sw("Follow-up calls", "On", True) + sw("Photos and stories", "On", True)
                   + locked("Health screening") + '<div class="out hl" style="color:#9E2F24;border-color:#9E2F24">⎋ Leave the programme</div>' + OTHER + "</div>"
                   + foot("Save", off=True))),
        step("<b>2.</b> A warning: every use stops, essential too, and the programme stops serving her. Ravi checks she still wants it.",
             phone(SCR + '<div class="body dim">' + person("Sunita D. (sample)", "VHC-6TR2W8") + "</div>"
                   + dialog("Leave the programme?", '<div style="font-size:14px">This stops every use of their data in this programme, essential ones too. The programme stops serving them. Do they still want this?</div>',
                            link("Cancel") + cta("Yes, leave")))),
        step("<b>3.</b> Every use now shows <b>Will stop</b>, switches greyed, with a warning. <b>Don't leave</b> undoes it. Save.",
             phone(SCR + '<div class="body">' + person("Sunita D. (sample)", "VHC-6TR2W8 · AN-9QH4LM")
                   + sw_off("Follow-up calls") + sw_off("Photos and stories")
                   + '<div class="p req"><div><div class="t">🔒 Health screening</div><div class="d" style="color:#9E2F24">Will stop</div></div></div>'
                   + '<div class="out" style="color:#9E2F24;border:2px solid #9E2F24">↶ Don\'t leave</div>'
                   + '<div class="note bad">Every use above will stop, and the programme stops serving them.</div>' + "</div>"
                   + '<div class="foot"><div class="cta" style="background:#9E2F24">Leave the programme</div></div>')),
        step("<b>4.</b> Noted, with a withdrawal code for her slip. On sync: every use withdrawn (even ones already off, so an older “yes” from another phone can't undo it); her record shows <b>Relationship ended</b> (retention clock starts); inbox has a closed request “Left the programme”.",
             phone(SCR + '<div class="body dim">' + person("Sunita D. (sample)", "VHC-6TR2W8") + "</div>"
                   + dialog("Withdrawal noted", '<div style="font-size:14px">They have left the programme.</div>' + code_box("AN-L2X9FT")
                            + '<div class="muted">It takes effect on this phone now and reaches the office on sync.</div>',
                            link("Send by SMS") + cta("OK")))),
    ]))

# 3. A slip from someone not on this phone, and other requests
STRIPS.append(strip(
    "j3-slip-not-on-phone", "Journey 3: a slip from someone not on this phone",
    "A man hands Ravi a tear-off slip with a receipt code. He isn't on Ravi's phone (another worker enrolled him).",
    [
        step("<b>1.</b> Type the code from the slip: “Not on this phone”. Choose what he wants, then tick <b>paper slip or letter</b> and add the slip number.",
             phone(SCR + '<div class="body"><div class="field"><span>Receipt code, name, ID or phone</span><b>AN-B7W3KD</b></div>'
                   '<div class="note">Not on this phone. It goes to the office inbox with the code.</div>'
                   '<div class="muted">What do they want?</div>'
                   '<div class="opt on"><span class="dot"></span>Stop all optional uses</div>'
                   '<div class="opt"><span class="dot"></span>Leave the programme</div>'
                   '<div class="muted">Other requests</div>'
                   '<div class="opt"><span class="dot"></span>See or correct my data</div>'
                   '<div class="opt"><span class="dot"></span>Delete my data</div>' + SLIP_ON + '</div>' + foot("Save request"))),
        step("<b>2.</b> Saved on the phone; it reaches the office on sync. (Works offline.)",
             phone(SCR + '<div class="body dim"><div class="field"><span>Receipt code, name, ID or phone</span><b>AN-B7W3KD</b></div></div>'
                   + '<div style="position:absolute;left:20px;right:20px;bottom:110px;background:#2A2118;color:#FFF7EF;border-radius:10px;padding:12px 14px;font-size:14px">Saved on this phone. It reaches the office inbox on sync.</div>')),
        step("<b>3.</b> Office: the request is already <b>matched by the code</b>, due in 30 days. Staff open it → <b>Record withdrawal</b>.",
             '<div class="desk"><div class="top">Requests › RR-0117</div><div class="pad">'
             '<div class="dbox"><b>Withdrawal by paper slip</b><span class="lbl">Received today · Due in 30 days</span>'
             '<div><span class="pill blue">Open</span></div><span class="lbl">Beneficiary</span><span>VHC-3MN8Q2 (matched from AN-B7W3KD)</span>'
             '<span class="lbl">Paper slip number</span><span>SLIP-0042</span></div>'
             '<div class="btn">Record withdrawal</div></div></div>'),
        step("<b>4.</b> A checklist of his optional uses that are on, all ticked. The essential use stops only if he leaves: tick <b>Leave the programme</b>. Withdraw → signed, request closed.",
             '<div class="desk"><div class="top dim">Requests › RR-0117</div>'
             '<div class="dlg" style="top:120px;border-radius:10px;gap:10px"><div class="h1" style="font-size:16px">Record withdrawal</div>'
             '<span class="lbl">Uses to stop in Village Health Camps</span>'
             '<div class="ck"><span class="cb on"></span>Follow-up calls</div><div class="ck"><span class="cb on"></span>Photos and stories</div>'
             '<span class="lbl">Essential, stops only if they leave the programme: Health screening</span><hr style="border:0;border-top:1px solid #E2E6E9;width:100%">'
             '<div class="ck"><span class="cb"></span>Leave the programme</div><span class="lbl">Stops every use, essential ones too. The programme stops serving them and their retention clock starts.</span>'
             '<div class="btn" style="align-self:flex-end">Withdraw</div></div></div>'),
    ]))

# 4. Other requests: delete, see or correct, complaint
STRIPS.append(strip(
    "j4-other-requests", "Journey 4: other requests (delete, see or correct, complaint)",
    "Radha asks for her data to be deleted. The worker logs it; the office acts on it.",
    [
        step("<b>1.</b> Find Radha → under <b>Other requests</b> pick <b>Delete my data</b>. It explains what happens.",
             phone(SCR + '<div class="body">' + person("Radha S. (sample)", "VHC-4XK2M9 · AN-7K2Q9C")
                   + sw("Follow-up calls", "On", True) + locked("Health screening")
                   + '<div class="muted">Other requests</div><div class="opt"><span class="dot"></span>See or correct my data</div>'
                   '<div class="opt on"><span class="dot"></span><div>Delete my data<div class="d" style="font-weight:400">The office keeps only what the law needs and erases the rest. This may stop the programme\'s services to them.</div></div></div>'
                   '<div class="opt"><span class="dot"></span>Complaint</div></div>' + foot("Save request"))),
        step("<b>2.</b> Office inbox: <b>Erasure request</b>, matched to Radha, due in 30 days; staff are alerted, and reminded 3 days before.",
             '<div class="desk"><div class="top">Requests</div><div class="pad">'
             '<div class="dbox"><b>Erasure request by field worker</b><span class="lbl">VHC-4XK2M9 · due in 30 days</span><div><span class="pill blue">Open</span></div></div>'
             '<div class="dbox"><b>Data access request by field worker</b><span class="lbl">VHC-6TR2W8 · due in 12 days</span><div><span class="pill blue">Open</span></div></div>'
             '<div class="dbox"><b>Grievance by SMS</b><span class="lbl">Not matched · overdue</span><div><span class="pill red">Overdue</span></div></div></div></div>'),
        step("<b>3.</b> Staff act (erase what the law allows, tell partners), write the resolution, close. Automating erasure is Phase 2.",
             '<div class="desk"><div class="top">Requests › RR-0121</div><div class="pad">'
             '<div class="dbox"><b>Erasure request by field worker</b><span class="lbl">Beneficiary</span><span>VHC-4XK2M9</span>'
             '<span class="lbl">Resolution</span><span>Erased profile and photos; consent records kept as the law requires. Told partner clinic.</span>'
             '<div><span class="pill">Closed</span></div></div></div></div>'),
    ]))

# 5. Add a use or rejoin: the three cases
AP = lambda sub: bar("Add a use or rejoin", sub)  # noqa: E731
ALL = '<div class="two"><span>Yes to all</span><span>No to all</span></div>'


def waiting(kind, title):
    return (f'<div class="card" style="opacity:.5"><b>{kind}: {title}</b><div class="muted">Answer “Rejoin the programme” first.</div>'
            '<div class="two"><span>Yes</span><span>No</span></div></div>')


SHEET = ('<div style="position:absolute;left:0;right:0;bottom:0;background:#FFFDF8;border-radius:18px 18px 0 0;padding:16px;'
         'box-shadow:0 -6px 24px rgba(0,0,0,.18);display:flex;flex-direction:column;gap:12px">'
         '<b>Sunita D. (sample)</b><div class="row" style="font-weight:500">× Stop a use or leave</div>'
         '<div class="row hl" style="font-weight:500;padding:6px">＋ Add a use or rejoin</div></div>')


def ask(kind, title, desc):
    return (f'<div class="card" style="border-color:#3E6B3A"><b>{kind}: {title}</b><div class="d">{desc}</div>'
            '<div class="check" style="padding:6px 0;border:0;background:none"><span class="box on"></span><div>I have read it to them</div></div>'
            '<div class="two"><span>Yes</span><span>No</span></div></div>')


def agreed(*names):
    rows = "".join(f'<div class="row" style="font-weight:400">{n}<span class="st ok">Agreed</span></div>' for n in names)
    return f'<div class="muted">Already agreed, not asked again</div>{rows}'


STRIPS.append(strip(
    "j5-add-use-or-rejoin", "Journey 5: Add a use or rejoin (three cases)",
    "Sunita, Village Health Camps. Home → Add a use or rejoin → pick her (or Find → tap her). Only what's new or changed is asked.",
    [
        step("<b>From Find:</b> tapping a person offers both actions. (Home → <b>Add a use or rejoin</b> also works.)",
             phone(bar("Find beneficiary") + '<div class="body dim"><div class="field"><span>Search by name, ID, code or phone</span><b>sunita</b></div>'
                   + '<div class="card"><b>Sunita D. (sample)</b><div class="muted">VHC-6TR2W8 · AN-9QH4LM</div>'
                   + '<div class="row" style="font-weight:400">Follow-up calls<span class="st bad">Withdrawn</span></div></div></div>' + SHEET)),
        step("<b>Case 1, a new use is added.</b> The NGO added “Health tips by SMS” (notice v2). Photos, which she refused at first, is asked again. With 2+ uses: <b>Yes to all / No to all</b> once each part is read.",
             phone(AP("Later visit · Sunita D. (sample)") + '<div class="body">' + agreed("Health screening", "Follow-up calls") + ALL
                   + ask("New use", "Health tips by SMS", "A weekly health tip by SMS.")
                   + ask("Ask again", "Photos and stories", "Photos of the camp for our reports, never with your name.")
                   + '<div class="muted">How this is confirmed: Code from the server, after Save.</div></div>' + foot("Save"))),
        step("<b>Case 2, she changed her mind.</b> She stopped follow-up calls in May and wants them back.",
             phone(AP("Later visit · Sunita D. (sample)") + '<div class="body">' + agreed("Health screening", "Photos and stories", "Health tips by SMS")
                   + ask("Ask again", "Follow-up calls", "A health worker calls to check on you after the camp.")
                   + '<div class="muted">How this is confirmed: Code from the server, after Save.</div></div>' + foot("Save"))),
        step("<b>Case 3, she left and wants to rejoin.</b> Health screening is a rejoin. The other uses wait until she says Yes to rejoining; if she says No, there is nothing to save.",
             phone(AP("Later visit · Sunita D. (sample)") + '<div class="body"><div class="muted">Already agreed, not asked again: none</div>'
                   + ask("Rejoin the programme", "Health screening", "Blood pressure, sugar and anaemia checks.")
                   + waiting("Ask again", "Follow-up calls") + waiting("Ask again", "Photos and stories")
                   + "</div>" + foot("Save", off=True))),
        step("<b>After Save</b> (any case): a new receipt code for the slip; the server texts a code to confirm. On sync the choices apply; in case 3 <b>Relationship ended</b> is cleared.",
             phone(AP("Later visit · Sunita D. (sample)") + '<div class="body dim">' + agreed("Health screening") + "</div>"
                   + dialog("Saved on this phone", '<div class="muted">Consent code — write it on their slip</div><div class="code">AN-P3V8NQ</div>'
                            '<div class="out">Send code</div>', cta("OK")))),
    ]))


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROME") or None)
        for name, html in STRIPS:
            n = html.count('class="step"')
            width = 48 + n * 390 + (n - 1) * 54
            page = b.new_page(viewport={"width": width, "height": 1000}, device_scale_factor=1)
            page.set_content(f'<!doctype html><html><head><meta charset="utf-8"><style>{g.CSS}{EXTRA}</style></head>'
                             f'<body style="margin:0;background:#EFE5D3">{html}</body></html>')
            page.screenshot(path=os.path.join(OUT, f"{name}.png"), full_page=True)
            print("wrote", f"docs/guide/wireframes/{name}.png")
        b.close()


if __name__ == "__main__":
    main()
