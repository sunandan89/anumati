"""Chain verification for DPOs and auditors. /api/v2/method/anumati.api.v1.chain.verify"""

import frappe

from anumati.ledger import chain

ALLOWED = ("Anumati DPO", "Anumati Admin", "System Manager")


@frappe.whitelist(methods=["GET", "POST"])
def verify(ledger: str = "Consent Event"):
	frappe.only_for(ALLOWED)
	if ledger not in chain.CHAINS:
		frappe.throw("ledger must be Consent Event or Audit Entry")
	return chain.verify_chain(ledger)
