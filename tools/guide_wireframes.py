"""Wireframes of the field app's screens for the product guide (docs/guide/wireframes/*.png).

Each screen is a small HTML mock in the field app's look (colours from lib/core/theme.dart) with the app's
own wording, rendered to PNG. DESK holds Desk (web console) screens, 1280 wide, following the server's
workspace, DocType JSON and form scripts. When a screen changes, update its mock here and re-run, in the same PR:
    pip install playwright && python3 tools/guide_wireframes.py   (CHROME=/path/to/chrome to use another Chromium)
(needs Chromium; fonts: Noto Sans + Noto Sans Devanagari). All names are fictional."""

import os

from playwright.sync_api import sync_playwright

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "guide", "wireframes")
W, H = 390, 800

CSS = """
*{box-sizing:border-box}
body{margin:0;font-family:'Noto Sans','Noto Sans Devanagari',sans-serif;color:#2A2118;background:#F3EADB}
.phone{width:390px;height:800px;position:relative;overflow:hidden;background:#F3EADB}
.bar{background:#3E6B3A;color:#F4F8EF;height:64px;padding:0 12px 0 6px;display:flex;align-items:center;gap:8px}
.bar .bk{width:40px;text-align:center;font-size:22px}.bar .tt{flex:1;min-width:0}
.bar h1{margin:0;font-size:17px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar p{margin:0;font-size:12px;color:#F4F8EF}
.bar .chipb{font-size:12px;padding:4px 10px;border-radius:8px;background:rgba(255,255,255,.24)}
.hero{background:#3E6B3A;color:#F4F8EF;padding:16px 8px 16px 16px}
.hero .pg{font-size:12px}.hero .hi{font-size:24px;font-weight:600;display:flex;justify-content:space-between;align-items:center}
.hero .sbox{margin:12px 8px 0 0;padding:12px;border-radius:12px;background:rgba(255,255,255,.14);display:flex;align-items:center;gap:10px}
.hero .sync{background:#F4F8EF;color:#3E6B3A;border-radius:12px;padding:9px 14px;font-size:14px;font-weight:600;white-space:nowrap}
.body{padding:12px 16px;display:flex;flex-direction:column;gap:9px}
.muted{font-size:13px;color:#5C4F40}
.note{font-size:13px;padding:9px 11px;border-radius:10px;background:#F6E3B8;color:#2A2118}
.note.ok{background:#DDE8D3}.note.bad{background:#F4D6CF;color:#9E2F24}
.card{padding:11px 12px;background:#FFFDF8;border:1px solid #E9DCC6;border-radius:12px;font-size:14px;display:flex;flex-direction:column;gap:3px}
.h{font-size:14px;font-weight:600;margin-top:2px}
.opt{display:flex;gap:10px;align-items:center;padding:10px 12px;border:1px solid #DDCDB3;border-radius:12px;background:#FFFDF8;font-size:14px;font-weight:600}
.opt.on{border-color:#B4532A;background:#F9EBE1}
.dot{width:16px;height:16px;border-radius:8px;border:2px solid #7D6E5C;flex-shrink:0}
.opt.on .dot{border-color:#B4532A;background:radial-gradient(#B4532A 45%,transparent 50%)}
.field{display:flex;flex-direction:column;gap:1px;background:#FFFDF8;border:1px solid #DDCDB3;border-radius:10px;padding:6px 12px 8px}
.field span{font-size:12px;color:#5C4F40}.field b{font-size:16px;font-weight:400;min-height:20px}
.help{font-size:11.5px;color:#5C4F40}
.row{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:14px;font-weight:600}
.seg{display:flex;border:1px solid #7D6E5C;border-radius:18px;overflow:hidden;font-weight:400}
.seg span{padding:6px 12px;font-size:13px}.seg .on{background:#F4DCCB;font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-size:13px;padding:6px 11px;border:1px solid #DDCDB3;border-radius:8px;background:#FFFDF8}
.chip.on{background:#F4DCCB;border-color:#B4532A;font-weight:600}
.tile{display:flex;align-items:center;gap:10px;padding:11px 12px;background:#FFFDF8;border:1px solid #E9DCC6;border-radius:12px;font-size:14px}
.ic{width:22px;height:22px;border-radius:6px;background:#DDE8D3;color:#3E6B3A;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0}
.st{margin-left:auto;font-size:12px;padding:2px 9px;border-radius:10px;background:#EADFCB;color:#5C4F40;white-space:nowrap}
.st.ok{background:#DDE8D3;color:#3E6B3A}.st.warn{background:#F6E3B8;color:#9A6A10}.st.bad{background:#F4D6CF;color:#9E2F24}
.grp{border:1.5px solid #B4532A;border-radius:14px;padding:10px;display:flex;flex-direction:column;gap:8px}
.grp.done{border-color:#3E6B3A}
.p{display:flex;align-items:center;gap:10px;padding:9px 12px;background:#FFFDF8;border:1px solid #E9DCC6;border-radius:12px}
.p.req{background:#EADFCB}.t{font-size:14px;font-weight:600}.d{font-size:12px;color:#5C4F40}
.sw{width:40px;height:24px;border-radius:12px;background:#DDCDB3;position:relative;flex-shrink:0;margin-left:auto}
.sw::after{content:'';position:absolute;top:3px;left:3px;width:18px;height:18px;border-radius:9px;background:#FFFDF8}
.sw.on{background:#3E6B3A}.sw.on::after{left:19px}
.player{padding:10px 12px;background:#FFFDF8;border:2px solid #3E6B3A;border-radius:12px;display:flex;gap:10px;align-items:center}
.play{width:44px;height:44px;border-radius:22px;background:#3E6B3A;color:#F4F8EF;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:18px}
.track{height:4px;background:#3E6B3A;border-radius:2px;margin-top:6px}
.ai{font-size:12px;font-weight:600;color:#3E6B3A}
.two{display:flex;gap:8px}.two span{flex:1;text-align:center;font-size:15px;font-weight:600;padding:11px 8px;border:1.5px solid #B4532A;color:#B4532A;border-radius:12px}
.two span.on{background:#B4532A;color:#FFF7EF}.two.off span{border-color:#DDCDB3;color:#7D6E5C}
.check{display:flex;gap:10px;align-items:flex-start;padding:10px 12px;background:#FFFDF8;border:1px solid #E9DCC6;border-radius:12px;font-size:13.5px}
.box{width:18px;height:18px;border-radius:4px;border:2px solid #7D6E5C;flex-shrink:0;margin-top:1px}
.box.on{background:#3E6B3A;border-color:#3E6B3A}
.code{font-family:monospace;font-size:28px;letter-spacing:3px;text-align:center}
.otp{font-size:22px;letter-spacing:8px;text-align:center;background:#FFFDF8;border:1px solid #DDCDB3;border-radius:10px;padding:6px}
.out{text-align:center;font-size:15px;font-weight:600;padding:11px;border:1.5px solid #B4532A;color:#B4532A;border-radius:12px}
.link{font-size:13px;color:#3E6B3A;font-weight:600;text-decoration:underline}
.foot{position:absolute;left:0;right:0;bottom:0;padding:10px 16px 18px;background:#F3EADB;border-top:1px solid #E9DCC6;display:flex;flex-direction:column;gap:6px}
.miss{font-size:13px;color:#9E2F24;text-align:center}
.cta{text-align:center;font-size:16px;font-weight:600;padding:14px;border-radius:12px;background:#B4532A;color:#FFF7EF}
.cta.off{background:#DDCDB3;color:#7D6E5C}
.sec{text-align:center;font-size:16px;font-weight:600;padding:12px;border:1.5px solid #B4532A;color:#B4532A;border-radius:12px}
.fill{text-align:center;font-size:15px;font-weight:600;padding:11px;border-radius:12px;background:#B4532A;color:#FFF7EF}
.dlg{position:absolute;left:24px;right:24px;top:220px;background:#FFFDF8;border-radius:20px;padding:20px;display:flex;flex-direction:column;gap:12px;box-shadow:0 8px 30px rgba(0,0,0,.25)}
.dlg .h1{font-size:19px;font-weight:600}
.dim{opacity:.35}
.toast{position:absolute;left:20px;right:20px;bottom:110px;background:#2A2118;color:#FFF7EF;border-radius:10px;padding:12px 14px;font-size:14px}
.sheet{position:absolute;left:0;right:0;bottom:0;background:#FFFDF8;border-radius:18px 18px 0 0;padding:16px;box-shadow:0 -6px 24px rgba(0,0,0,.18);display:flex;flex-direction:column;gap:12px}
.pin{display:flex;justify-content:center;gap:16px}.pin span{width:16px;height:16px;border-radius:8px;border:2px solid #B4532A}.pin span.on{background:#B4532A}
.keys{display:grid;grid-template-columns:repeat(3,1fr);row-gap:10px;text-align:center;font-size:26px;padding:0 24px}
.big{display:flex;flex-direction:column;align-items:center;gap:4px;padding:6px 0}
.tick{width:56px;height:56px;border-radius:28px;background:#DDE8D3;color:#3E6B3A;display:flex;align-items:center;justify-content:center;font-size:28px}
"""


