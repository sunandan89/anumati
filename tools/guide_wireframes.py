"""Wireframes of the field app's screens for the product guide (docs/guide/wireframes/*.png).

Each screen is a small HTML mock in the field app's look (colours from lib/core/theme.dart) with the app's
own wording, rendered to PNG. When a screen changes, update its mock here and re-run, in the same PR:
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
.bar{background:#3E6B3A;color:#F4F8EF;padding:14px 16px}.bar h1{margin:0;font-size:19px;font-weight:600}
.bar p{margin:2px 0 0;font-size:13px;color:#DDE8D3}
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
.field{display:flex;flex-direction:column;gap:2px;border-bottom:1px solid #7D6E5C;padding:4px 0 6px}
.field span{font-size:12px;color:#5C4F40}.field b{font-size:16px;font-weight:400}
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
.st.ok{background:#DDE8D3;color:#3E6B3A}.st.bad{background:#F4D6CF;color:#9E2F24}
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
.two{display:flex;gap:8px}.two span{flex:1;text-align:center;font-size:14px;padding:8px;border:1px solid #7D6E5C;border-radius:20px}
.check{display:flex;gap:10px;align-items:flex-start;padding:10px 12px;background:#FFFDF8;border:1px solid #E9DCC6;border-radius:12px;font-size:13.5px}
.box{width:18px;height:18px;border-radius:4px;border:2px solid #7D6E5C;flex-shrink:0;margin-top:1px}
.box.on{background:#3E6B3A;border-color:#3E6B3A}
.code{font-family:monospace;font-size:28px;letter-spacing:3px;text-align:center}
.otp{font-size:22px;letter-spacing:8px;text-align:center;border-bottom:1px solid #7D6E5C;padding:4px}
.out{text-align:center;font-size:14px;padding:9px;border:1px solid #7D6E5C;border-radius:20px}
.link{font-size:13px;color:#3E6B3A;font-weight:600;text-decoration:underline}
.foot{position:absolute;left:0;right:0;bottom:0;padding:10px 16px 18px;background:#F3EADB;border-top:1px solid #E9DCC6;display:flex;flex-direction:column;gap:6px}
.miss{font-size:13px;color:#9E2F24;text-align:center}
.cta{text-align:center;font-size:16px;font-weight:600;padding:13px;border-radius:24px;background:#B4532A;color:#FFF7EF}
.cta.off{background:#DDCDB3;color:#7D6E5C}
.sec{text-align:center;font-size:15px;padding:11px;border:1px solid #7D6E5C;border-radius:24px}
.big{display:flex;flex-direction:column;align-items:center;gap:4px;padding:6px 0}
.tick{width:56px;height:56px;border-radius:28px;background:#DDE8D3;color:#3E6B3A;display:flex;align-items:center;justify-content:center;font-size:28px}
"""


def bar(title, sub=""):
    return f'<div class="bar"><h1>{title}</h1>{f"<p>{sub}</p>" if sub else ""}</div>'


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
    "home": bar("Namaste, Ravi", "Village Health Camps") + """<div class="body">
<div class="card"><div class="row">3 records on this phone<span class="st">Sync</span></div><div class="muted">Sync when you have data</div></div>
<div class="muted">Programme</div><div class="card" style="flex-direction:row;justify-content:space-between"><span>Village Health Camps</span><span style="color:#B4532A;font-size:13px">Change</span></div>
<div class="tile"><span class="ic">+</span><div><div class="t">Take new consent</div><div class="d">Self, assisted or guardian</div></div></div>
<div class="tile"><span class="ic">×</span><div><div class="t">Stop or change consent</div><div class="d">Told in person, slip or letter</div></div></div>
<div class="tile"><span class="ic">↺</span><div><div class="t">Ask for one more purpose</div><div class="d">Existing beneficiary, new use</div></div></div>
<div class="tile"><span class="ic">⌕</span><div><div class="t">Find beneficiary</div><div class="d">See consent status offline</div></div></div>
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
    "a4-receipt-code": bar("Saved on this phone", "DEMO") + """<div class="body">
