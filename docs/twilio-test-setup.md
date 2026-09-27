# Testing withdrawal on WhatsApp and voice with a Twilio trial

For testing only: the Twilio sandbox is hosted outside India, so use your own phone and fictional data, never real beneficiaries. For the pilot, use an India-hosted provider (MSG91 or Exotel).

## 1. Twilio console (once)
1. **Phone Numbers › Manage › Verified Caller IDs:** add your own mobile number.
2. **Messaging › Try it out › Send a WhatsApp message:** from your WhatsApp, send the join code shown (e.g. `join given-hunter`) to **+1 415 523 8886**. The sandbox connection lasts 72 hours; send the code again if it expires.
3. **Voice (optional):** **Phone Numbers › Buy a number** (the trial pays for one US number). Note it. Calling a US number from India is an international call on your phone bill.
4. Note the **Account SID** and **Auth Token** from the console home. Don't paste them into chat or email.

## 2. Anumati site (Desk)
Deploy this branch to your Frappe Cloud site first. Then:

1. **Channel Provider › New** (one for WhatsApp; add a second one for voice if you want it):

| Field | WhatsApp | Voice |
|---|---|---|
| Name | `twilio-whatsapp` (no spaces) | `twilio-voice` |
| Type | WhatsApp | IVR |
| Provider | Twilio | Twilio |
| Sender ID | `+14155238886` | your Twilio number |
| API key | Account SID | Account SID |
| API secret | Auth Token | Auth Token |
| Inbound webhook secret | any long random string you make up | another one |

2. **Test data:** a Programme with two or three Purposes (one essential), a **Data Principal** with your mobile number and preferred language English, and one consent for them. Use the field app, or `consent.record` from the API.
3. **Message Template** (optional, for receipts and confirmations): event `receipt` or `rights_update`, channel `whatsapp` or `sms`, language `en`, **Approved** ticked. WhatsApp uses the SMS wording if there is no WhatsApp template.

## 3. Webhooks in the Twilio console
Replace `<site>` with your site and `<secret>` with the inbound webhook secret you set above.

- **WhatsApp sandbox settings › When a message comes in** (HTTP POST):
  `https://<site>/api/method/anumati.api.v1.channel.inbound_whatsapp?provider=twilio-whatsapp&token=<secret>`
- **Your Twilio number › Voice configuration › A call comes in** (Webhook, HTTP POST):
  `https://<site>/api/method/anumati.api.v1.channel.ivr?provider=twilio-voice&token=<secret>`

Anumati checks both the secret in the URL and Twilio's signature (`X-Twilio-Signature`, made with your Auth Token). A request missing either gets 403.

## 4. What to try
**WhatsApp:** send `STOP` to the sandbox number.
- You get a menu: `1` stop every optional use, `2…` stop one purpose, `E` delete my data, `D` send me what you hold.
- Reply `2`. You should get "Done…" with a receipt code.
- In Desk you should see: the Rights Request under **Rights Request** (channel whatsapp, Closed, with the conversation on its timeline); a new signed **Consent Event** (action withdraw); **Consent State** for that purpose showing *withdrawn*; and `consent.check` for that purpose now returning `allow: false`.
- If two test principals share your number, the menu first asks "who is this for?" and lists them by receipt code, never by name.
- `E` opens an erasure request in the inbox for staff to start.

**Voice:** call your Twilio number. The trial message plays first; press any key. Then press `1` to stop every optional use, `7` to delete, `8` to ask for your data.

## Trial limits
- Messages and calls only reach verified numbers.
- The WhatsApp sandbox allows free-text replies only within 24 hours of your last message to it, which covers the STOP menu.
- The trial credit is about $15 and lasts 30 days.
