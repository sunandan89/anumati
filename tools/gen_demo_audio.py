"""Record the fictional demo notices once, here, so demo sites need no Sarvam call.

Builds each demo notice's recording text exactly as anumati.voice.notice_script does on a site (same
compose_script), records it in the woman's and man's default voices, and writes
anumati/public/demo_audio/*.mp3 plus manifest.json (keyed by a hash of the text). A demo site attaches
a bundled file only when its own notice text hashes the same, so edited notices are never mismatched.

Run from the repo root with SARVAM_API_KEY in the environment or .env:
    python3 tools/gen_demo_audio.py
Only notice text is sent to Sarvam. Existing files are reused; nothing is re-recorded needlessly."""
import base64, importlib.util, json, os, sys, types

import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "anumati", "public", "demo_audio")
VOICES = {"female": "kavya", "male": "rahul"}
PACE = 0.9


def _stub_frappe():
    """demo.py and voice.py import Frappe; only their constants and pure helpers are used here."""
    f = types.ModuleType("frappe")
    f._ = lambda s: s
    f.whitelist = lambda **k: (lambda fn: fn)
    f.ValidationError = Exception
    utils = types.ModuleType("frappe.utils")
    utils.cint, utils.flt, utils.strip_html = int, float, lambda s: s
    model = types.ModuleType("frappe.model")
    workflow = types.ModuleType("frappe.model.workflow")
    workflow.apply_workflow = None
    for name, mod in {"frappe": f, "frappe.utils": utils, "frappe.model": model, "frappe.model.workflow": workflow}.items():
        sys.modules[name] = mod


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, "anumati", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _key():
    key = os.environ.get("SARVAM_API_KEY")
    env = os.path.join(REPO, ".env")
    if not key and os.path.exists(env):
        for line in open(env):
            name, _, value = line.strip().partition("=")
            if name == "SARVAM_API_KEY":
                key = value.strip()
    if not key:
        raise SystemExit("SARVAM_API_KEY is not set.")
    return key


def scripts(demo, voice):
    """(programme code, language) -> recording text, for every demo notice and its Hindi translation."""
    out = {}
    rule3 = [demo.RULE3[k] for k in voice.RULE3]
    for spec in demo.PROGRAMMES:
        purposes = [(title, description, essential) for _c, title, description, essential, _m in spec["purposes"]]
        out[(spec["code"], "en")] = voice.compose_script(spec["summary"], spec["full_text"], purposes, rule3)
        hindi = {**demo.HINDI, **spec["hindi"]}
        out[(spec["code"], "hi")] = voice.compose_script(
            hindi["summary"], hindi["full_text"], [], [hindi.get(k) or demo.RULE3[k] for k in voice.RULE3])
    return out


def record(key, text, language, speaker, voice):
    audio = b""
    for part in voice.chunks(text):
        r = requests.post("https://api.sarvam.ai/text-to-speech", headers={"api-subscription-key": key}, timeout=120,
                          json={"text": part, "language_code": voice.LANGUAGES[language], "model": voice.TTS_MODEL,
                                "output_audio_codec": "mp3", "speaker": speaker, "pace": PACE})
        r.raise_for_status()
        audio += base64.b64decode(r.json()["audios"][0])
    return audio


if __name__ == "__main__":
    _stub_frappe()
    voice, demo = _load("voice"), _load("demo")
    os.makedirs(OUT, exist_ok=True)
    manifest, key = {}, None
    for (code, language), text in scripts(demo, voice).items():
        digest = voice.script_hash(text)
        entry = {"programme": code, "language": language}
        for gender, speaker in VOICES.items():
            name = f"{code}-{language}-{speaker}.mp3"
            path = os.path.join(OUT, name)
            old = json.load(open(os.path.join(OUT, "manifest.json"))).get(digest, {}) if os.path.exists(os.path.join(OUT, "manifest.json")) else {}
            if not (os.path.exists(path) and old.get(gender) == name):
                key = key or _key()
                open(path, "wb").write(record(key, text, language, speaker, voice))
                print("recorded", name, os.path.getsize(path) // 1024, "KB")
            entry[gender] = name
        manifest[digest] = entry
    with open(os.path.join(OUT, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(len(manifest), "notices,", 2 * len(manifest), "clips")
