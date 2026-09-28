# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate

from anumati import inbox


TITLES = {"withdrawal": "Withdrawal", "access": "Data access request", "correction": "Correction request",
          "erasure": "Erasure request", "grievance": "Grievance", "nomination": "Nomination"}
CHANNELS = {"field_worker": "field worker", "slip": "paper slip", "sms": "SMS", "missed_call": "missed call",
            "ivr": "phone (IVR)", "whatsapp": "WhatsApp", "web": "website", "email": "email",
            "community": "community meeting", "api": "connected system", "ussd": "USSD"}


class RightsRequest(Document):
	def validate(self):
		# SLA clock starts at receipt, not at match (spec section 6).
		if not self.sla_due:
			days = frappe.db.get_single_value("Anumati Settings", "rights_sla_days") or 30
			self.sla_due = add_days(getdate(self.received_on), days)
		inbox.match(self)
		# Board cards and lists show the subject; SMS and missed calls arrive without one.
		if not self.subject:
			self.subject = TITLES.get(self.request_type, "Request") + " by " + CHANNELS.get(self.channel, self.channel or "")