def bar(title, sub="", back=True, chip="Offline"):
    """The app bar (StepBar): back arrow, subtitle above the title, and the Offline / Synced chip."""
    return (f'<div class="bar"><span class="bk">{"←" if back else ""}</span><div class="tt">{f"<p>{sub}</p>" if sub else ""}'
            f'<h1>{title}</h1></div>{f"<span class=chipb>{chip}</span>" if chip else ""}</div>')


def home_head(n=3):
    """Home's own header: programme, greeting, and the sync box."""
    sub = "Sync when you have data" if n else "Everything is signed on the server"
    return (f'<div class="hero"><div class="pg">Village Health Camps</div><div class="hi">Namaste, Ravi<span style="font-size:20px">⋮</span></div>'
            f'<div class="sbox"><div style="flex:1"><div style="font-weight:600">{n} records on this phone</div>'
            f'<div style="font-size:12px">{sub}</div></div><span class="sync">⟳ Sync</span></div></div>')


def foot(label, missing="", off=False, second=""):
    m = f'<div class="miss">{missing}</div>' if missing else ""
    s = f'<div class="sec">{second}</div>' if second else ""
    return f'<div class="foot">{m}<div class="cta{" off" if off else ""}">{label}</div>{s}</div>'


def who(selected):
    labels = [("self", "The person, for themself"), ("child", "A parent, for a child under 18"),
              ("guardian", "A guardian, for an adult who can't decide alone")]
    return "".join(f'<div class="opt{" on" if k == selected else ""}"><span class="dot"></span>{v}</div>' for k, v in labels)


def yesno(q, yes, a="Yes", b="No"):
    return (f'<div class="row">{q}<div class="seg"><span class="{"on" if yes else ""}">{a}</span>'
            f'<span class="{"" if yes else "on"}">{b}</span></div></div>')


def lang(hi=False):
    return yesno("Language", not hi, "English", "हिन्दी")


ATTEST = ('<div class="check"><span class="box on"></span><div>I played the full notice in the person\'s language, '
          'answered their questions, and they chose freely. Nothing was pre-selected.</div></div>')
ATTEST_G = ('<div class="check"><span class="box on"></span><div>I played the full notice to the guardian, '
            'answered their questions, and they chose freely. Nothing was pre-selected.</div></div>')
PLAYER = ('<div class="player"><div class="play">❚❚</div><div style="flex:1"><div class="t">Notice played in full</div>'
          '<div class="d">Reviewed recording · 1:48 / 1:48</div><div class="ai">Natural voice · Powered by Sarvam AI</div>'
          '<div class="track"></div></div></div>')
FOLD = '<div class="card" style="flex-direction:row;justify-content:space-between"><span>Read the full notice (data, rights, how to withdraw)</span><span>▾</span></div>'


def purpose(title, desc, on=None):
    if on is None:
        return f'<div class="p req"><div><div class="t">{title}</div><div class="d">{desc}</div></div><span class="st">Required</span></div>'
    return (f'<div class="p"><div><div class="t">{title}</div><div class="d">{desc} · optional</div></div>'
            f'<span class="sw{" on" if on else ""}"></span></div>')


