"""CI gate: hash-chain tamper detection, and key rotation keeps old signatures valid."""

import frappe
from frappe.tests.utils import FrappeTestCase

from anumati.ledger import chain, keystore
from anumati.tests.utils import make_event, make_programme

SAVEPOINT = "anumati_chain_test"


class TestChain(FrappeTestCase):
	def setUp(self):
		self.events = [make_event() for _ in range(3)]
		frappe.db.savepoint(SAVEPOINT)

	def tearDown(self):
		frappe.db.rollback(save_point=SAVEPOINT)
		keystore.clear_cache()

	def assertBrokenAt(self, result, name, reason_part):
		self.assertFalse(result["ok"])
		self.assertEqual(result["error"]["name"], name)
		self.assertIn(reason_part, result["error"]["reason"])

	def test_untouched_chain_verifies(self):
		result = chain.verify_chain("Consent Event")
		self.assertTrue(result["ok"], result["error"])
		self.assertGreaterEqual(result["checked"], 3)
		self.assertEqual(result["head_hash"], self.events[-1].hash)

	def test_links_follow_each_other(self):
		for prev, cur in zip(self.events, self.events[1:]):
			self.assertEqual(cur.prev_hash, prev.hash)
			self.assertEqual(cur.chain_seq, prev.chain_seq + 1)

	def test_editing_a_field_in_the_database_is_detected(self):
		target = self.events[1].name
		frappe.db.sql(
			"update `tabConsent Event` set purposes_granted=%s where name=%s", ('["screen","research"]', target)
		)
		self.assertBrokenAt(chain.verify_chain("Consent Event"), target, "hash mismatch")

	def test_rehashing_a_row_breaks_the_next_link(self):
		target, following = self.events[1].name, self.events[2].name
		frappe.db.sql("update `tabConsent Event` set hash=%s where name=%s", ("f" * 64, target))
		result = chain.verify_chain("Consent Event")
		self.assertFalse(result["ok"])
		self.assertIn(result["error"]["name"], (target, following))

	def test_forged_signature_is_detected(self):
		target = self.events[0].name
		other = self.events[2].signature
		frappe.db.sql("update `tabConsent Event` set signature=%s where name=%s", (other, target))
		self.assertBrokenAt(chain.verify_chain("Consent Event"), target, "signature invalid")

	def test_deleting_a_row_in_the_database_is_detected(self):
		frappe.db.sql("delete from `tabConsent Event` where name=%s", self.events[1].name)
		self.assertBrokenAt(chain.verify_chain("Consent Event"), self.events[2].name, "sequence gap")

	def test_truncating_the_chain_is_detected_against_a_checkpoint(self):
		head = chain.verify_chain("Consent Event")
		anchor = {"seq": head["head_seq"], "hash": head["head_hash"]}
		frappe.db.sql("delete from `tabConsent Event` where name=%s", self.events[-1].name)
		result = chain.verify_chain("Consent Event", anchor=anchor)
		self.assertFalse(result["ok"])
		self.assertIn("truncated", result["error"]["reason"])

	def test_key_rotation_keeps_old_signatures_valid(self):
		old_key = self.events[-1].key_id
		new_key = keystore.rotate()
		self.assertNotEqual(old_key, new_key)
		after = make_event()
		self.assertEqual(after.key_id, new_key)
		result = chain.verify_chain("Consent Event")
		self.assertTrue(result["ok"], result["error"])

	def test_admin_changes_are_sealed_and_tamper_evident(self):
		programme = frappe.get_doc("Programme", make_programme())
		programme.status = "Paused"
		programme.save()
		self.assertGreaterEqual(chain.seal_audit_trail(), 1)
		self.assertTrue(chain.verify_chain("Audit Entry")["ok"])
		entry = frappe.db.get_value("Audit Entry", {"ref_doctype": "Programme", "action": "update"}, "name")
		self.assertTrue(entry)
		remarks = frappe.db.get_value("Audit Entry", entry, "remarks")
		self.assertNotIn("Paused", remarks or "", "audit entries carry hashes and field names, not values")
		frappe.db.sql("update `tabAudit Entry` set actor='Guest' where name=%s", entry)
		self.assertBrokenAt(chain.verify_chain("Audit Entry"), entry, "hash mismatch")

	def test_sealing_is_idempotent(self):
		programme = frappe.get_doc("Programme", make_programme())
		programme.status = "Live"
		programme.save()
		chain.seal_audit_trail()
		self.assertEqual(chain.seal_audit_trail(), 0)
