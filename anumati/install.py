import frappe

from anumati.ledger import keystore


def after_install():
	# Tenant setup: each site gets its own Ed25519 signing key and phone-hash salt.
	keystore.ensure_keys()
	# Spec section 9 / v0.4: 2FA for anyone with PII access. Which roles need it is set on the Role
	# fixtures (two_factor_auth); this switches the stock feature on.
	frappe.db.set_single_value("System Settings", "enable_two_factor_auth", 1)


def after_migrate():
	keystore.ensure_keys()