SCREENS = {
    "home": home_head() + """<div class="body">
<div class="muted">Programme</div><div class="card" style="flex-direction:row;justify-content:space-between"><span>Village Health Camps</span><span style="color:#B4532A;font-size:13px">Change</span></div>
<div class="tile"><span class="ic">+</span><div><div class="t">Take new consent</div><div class="d">Self, assisted or guardian</div></div></div>
<div class="tile"><span class="ic">×</span><div><div class="t">Stop a use or leave</div><div class="d">In person, slip or letter</div></div></div>
<div class="tile"><span class="ic">＋</span><div><div class="t">Add a use or rejoin</div><div class="d">A new use, a change of mind, or rejoining</div></div></div>
<div class="tile"><span class="ic">⌕</span><div><div class="t">Find beneficiary</div><div class="d">Status offline; stop or add a use</div></div></div>
</div>""",
    "a1-who": bar("Who is giving consent?", "Step 1 of 3") + f"""<div class="body">{who("self")}
<div class="field"><span>Name</span><b>Sunita Devi (sample)</b></div>
{yesno("Has a mobile phone?", True)}
<div class="field"><span>Mobile number</span><b>90000 12345</b></div>
{yesno("Can read the notice?", True, "Yes", "Needs help")}{lang()}
<div class="row" style="font-weight:400">More: phone shared in the household<span>▾</span></div>
<div class="muted">The beneficiary ID is created automatically.</div></div>""" + foot("Continue"),
    "a2-notice": bar("Notice and choices", "Step 2 of 3") + f"""<div class="body">{PLAYER}
<div class="t" style="font-size:15px">We screen your health and refer you to a doctor if needed.</div>{FOLD}
<div class="h">Choose for each use</div>
{purpose("Health screening", "Blood pressure, sugar and anaemia checks")}
{purpose("Follow-up calls", "A health worker calls after the camp", True)}
{purpose("Photos and stories", "Camp photos, never with your name", False)}
{purpose("Anonymised research", "Results without names", False)}
<div class="two"><span>Yes to all</span><span>No to all</span></div></div>""" + foot("Continue"),
    "a3-confirm-online": bar("Confirm and save", "Step 3 of 3") + f"""<div class="body">
<div class="card"><b>Sunita Devi (sample) · English</b><div class="muted">Agreed: Health screening, Follow-up calls</div><div class="muted">Refused: Photos and stories, Anonymised research</div></div>
<div class="note">After Save, you can send a code to their phone from the server. They read it out to confirm.</div>
<div class="muted">No witness: they read the notice themselves.</div>{ATTEST}</div>""" + foot("Save"),
    "a4-receipt-code": bar("Saved on this phone", "DEMO", back=False) + """<div class="body">
<div class="big"><div class="tick">✓</div><div class="t" style="font-size:20px">Saved on this phone</div><div class="muted">Signed and chained when this phone syncs</div></div>
<div class="card" style="border:1.5px solid #D9A285"><div class="muted" style="text-align:center">Consent code — write it on their slip</div><div class="code">AN-7K2Q9C</div></div>
<div class="card"><div class="row" style="font-weight:400"><span class="d">Sunita Devi (sample)</span><span>English</span></div><div class="row" style="font-weight:400"><span class="d">Granted</span><span>Health screening, Follow-up calls</span></div><div class="row" style="font-weight:400"><span class="d">Refused</span><span>Photos and stories, Anonymised research</span></div><div class="row" style="font-weight:400"><span class="d">Verified by</span><span>Code from the server (below)</span></div></div>
<div class="grp done"><div class="t">Confirm with a code to their phone</div><div class="muted">The code is sent by the server, not from this phone. They read it out to you.</div>
<div class="muted">Code sent to 9000012XXX. Ask them to read it out.</div><div class="otp">4 8 1 _ _ _</div><div class="link">Send a new code</div></div>
<div class="card">Tell them: SMS STOP with this code, a missed call, or tell any worker to withdraw.</div>
<div class="out">✉ Send receipt by SMS</div><div class="muted" style="text-align:center">Opens your SMS app with their receipt. You tap Send.</div></div>""" + foot("Done — next beneficiary"),
    "a5-confirm-offline": bar("Confirm and save", "Step 3 of 3") + f"""<div class="body">
<div class="card"><b>Sunita Devi (sample) · English</b><div class="muted">Agreed: Health screening, Follow-up calls</div></div>
<div class="grp"><div class="row">Check their phone · both needed<span class="st bad">0 of 1</span></div>
<div class="muted">No internet: the code goes from your phone. Their voice “haan” is needed with it.</div>
<div class="out">Open SMS app with code</div><div class="muted">Code they read back</div><div class="otp">_ _ _ _ _ _</div>
<div class="link">Can't get the code now? Confirm later by SMS</div>
<div class="tile"><span class="ic">🎙</span>Voice: their “haan”<span class="st">Tap to record</span></div></div>
<div class="muted">No witness: they read the notice themselves.</div>{ATTEST}</div>""" + foot("Save", "To save: the SMS code, their voice “haan”", off=True),
    "b1-who-help": bar("Who is giving consent?", "Step 1 of 3") + f"""<div class="body">{who("self")}
<div class="field"><span>Name</span><b>Kamla Bai (sample)</b></div>
{yesno("Has a mobile phone?", False)}{yesno("Can read the notice?", False, "Yes", "Needs help")}{lang(True)}
<div class="note">No phone and needs help reading: at the end you record their “haan” or thumbprint and a witness's name. They get a paper slip with their code.</div>
<div class="muted">The beneficiary ID is created automatically.</div></div>""" + foot("Continue"),
    "b2-notice-hindi": bar("सूचना और चुनाव", "Step 2 of 3") + f"""<div class="body">{PLAYER.replace("Natural voice · Powered by Sarvam AI", "प्राकृतिक आवाज़ · Sarvam AI द्वारा").replace("Notice played in full", "सूचना पूरी सुनाई गई")}
<div class="t" style="font-size:15px">हम आपकी स्वास्थ्य जाँच करते हैं और ज़रूरत हो तो डॉक्टर के पास भेजते हैं।</div>
<div class="h">हर उपयोग के लिए चुनें</div>
{purpose("स्वास्थ्य जाँच", "बीपी, शुगर और खून की कमी की जाँच")}
{purpose("फ़ोटो और कहानियाँ", "कैंप की फ़ोटो, कभी नाम के साथ नहीं", True)}
{purpose("बिना नाम का शोध", "बिना नाम के जाँच के नतीजे", False)}
<div class="muted">जिन उपयोगों के लिए फ़ोन चाहिए, वे नहीं पूछे गए।</div>
<div class="two"><span>सब के लिए हाँ</span><span>सब के लिए नहीं</span></div></div>""".replace("· optional", "· वैकल्पिक").replace(">Required<", ">ज़रूरी<") + foot("आगे बढ़ें"),
    "b3-confirm-witness": bar("Confirm and save", "Step 3 of 3") + f"""<div class="body">
<div class="card"><b>Kamla Bai (sample) · हिन्दी · needs help reading · no phone</b><div class="muted">Agreed: Health screening, Photos and stories</div></div>
<div class="grp done"><div class="row">Record their yes · choose at least one<span class="st ok">✓ Done</span></div>
<div class="tile"><span class="ic">🎙</span>Voice: their “haan”<span class="st ok">Saved</span></div>
<div class="tile"><span class="ic">☝</span>Thumbprint on their slip<span class="st">Tap to capture</span></div></div>
<div class="h">Witness (needed because the notice was read to them)</div>
<div class="field"><span>Witness name</span><b>Shanti (sample neighbour)</b></div>
<div class="field"><span>Relation (optional)</span><b>&nbsp;</b></div>{ATTEST}</div>""" + foot("Save"),
    "b4-reads-no-phone": bar("Confirm and save", "Step 3 of 3") + f"""<div class="body">
<div class="card"><b>Mohan Lal (sample) · English · no phone</b><div class="muted">Agreed: Health screening, Photos and stories</div></div>
<div class="grp"><div class="row">Record their yes · choose at least one<span class="st bad">0 of 1</span></div>
<div class="tile"><span class="ic">🎙</span>Voice: their “haan”<span class="st">Tap to record</span></div>
<div class="tile"><span class="ic">☝</span>Photo of their signature or thumbprint on the slip<span class="st">Tap to capture</span></div></div>
<div class="muted">No witness: they read the notice themselves.</div>{ATTEST}</div>""" + foot("Save", "To save: a voice “haan” or a photo", off=True),
    "c1-who-child": bar("Who is giving consent?", "Step 1 of 3") + f"""<div class="body">{who("child")}
<div class="field"><span>Child's name</span><b>Aarav (sample)</b></div>
<div class="field"><span>Child's year of birth</span><b>2014</b></div><div class="help">Used only to ask for fresh consent when the child turns 18.</div>
{lang()}
<div class="note">No phone or reading questions for the child. The parent's mobile is asked on the next screen, where it is verified.</div></div>""" + foot("Continue"),
    "c2-parent": bar("Parent's details", "Step 2 of 3") + """<div class="body">
<div class="card">For Aarav (sample) · under 18</div>
<div class="muted">Who is consenting?</div><div class="chips"><span class="chip on">Mother</span><span class="chip">Father</span><span class="chip">Other guardian</span></div>
<div class="field"><span>Parent's name</span><b>Meena Kumari (sample)</b></div>
<div class="field"><span>Parent's mobile</span><b>90000 67890</b></div>
<div class="muted">After Save, a code is sent to this number from the server. They read it out to confirm.</div>
<div class="tile"><span class="ic">📷</span>Photo of the parent's ID (optional)<span class="st">Tap to capture</span></div></div>""" + foot("Continue"),
    "c3-notice-save": bar("Notice and choices", "Step 3 of 3") + f"""<div class="body">{PLAYER}
<div class="h">Choose for each use</div>
{purpose("Attendance and learning records", "Who comes and how they learn")}
{purpose("SMS updates to parents", "Attendance and progress", True)}
{purpose("Photos for our reports", "Never with the child's name", False)}
<div class="muted">Some uses are not offered for children.</div>
<div class="two"><span>Yes to all</span><span>No to all</span></div>{ATTEST_G}</div>""" + foot("Save"),
    "c4-parent-offline": bar("Parent's details", "Step 2 of 3") + """<div class="body">
<div class="card">For Aarav (sample) · under 18</div>
<div class="chips"><span class="chip on">Mother</span><span class="chip">Father</span><span class="chip">Other guardian</span></div>
<div class="field"><span>Parent's mobile</span><b>90000 67890</b></div>
<div class="muted">No internet: the code goes from your phone. The guardian's voice “haan” is needed with it.</div>
<div class="out">Open SMS app with code</div><div class="otp">2 7 0 9 1 4</div>
<div class="note ok">✓ Code matched</div>
<div class="tile"><span class="ic">🎙</span>Voice: the guardian’s “haan”<span class="st ok">Saved</span></div></div>""" + foot("Continue"),
    "d2-guardian": bar("Guardian's details", "Step 2 of 3") + """<div class="body">
<div class="card">For Ramesh Kumar (sample) · adult who can't decide alone</div>
<div class="muted">Guardian appointed by</div><div class="chips"><span class="chip on">Local Level Committee</span><span class="chip">Court</span><span class="chip">Other authority</span><span class="chip">No order yet</span></div>
<div class="field"><span>Order number</span><b>LLC/2026/0412 (sample)</b></div>
<div class="tile"><span class="ic">📷</span>Photo of the order (optional)<span class="st ok">Saved</span></div>
<div class="muted">Relation</div><div class="chips"><span class="chip">Parent</span><span class="chip on">Brother / sister</span><span class="chip">Spouse</span><span class="chip">Other</span></div>
<div class="field"><span>Guardian's name</span><b>Suresh Kumar (sample)</b></div>
<div class="field"><span>Guardian's mobile</span><b>90000 24680</b></div>
<div class="muted">After Save, a code is sent to this number from the server. They read it out to confirm.</div>
<div class="tile"><span class="ic">📷</span>Photo of the guardian's ID (optional)<span class="st">Tap to capture</span></div></div>""" + foot("Continue"),
    "d3-no-order": bar("Guardian's details", "Step 2 of 3") + """<div class="body">
<div class="muted">Guardian appointed by</div><div class="chips"><span class="chip">Local Level Committee</span><span class="chip">Court</span><span class="chip">Other authority</span><span class="chip on">No order yet</span></div>
<div class="card" style="border:1.5px solid #B4532A;gap:8px"><div class="t" style="color:#9E2F24;font-size:17px">Consent can't be taken yet</div>
<div>For an adult who can't decide alone, only a guardian appointed by a court or the Local Level Committee can give consent.</div>
<div>The family can apply to the Local Level Committee (National Trust) or a court. The person can still be helped today; their data just isn't recorded under consent.</div></div>
<div class="muted">Nothing is saved. Your coordinator gets a note to follow up, without the person's details.</div></div>""" + foot("Inform coordinator", second="Back"),
    "e1-about": bar("About the person", "Step 3 of 4") + """<div class="body">
<div class="field"><span>Age in years</span><b>34</b></div>
<div class="h">Gender (optional)</div><div class="chips"><span class="chip on">Female</span><span class="chip">Male</span><span class="chip">Other</span><span class="chip">Prefer not to say</span></div>
<div class="h">Occupation (optional)</div><div class="chips"><span class="chip">Farming or farm labour</span><span class="chip on">Daily wage work</span><span class="chip">Homemaker</span><span class="chip">Self-employed</span><span class="chip">Other</span></div>
<div class="note">These are listed in the notice under “What we collect”. Reports show only totals, never one person's answers.</div></div>""" + foot("Continue"),
    "f1-withdraw": bar("Stop a use or leave", "Withdrawal or request") + """<div class="body">
<div class="field"><span>⌕ Receipt code, name, ID or phone</span><b>AN-7K2Q9C</b></div>
<div class="card" style="border-color:#B4532A"><b>Sunita Devi (sample)</b><div class="muted">AC-6TR2W3HJ · AN-7K2Q9C</div></div>
<div class="row" style="font-weight:400"><span class="muted">Switch off what they no longer agree to</span><span class="link">Stop all</span></div>
<div class="p"><div><div class="t">Follow-up calls</div><div class="d" style="color:#9E2F24">Will stop</div></div><span class="sw"></span></div>
<div class="p"><div><div class="t">Photos and stories</div><div class="d">On</div></div><span class="sw on"></span></div>
<div class="p req"><div><div class="t">🔒 Health screening</div><div class="d">Needed for the programme. To stop it, they leave the programme.</div></div></div>
<div class="out" style="color:#9E2F24;border-color:#9E2F24">⎋ Leave the programme</div>
<div class="muted" style="border-top:1px solid #DDCDB3;padding-top:8px">Other requests</div>
<div class="opt"><span class="dot"></span>See or correct my data</div><div class="opt"><span class="dot"></span>Delete my data</div>
<div class="opt"><span class="dot"></span>Complaint</div>
<div class="check"><span class="box on"></span><div>They gave a paper slip or letter</div></div></div>""" + foot("Stop 1 use for Sunita Devi (sample)"),
    "f2-leave": bar("Stop a use or leave", "Withdrawal or request") + """<div class="body" style="opacity:.35">
<div class="card"><b>Sunita Devi (sample)</b><div class="muted">AC-6TR2W3HJ · AN-7K2Q9C</div></div>
<div class="p"><div><div class="t">Follow-up calls</div></div><span class="sw on"></span></div></div>
<div style="position:absolute;left:24px;right:24px;top:230px;background:#FFFDF8;border-radius:20px;padding:20px;display:flex;flex-direction:column;gap:12px;box-shadow:0 8px 30px rgba(0,0,0,.25)">
<div style="font-size:19px;font-weight:600">Leave the programme?</div>
<div style="font-size:14px">This stops every use of their data in this programme, essential ones too. The programme stops serving them. Do they still want this?</div>
<div class="row" style="justify-content:flex-end"><span class="link" style="text-decoration:none">Cancel</span><span class="cta" style="padding:9px 16px;font-size:14px">Yes, leave</span></div></div>""",
    "f3-noted": bar("Stop a use or leave", "Withdrawal or request") + """<div class="body" style="opacity:.35">
<div class="card"><b>Sunita Devi (sample)</b></div></div>
<div style="position:absolute;left:24px;right:24px;top:230px;background:#FFFDF8;border-radius:20px;padding:20px;display:flex;flex-direction:column;gap:12px;box-shadow:0 8px 30px rgba(0,0,0,.25)">
<div style="font-size:19px;font-weight:600">Withdrawal noted</div>
<div style="font-size:14px">Stopped: Follow-up calls</div>
<div class="muted">Withdrawal code — write it on their slip</div><div class="code" style="font-size:24px">AN-W5K7RD</div>
<div class="muted">It takes effect on this phone now and reaches the office on sync.</div>
<div class="row" style="justify-content:flex-end"><span class="link" style="text-decoration:none">Send by SMS</span><span class="cta" style="padding:9px 16px;font-size:14px">OK</span></div></div>""",
}