<div class="big"><div class="tick">✓</div><div class="t" style="font-size:20px">Saved on this phone</div><div class="muted">Signed and chained when this phone syncs</div></div>
<div class="card" style="border:1.5px solid #D9A285"><div class="muted" style="text-align:center">Consent code — write it on their slip</div><div class="code">AN-7K2Q9C</div></div>
<div class="card"><div class="row" style="font-weight:400"><span class="d">Sunita Devi (sample)</span><span>English</span></div><div class="row" style="font-weight:400"><span class="d">Granted</span><span>Health screening, Follow-up calls</span></div><div class="row" style="font-weight:400"><span class="d">Verified by</span><span>Code from the server (below)</span></div></div>
<div class="grp done"><div class="t">Confirm with a code to their phone</div><div class="muted">The code is sent by the server, not from this phone. They read it out to you.</div>
<div class="muted">Code sent to 9000012XXX. Ask them to read it out.</div><div class="otp">4 8 1 _ _ _</div><div class="link">Send a new code</div></div>
<div class="out">Send receipt by SMS</div></div>""" + foot("Done — next beneficiary"),
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
<div class="note">After Save, a code is sent to this number from the server. They read it out to confirm.</div>
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
<div class="note">After Save, a code is sent to this number from the server. They read it out to confirm.</div></div>""" + foot("Continue"),
    "d3-no-order": bar("Guardian's details", "Step 2 of 3") + """<div class="body">
<div class="muted">Guardian appointed by</div><div class="chips"><span class="chip">Local Level Committee</span><span class="chip">Court</span><span class="chip">Other authority</span><span class="chip on">No order yet</span></div>
<div class="card" style="border:2px solid #B4532A;gap:8px"><div class="t" style="color:#9E2F24;font-size:17px">Consent can't be taken yet</div>
<div>For an adult who can't decide alone, only a guardian appointed by a court or the Local Level Committee can give consent.</div>
<div>The family can apply to the Local Level Committee (National Trust) or a court. The person can still be helped today; their data just isn't recorded under consent.</div></div>
<div class="muted">Nothing is saved. Your coordinator gets a note to follow up, without the person's details.</div></div>""" + foot("Inform coordinator", second="Back"),
    "e1-about": bar("About the person", "Step 3 of 4") + """<div class="body">
<div class="field"><span>Age in years</span><b>34</b></div>
<div class="h">Gender (optional)</div><div class="chips"><span class="chip on">Female</span><span class="chip">Male</span><span class="chip">Other</span><span class="chip">Prefer not to say</span></div>
<div class="h">Occupation (optional)</div><div class="chips"><span class="chip">Farming or farm labour</span><span class="chip on">Daily wage work</span><span class="chip">Homemaker</span><span class="chip">Self-employed</span><span class="chip">Other</span></div>
<div class="note">These are listed in the notice under “What we collect”. Reports show only totals, never one person's answers.</div></div>""" + foot("Continue"),
    "f1-withdraw": bar("Stop or change consent", "Withdrawal or request") + """<div class="body">
<div class="field"><span>Receipt code, name or ID</span><b>AN-7K2Q9C</b></div>
<div class="check"><span class="box on"></span><div>They gave a paper slip or letter</div></div>
<div class="field"><span>Paper slip number (optional)</span><b>SLIP-0042</b></div>
<div class="card" style="border-color:#B4532A"><b>Sunita Devi (sample)</b><div class="muted">AC-4XK2M9PQ · AN-7K2Q9C</div></div>
<div class="row" style="font-weight:400"><span class="muted">Switch off what they no longer agree to</span><span class="link">Stop all</span></div>
<div class="p"><div><div class="t">Follow-up calls</div><div class="d" style="color:#9E2F24">Will stop</div></div><span class="sw"></span></div>
<div class="p"><div><div class="t">Photos and stories</div><div class="d">On</div></div><span class="sw on"></span></div>
<div class="p req"><div><div class="t">🔒 Health screening</div><div class="d">Needed for the programme. To stop it, they leave the programme.</div></div></div>
<div class="out" style="color:#9E2F24;border-color:#9E2F24">⎋ Leave the programme</div>
<div class="muted">Other requests: See or correct my data · Delete my data · Complaint</div></div>""" + foot("Stop 1 use for Sunita Devi (sample)"),
    "f2-leave": bar("Stop or change consent", "Withdrawal or request") + """<div class="body" style="opacity:.35">
<div class="card"><b>Sunita Devi (sample)</b><div class="muted">AC-4XK2M9PQ · AN-7K2Q9C</div></div>
<div class="p"><div><div class="t">Follow-up calls</div></div><span class="sw on"></span></div></div>
<div style="position:absolute;left:24px;right:24px;top:230px;background:#FFFDF8;border-radius:20px;padding:20px;display:flex;flex-direction:column;gap:12px;box-shadow:0 8px 30px rgba(0,0,0,.25)">
<div style="font-size:19px;font-weight:600">Leave the programme?</div>
<div style="font-size:14px">This stops every use of their data in this programme, essential ones too. The programme stops serving them. Do they still want this?</div>
<div class="row" style="justify-content:flex-end"><span class="link" style="text-decoration:none">Cancel</span><span class="cta" style="padding:9px 16px;font-size:14px">Yes, leave</span></div></div>""",
    "f3-noted": bar("Stop or change consent", "Withdrawal or request") + """<div class="body" style="opacity:.35">
<div class="card"><b>Sunita Devi (sample)</b></div></div>
<div style="position:absolute;left:24px;right:24px;top:230px;background:#FFFDF8;border-radius:20px;padding:20px;display:flex;flex-direction:column;gap:12px;box-shadow:0 8px 30px rgba(0,0,0,.25)">
<div style="font-size:19px;font-weight:600">Withdrawal noted</div>
<div style="font-size:14px">Stopped: Follow-up calls</div>
<div class="muted">It takes effect on this phone now and reaches the office on sync.</div>
<div class="row" style="justify-content:flex-end"><span class="link" style="text-decoration:none">Send by SMS</span><span class="cta" style="padding:9px 16px;font-size:14px">OK</span></div></div>""",
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
        browser.close()


if __name__ == "__main__":
    main()
