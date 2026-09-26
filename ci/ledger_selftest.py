"""Frappe-free checks of the ledger primitives: canonical JSON, hashing, Ed25519. Runs in seconds."""

from datetime import datetime

from anumati.ledger import signing
from anumati.ledger.canonical import GENESIS_HASH, canonical_json, compute_hash, normalise, payload, to_storage

schema = {"a": "str", "n": "int", "t": "datetime", "j": "json"}
row_from_client = {"a": "x", "n": "3", "t": "2026-09-20 11:20:00", "j": ["b", "a"]}
row_from_db = {"a": "x", "n": 3, "t": datetime(2026, 9, 20, 11, 20), "j": '["b","a"]'}

p1, p2 = payload(schema, row_from_client.get), payload(schema, row_from_db.get)
assert p1 == p2, (p1, p2)
assert canonical_json({"b": 1, "a": "अ"}) == '{"a":"अ","b":1}'.encode()
assert normalise("", "str") is None and normalise(None, "int") == 0
assert to_storage(["b", "a"], "json") == '["b","a"]'

h1 = compute_hash(p1, GENESIS_HASH)
h2 = compute_hash(p1, h1)
assert h1 != h2 and len(h1) == 64
assert compute_hash({**p1, "a": "y"}, GENESIS_HASH) != h1

priv, pub, kid = signing.generate_keypair()
sig = signing.sign(priv, h1)
assert signing.verify(pub, h1, sig)
assert not signing.verify(pub, h2, sig)
assert not signing.verify(signing.generate_keypair()[1], h1, sig)
assert not signing.verify(pub, h1, "not-base64!")
assert kid == signing.key_id_for(pub) and len(kid) == 16

try:
	normalise("2026-09-20T11:20:00+05:30", "datetime")
	raise AssertionError("aware datetimes must be rejected")
except ValueError:
	pass

print("ledger self-test ok")