KEYS = ('<div class="keys">' + "".join(f"<span>{k}</span>" for k in "123456789") + '<span></span><span>0</span><span>⌫</span></div>')


def status(title, st):
    tone = {"granted": "ok", "withdrawn": "bad", "refused": "warn"}.get(st, "")
    return f'<div class="row" style="font-weight:400;font-size:13px">{title}<span class="st {tone}">{st}</span></div>'


NEW_SCREENS = {
    "m1-sign-in": """<div class="body" style="padding:48px 24px;gap:14px">
<div style="display:flex;align-items:center;gap:12px"><div style="width:48px;height:48px;border-radius:14px;background:#3E6B3A;color:#F4F8EF;display:flex;align-items:center;justify-content:center;font-size:22px">🛡</div><div style="font-size:24px;font-weight:600">Anumati Collect</div></div>
<div class="seg" style="align-self:flex-start"><span class="on">English</span><span>हिन्दी</span></div>
<div class="field" style="margin-top:12px"><span>Organisation address</span><b>sample-ngo.frappe.cloud</b></div>
<div class="field"><span>User ID</span><b>ravi.sample</b></div>
<div class="field"><span>Password</span><b style="display:flex;justify-content:space-between">••••••••<span>👁</span></b></div>
<div class="note bad">Could not sign in. Check your user ID and password.</div>
<div class="cta">Sign in</div></div>""",
    "m2-set-pin": """<div class="body" style="padding:56px 24px 0;align-items:center;gap:12px;text-align:center">
<div style="font-size:40px;color:#3E6B3A">🔒</div><div style="font-size:20px;font-weight:600">Choose a 4-digit PIN for this app</div>
<div class="muted">The app locks when you leave it for 5 minutes. Names and evidence stay protected.</div>
<div class="pin" style="margin-top:12px"><span class="on"></span><span class="on"></span><span></span><span></span></div></div>
<div style="position:absolute;left:0;right:0;bottom:60px">""" + KEYS + "</div>",
    "m3-unlock": """<div class="body" style="padding:56px 24px 0;align-items:center;gap:12px;text-align:center">
<div style="font-size:40px;color:#3E6B3A">🔒</div><div style="font-size:20px;font-weight:600">Enter your PIN</div>
<div class="pin" style="margin-top:12px"><span></span><span></span><span></span><span></span></div>
<div class="note bad">Wrong PIN. 4 tries left.</div></div>
<div style="position:absolute;left:0;right:0;bottom:24px;display:flex;flex-direction:column;gap:18px">""" + KEYS + """
<div class="link" style="text-align:center;text-decoration:none;color:#B4532A">Forgot PIN? Sign out</div></div>""",
    "d1-who-guardian": bar("Who is giving consent?", "Step 1 of 3") + f"""<div class="body">{who("guardian")}
<div class="field"><span>Person's name</span><b>Ramesh Kumar (sample)</b></div>{lang()}
<div class="note">The guardian's details, their appointment order and their mobile are asked on the next screen.</div>
<div class="muted">The beneficiary ID is created automatically.</div></div>""" + foot("Continue"),
    "a6-notice-phone-voice": bar("Notice and choices", "Step 2 of 3") + f"""<div class="body">
<div class="player" style="flex-direction:column;align-items:stretch"><div style="display:flex;gap:10px;align-items:center"><div class="play">🔊</div>
<div><div class="t">Listen to the notice</div><div class="d">Phone voice · the notice is read aloud by this phone</div></div></div>
<div class="track" style="width:35%"></div></div>
<div class="t" style="font-size:15px">We screen your health and refer you to a doctor if needed.</div>
<div class="card" style="flex-direction:row;justify-content:space-between"><span class="t">Read the full notice (data, rights, how to withdraw)</span><span>▴</span></div>
<div class="muted" style="padding:0 4px"><b>Why we need this.</b> Health screening. Blood pressure, sugar and anaemia checks. Follow-up calls…</div>
<div class="out">✓✓ They have read the whole notice</div>
<div class="h">Choose for each use</div>
{purpose("Health screening", "Blood pressure, sugar and anaemia checks")}
<div style="opacity:.5;display:flex;flex-direction:column;gap:9px">{purpose("Follow-up calls", "A health worker calls after the camp", False)}
{purpose("Photos and stories", "Camp photos, never with your name", False)}</div>
<div class="two off"><span>Yes to all</span><span>No to all</span></div>
<div class="note">Choices unlock when the whole notice has been heard or read</div></div>""" + foot("Continue", off=True),
    "k1-find": bar("Find beneficiary", chip="Synced") + """<div class="body">
<div class="field"><span>⌕ Search by name, ID, code or phone</span><b>90000 12345</b></div>
<div class="card"><b>Sunita Devi (sample)</b><div class="muted">AC-6TR2W3HJ · AN-7K2Q9C · English</div><div class="muted">Their number</div>""" + status("Health screening", "granted") + status("Follow-up calls", "withdrawn") + status("Photos and stories", "refused") + status("Anonymised research", "not asked") + """</div>
<div class="card"><b>Pooja (sample)</b><div class="muted">AC-5PQ3RZ2A · AN-M4D2XC · English</div><div class="muted">Guardian's number (Mother)</div>""" + status("Health screening", "granted") + status("Follow-up calls", "granted") + status("Photos and stories", "not asked") + status("Anonymised research", "not asked") + """</div></div>""",
    "k2-sync-issues": home_head(2) + """<div class="body">
<div class="card" style="background:#F4D6CF;border-color:#9E2F24;flex-direction:row;gap:10px;align-items:center"><span style="color:#9E2F24;font-size:18px">ⓘ</span>1 records could not be saved on the server. Open to see why.</div>
<div class="muted">Programme</div><div class="card" style="flex-direction:row;justify-content:space-between"><span>Village Health Camps</span><span style="color:#B4532A;font-size:13px">Change</span></div></div>
<div style="position:absolute;left:0;right:0;top:300px;bottom:0;background:#F3EADB;box-shadow:0 -6px 24px rgba(0,0,0,.18);border-radius:18px 18px 0 0;overflow:hidden">""" + bar("Records that need attention") + """<div class="body">
<div class="card"><b>consent · AC-2LK7T5WE · AN-R8Z6PC</b><div class="muted">2026-10-14 16:42:05</div>
<div class="note bad">This programme's notice was withdrawn. Ask the office to publish it again.</div>
<div class="row" style="justify-content:flex-start;gap:20px;color:#B4532A"><span>Try again</span><span>Discard</span></div></div></div></div>""",
}
SCREENS.update(NEW_SCREENS)


