"""Upgrade check for CI: record row counts and chain verification of a site, before and after `bench
migrate`, and compare them. Works with the DocType names before and after the Anumati prefix.

    python upgrade_snapshot.py <site> <out.json>          # run from the bench directory
    python upgrade_snapshot.py --compare before.json after.json
"""

import json
import os
import subprocess
import sys

LEDGERS = ("Consent Event", "Audit Entry")
COUNTED = LEDGERS + ("Data Principal", "Guardian Link", "Consent State", "Verification Attempt", "Rights Request",
                     "Programme", "Purpose", "Notice Template", "Notice Translation", "ROPA Entry")


def sql(db, query):
	out = subprocess.check_output(["mysql", "-h", "127.0.0.1", "-uroot", "-proot", "-N", "-B", db, "-e", query])
	return [line.split("\t") for line in out.decode().splitlines() if line]


def snapshot(site, path):
	db = json.load(open(os.path.join("sites", site, "site_config.json")))["db_name"]
	tables = {row[0] for row in sql(db, "show tables")}
	counts, names = {}, {}
	for short in COUNTED:
		for name in ("Anumati " + short, short):
			if "tab" + name in tables:
				counts[short] = int(sql(db, f"select count(*) from `tab{name}`")[0][0])
				names[short] = name
				break
	verify = {}
	for short in LEDGERS:
		out = subprocess.check_output(
			["bench", "--site", site, "execute", "anumati.ledger.chain.verify_chain", "--args", json.dumps([names[short]])]
		).decode()
		line = next(l for l in reversed(out.splitlines()) if l.strip().startswith("{"))
		verify[short] = json.loads(line)
	json.dump({"counts": counts, "names": names, "verify": verify}, open(path, "w"), indent=1)
	print(json.dumps({"counts": counts, "verify": {k: v["ok"] for k, v in verify.items()}}))


def compare(before_path, after_path):
	before, after = json.load(open(before_path)), json.load(open(after_path))
	problems = []
	for short, n in before["counts"].items():
		if after["counts"].get(short) != n:
			problems.append(f"{short}: {n} rows before, {after['counts'].get(short)} after")
	for short in LEDGERS:
		if not before["counts"].get(short):
			problems.append(f"{short}: no rows to test with")
		for label, snap in (("before", before), ("after", after)):
			if not snap["verify"][short]["ok"]:
				problems.append(f"{short} chain broken {label}: {snap['verify'][short]['error']}")
		if after["verify"][short]["checked"] != before["verify"][short]["checked"]:
			problems.append(f"{short}: verified {before['verify'][short]['checked']} rows before, "
			                f"{after['verify'][short]['checked']} after")
	for short, name in after["names"].items():
		if not name.startswith("Anumati "):
			problems.append(f"{short} was not renamed")
	print(json.dumps({"before": before["counts"], "after": after["counts"]}, indent=1))
	if problems:
		print("\n".join(problems))
		sys.exit(1)
	print("Upgrade kept every row and both chains verify.")


if __name__ == "__main__":
	if sys.argv[1] == "--compare":
		compare(sys.argv[2], sys.argv[3])
	else:
		snapshot(sys.argv[1], sys.argv[2])
