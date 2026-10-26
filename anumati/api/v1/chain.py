"""Chain verification for DPOs and auditors. /api/v2/method/anumati.api.v1.chain.verify"""

import frappe
from frappe import _

from anumati.ledger import chain

ALLOWED = ("Anumati DPO", "Anumati Admin", "System Manager")


# The ledgers' names before every DocType took the Anumati prefix, still accepted from older callers.
OLD_NAMES = {"Consent Event": "Anumati Consent Event", "Audit Entry": "Anumati Audit Entry"}


@frappe.whitelist(methods=["GET", "POST"])
def verify(ledger: str = "Anumati Consent Event"):
	frappe.only_for(ALLOWED)
	ledger = OLD_NAMES.get(ledger, ledger)
	if ledger not in chain.CHAINS:
		frappe.throw(_("ledger must be Anumati Consent Event or Anumati Audit Entry"))
	return chain.verify_chain(ledger)