# ---------------------------------------------------------------- Desk (web console) screens, 1280 wide
DESK_CSS = """
body{margin:0;background:#F4F5F6;font-family:Inter,'Noto Sans','Noto Sans Devanagari',sans-serif;color:#1F272E;font-size:13px}
.capband{background:#2A2118;color:#F3EADB;padding:14px 24px;font-size:14.5px;line-height:1.5}.capband b{color:#F2A97F}
.nav{background:#fff;border-bottom:1px solid #E2E6E9;height:48px;display:flex;align-items:center;gap:14px;padding:0 24px}
.logo{width:24px;height:24px;border-radius:6px;background:#B4532A;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px}
.srch{margin-left:auto;width:360px;background:#F3F3F3;border-radius:8px;padding:8px 12px;color:#8D99A6}
.av{width:28px;height:28px;border-radius:14px;background:#E2E6E9;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:11px}
.wrap{display:flex;gap:24px;padding:20px 24px}
.side{width:200px;flex-shrink:0;display:flex;flex-direction:column;gap:2px}
.side div{padding:7px 10px;border-radius:6px;color:#383838}.side .on{background:#fff;font-weight:600;box-shadow:0 1px 2px rgba(0,0,0,.06)}.side .sub{padding-left:26px}
.main{flex:1;display:flex;flex-direction:column;gap:14px}
.wh{font-size:15px;font-weight:700;margin-top:6px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.nc{background:#fff;border:1px solid #E2E6E9;border-radius:10px;padding:14px 16px}.nc .l{color:#6B7785;font-size:12.5px}.nc .v{font-size:24px;font-weight:600;margin-top:6px}
.nc .v.red{color:#C62828}.nc .v.or{color:#C76B00}
.scs{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.sc{background:#fff;border:1px solid #E2E6E9;border-radius:10px;padding:12px 16px;font-weight:600;display:flex;justify-content:space-between}
.sc span{color:#8D99A6;font-weight:400}
.panel{background:#fff;border:1px solid #E2E6E9;border-radius:10px;padding:16px 18px;display:flex;flex-direction:column;gap:10px}
.att .row{padding:8px 10px;border-radius:6px;font-size:13.5px}.att .red{background:#FDECEA;color:#9E2F24}.att .amber{background:#FFF4E0;color:#8A5300}
.tag{font-size:11.5px;color:#8D99A6;text-transform:uppercase;letter-spacing:.5px}
.ttl{display:flex;align-items:center;gap:10px}.ttl h2{margin:0;font-size:21px}
.pill{font-size:12px;padding:2px 8px;border-radius:10px;background:#FFF4E0;color:#C76B00}
.btns{margin-left:auto;display:flex;gap:8px;align-items:flex-start}
.bt{background:#F3F3F3;border-radius:6px;padding:7px 12px;font-weight:500}.bt.dk{background:#171717;color:#fff}
.menu{position:absolute;right:0;top:36px;background:#fff;border:1px solid #E2E6E9;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.12);padding:6px;width:240px;z-index:2}
.menu div{padding:8px 10px;border-radius:5px}.menu .hv{background:#F3F3F3}
.alert{padding:10px 14px;border-radius:8px;background:#FDECEA;color:#C62828}
.form{background:#fff;border:1px solid #E2E6E9;border-radius:10px}
.tabs{display:flex;gap:24px;padding:0 20px;border-bottom:1px solid #E2E6E9}.tabs div{padding:14px 0;color:#6B7785}.tabs .on{color:#1F272E;border-bottom:2px solid #1F272E;font-weight:500}
.sec{padding:18px 20px;border-bottom:1px solid #E2E6E9;display:flex;flex-direction:column;gap:12px}
.sec h3{margin:0;font-size:14px}.desc{color:#6B7785;font-size:12px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.fl{display:flex;flex-direction:column;gap:5px}.fl .lb{color:#525252;font-size:12.5px}.fl .in{background:#F3F3F3;border-radius:6px;padding:8px 10px;min-height:18px}
.big3{display:flex;gap:28px}.big3 b{font-size:20px;display:block}.big3 span{color:#6B7785;font-size:12px}
.bubble{background:#F3F3F3;border-radius:12px 12px 12px 3px;padding:10px 12px;max-width:560px;line-height:1.45}
table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #E2E6E9}th{color:#6B7785;font-weight:500;background:#F9FAFA}
.ck{display:inline-block;width:14px;height:14px;border:1.5px solid #8D99A6;border-radius:3px;vertical-align:middle}.ck.on{background:#171717;border-color:#171717}
"""


def desk(cap, crumb, body, side=None):
    nav = (f'<div class="capband">{cap}</div><div class="nav"><span class="logo">अ</span><span style="color:#525252">{crumb}</span>'
           '<span class="srch">Search or type a command (Ctrl + G)</span><span class="av">PM</span></div>')
    if side is None:
        return nav + f'<div style="padding:16px 24px;display:flex;flex-direction:column;gap:14px">{body}</div>'
    return nav + f'<div class="wrap"><div class="side">{side}</div><div class="main">{body}</div></div>'


def nc(label, v, tone=""):
    return f'<div class="nc"><div class="l">{label}</div><div class="v {tone}">{v}</div></div>'


SIDE = "".join(f'<div class="{c}">{t}</div>' for c, t in [
    ("", "Today"), ("on", "Requests"), ("sub", "Rights requests"), ("sub", "Grievances"), ("", "Beneficiaries"),
    ("", "Programmes"), ("", "Analytics"), ("", "Notices and Compliance"), ("", "Setup")])

ATT = ('<div class="panel att"><div class="tag">On the Today page</div><b style="font-size:14px">Needs attention</b>'
       '<div class="row red"><b>3</b> requests are past their due date</div>'
       '<div class="row red"><b>1</b> requests need matching to a person</div>'
       '<div class="row red"><b>2</b> grievances are past their reply date</div>'
       '<div class="row amber"><b>1</b> grievances are with the DPO</div>'
       '<div class="row amber"><b>4</b> consents are waiting for confirmation</div></div>')

DESK = {
    "w2-requests-workspace": desk(
        "<b>Staff · the Requests workspace</b> · counts only, never names. Rights requests and grievances each have "
        "three numbers; a red number needs action. <b>Requests board</b> shows requests by stage; <b>Grievance register</b> "
        "is a report of totals by what each grievance was about, for the DPO and audits. Today's <b>Needs attention</b> box links to the same lists.",
        "Requests",
        '<div class="wh">Rights / support requests</div><div class="cards">' + nc("Open Rights Requests", 7, "or")
        + nc("Overdue Requests", 3, "red") + nc("Requests To Match", 1, "red") + '</div>'
        '<div class="scs"><div class="sc">Rights requests<span style="color:#C76B00">7 open</span></div><div class="sc">Requests board<span>↗</span></div></div>'
        '<div class="wh">Grievances</div><div class="cards">' + nc("Grievances Open", 4, "or")
        + nc("Grievances With The DPO", 1, "red") + nc("Grievances Late", 2, "red") + '</div>'
        '<div class="scs"><div class="sc">Grievances<span style="color:#C76B00">4 open</span></div><div class="sc">Grievance register<span>↗</span></div></div>'
        + '<div style="max-width:520px;margin-top:8px">' + ATT + '</div>', side=SIDE),
    "w3-breach-tell": desk(
        "<b>Staff · tell people affected by a breach</b> · choose <b>who to tell</b>, fill the blanks of the approved notice in "
        "each language, check the <b>preview</b>, send a test, then <b>Send to affected people…</b>. People without a phone "
        "(or whose SMS failed) go on the <b>field visit list</b>, by ID only.",
        "Notices and Compliance / Breach Incident / BR-003",
        '<div class="ttl"><h2>BR-003</h2><span class="pill">● Notifying</span><div class="btns" style="position:relative">'
        '<span class="bt">Board told now</span><span class="bt" style="background:#E2E6E9">Tell affected people ▾</span><span class="bt dk">Save</span>'
        '<div class="menu" style="right:58px"><div class="hv">Send a test to my phone</div><div>Send to affected people…</div>'
        '<div>Download field visit list</div><div>Print notice for visits</div></div></div></div>'
        '<div class="alert"><b>41 hours left to tell the Data Protection Board (deadline 17-10-2026 15:30:00)</b></div>'
        '<div class="form"><div class="tabs"><div>Incident</div><div>72-hour steps</div><div class="on">Tell affected people</div></div>'
        '<div class="sec"><h3>Who was affected</h3><div class="cols"><div class="fl"><span class="lb">Who to tell</span>'
        '<span class="in">People whose data was on the lost phone</span><span class="desc">People whose data was on the lost phone, everyone in the programme, people with the affected uses, or a list of IDs</span></div>'
        '<div class="fl"><span class="lb">Who will be told</span><div class="big3"><div><b>38</b><span>people affected</span></div>'
        '<div><b>31</b><span>by SMS (26 own · 5 guardian’s)</span></div><div><b>7</b><span>no phone: field visit</span></div></div>'
        '<span class="desc">हिन्दी 29 · English 9. Includes people who withdrew or left: a breach notice is a legal duty, not a use of their data. '
        'A child’s or guarded adult’s message goes to the guardian.</span></div></div></div>'
        '<div class="sec"><h3>Message</h3><span class="desc">The words around these blanks are the approved breach notice (Message Template). Say only what you know; the Board report has the detail.</span>'
        '<div class="cols"><div class="fl"><span class="lb">What happened (English)</span><span class="in">a field phone with consent records was lost on 14 Oct</span>'
        '<span class="lb">What you can do (English)</span><span class="in">ignore calls asking for your code or OTP</span></div>'
        '<div class="fl"><span class="lb">What happened (Hindi)</span><span class="in">14 अक्टूबर को सहमति रिकॉर्ड वाला एक फ़ोन खो गया</span>'
        '<span class="lb">What you can do (Hindi)</span><span class="in">कोड या OTP माँगने वाले कॉल पर ध्यान न दें</span></div></div></div>'
        '<div class="sec"><h3>Preview</h3>'
        '<div><span class="desc">हिन्दी · 29 people · 4 SMS parts</span><div class="bubble">Aaroh (sample): आपकी जानकारी से जुड़ी एक घटना हुई: 14 अक्टूबर को सहमति रिकॉर्ड वाला एक फ़ोन खो गया। हमने इसे सुरक्षित किया है। आप: कोड या OTP माँगने वाले कॉल पर ध्यान न दें। मदद: 1800 000 000 (sample)। कोड AN-XXXXXX</div></div>'
        '<div><span class="desc">English · 9 people · 2 SMS parts</span><div class="bubble">Aaroh (sample): an incident affected your data: a field phone with consent records was lost on 14 Oct. We have secured it. You can: ignore calls asking for your code or OTP. Help: 1800 000 000 (sample). Ref AN-XXXXXX</div></div>'
        '<span class="desc">The code at the end is each person’s own latest receipt code, so they can quote it.</span></div>'
        '<div class="sec" style="border-bottom:0"><h3>Field visit list</h3><span class="desc">People without a phone, and anyone whose SMS failed. IDs only: field workers find each person in the app by ID.</span>'
        '<table><tr><th>Beneficiary ID</th><th>Language</th><th>Why</th><th>Told in person</th><th>Told on</th></tr>'
        '<tr><td>AC-4XK2M7PQ</td><td>hi</td><td>No phone</td><td><span class="ck on"></span></td><td>16-10-2026</td></tr>'
        '<tr><td>AC-3MN6Q2LD</td><td>hi</td><td>No phone</td><td><span class="ck"></span></td><td></td></tr>'
        '<tr><td>AC-2LK7T5WE</td><td>en</td><td>SMS failed</td><td><span class="ck"></span></td><td></td></tr></table></div></div>'),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        # CHROME = a Chromium binary to use instead of Playwright's own download (e.g. a preinstalled one).
        browser = p.chromium.launch(executable_path=os.environ.get("CHROME") or None)
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1.5)
        for name, body in SCREENS.items():
            page.set_content(f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head>'
                             f'<body><div class="phone">{body}</div></body></html>')
            page.screenshot(path=os.path.join(OUT, f"{name}.png"), clip={"x": 0, "y": 0, "width": W, "height": H})
            print("wrote", f"docs/guide/wireframes/{name}.png")
        page = browser.new_page(viewport={"width": 1280, "height": 860}, device_scale_factor=1)
        for name, body in DESK.items():
            page.set_content(f'<!doctype html><html><head><meta charset="utf-8"><style>{DESK_CSS}</style></head><body>{body}</body></html>')
            page.screenshot(path=os.path.join(OUT, f"{name}.png"), full_page=True)
            print("wrote", f"docs/guide/wireframes/{name}.png")
        browser.close()


if __name__ == "__main__":
    main()
