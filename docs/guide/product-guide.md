# Anumati product guide

Anumati helps NGOs take, prove and honour consent under India's DPDP Act 2023, including in the field: offline, in Hindi or English, and for people who can't read or have no phone. **Phase 1 is built** and ready for a pilot of about 500 real consents. Phases 2 and 3 are planned.

> This guide lives in the `anumati` repository (`docs/guide/`). Every pull request that changes behaviour updates it, so the published copy always matches what is merged.

## Contents

1. [The three parts](#the-three-parts)
2. [Who uses it](#who-uses-it)
3. [What Phase 1 gives each person](#what-phase-1-gives-each-person)
4. [Taking consent in the field](#taking-consent-in-the-field)
5. [Screens, journey by journey](#screens-journey-by-journey)
6. [After consent](#after-consent)
7. [Web console journeys](#web-console-journeys)
8. [Roadmap: Phase 2 and Phase 3](#roadmap-phase-2-and-phase-3)
9. [Setup still needed](#setup-still-needed)
10. [Glossary](#glossary)

## The three parts

| Part | Who uses it | What it does |
| --- | --- | --- |
| **Anumati Collect** (Android app) | Field workers | Plays the notice, records choices and proof, works offline, syncs later |
| **Web console** (Frappe Desk) | Programme managers, DPO, operators, admins | Programmes, notices, beneficiaries, requests inbox, reports, settings |
| **APIs** | Connected systems (MIS, CRM) | Record consent, check consent before using data, add or update beneficiaries |

```mermaid
flowchart LR
  FW["Field worker<br/>Anumati Collect app"] -- "consents sync when online" --> S["Anumati server<br/>signed, chained ledger"]
  S -- "programmes, notices, people" --> FW
  S --- C["Web console<br/>staff and DPO"]
  H["Connected system<br/>MIS / CRM"] -- "check before using data" --> S
  S -- "SMS: codes, receipts" --> P["Person's or guardian's phone"]
  P -- "STOP / missed call" --> S
```

Every consent is signed and chained, so any later change shows up. Names, phone numbers and evidence (voice, photos) are stored encrypted, and phone numbers are looked up by a salted hash, never in plain text.

## Who uses it

| Persona | Where | Main jobs |
| --- | --- | --- |
| **Field worker** | App | Take consent, log a withdrawal or request, add a use later, find a person, sync |
| **Beneficiary** (the person) | In person, SMS | Hear the notice, choose each use, read back a code, withdraw any time |
| **Parent or guardian** | In person, SMS | Consent for a child under 18, or for an adult who can't decide alone |
| **Programme manager** | Web console | Set up programmes, choose extra questions, watch the dashboards, get coordinator alerts |
| **DPO** (Data Protection Officer) | Web console | Publish notices, approve translations and audio, work the requests inbox, verify the chain |
| **Operator** | Web console | Work the requests inbox, match requests to people |
| **Admin** | Web console | Settings, users and roles, SMS account, field phones |
| **Connected system** | API | Ask "may I use this person's data for this purpose?" before using it |

Each role sees only its own menus. A field worker can't open the web console at all; they work only in the app.

## What Phase 1 gives each person

### Field worker (Anumati Collect)

| Feature | What it means on the ground |
| --- | --- |
| Sign in with organisation address, user and password | One-time set-up per phone; then a PIN locks the app |
| Choose programme | Village Health Camps, After-school Learning Centres, Women's Self-Help Groups in the demo |
| **Take new consent** in 3 screens | Who is consenting → notice and choices → confirm and save (guardians: who → guardian → notice and save). A programme with extra questions adds **About the person** as a 4th screen (Village Health Camps asks Age), where guardians then save |
| Notice in Hindi or English | A reviewed recording (natural voice by Sarvam AI, woman's or man's voice to match the worker), or the phone's own voice; with neither, the worker reads it aloud and taps "I have read the whole notice to them". Choices unlock only after that |
| Uses in the person's language | Use names show in Hindi when the notice is in Hindi |
| Uses that need a phone hidden | For someone without a phone, uses like "follow-up calls" are not offered |
| Proof that fits the person | SMS code, voice "haan", signature or thumbprint photo, witness: see the [proof table](#proof-and-witness) |
| Guardian journeys | Parent for a child; guardian with an appointment order for an adult who can't decide alone |
| "No order yet" stop | Nothing is saved; the coordinator is told, without the person's details |
| Extra questions | "About the person" screen, only when the programme switches questions on |
| Receipt code | A code like `AN-7K2Q9C` to write on the slip; optional SMS receipt from the worker's phone |
| Server-sent code | After Save, online: the server texts a code to the person's phone; the worker never sees it |
| **Log withdrawal or request** | In person, paper slip or letter: stop all optional uses, stop one use, see or correct data, delete data, complaint |
| **Ask for one more purpose** | A later visit: only the new use is asked; past choices are not asked again |
| **Find beneficiary** | Offline search by name or ID (and by receipt code for consents taken on this phone); shows each use's status; tapping a person opens the withdrawal screen |
| Offline first | Everything is saved on the phone (encrypted) and syncs when online; no duplicates even if sync is cut off |
| App lock and lost phone | The app locks after 5 minutes away or on restart; 5 wrong PINs sign out and wipe the phone's data. An admin or programme manager can mark a phone lost; it wipes itself on its next contact |

### Beneficiary and guardian

- Hears the whole notice before choosing; every optional use starts **off**; "Yes to all" and "No to all" carry equal weight.
- Gets a receipt code and can withdraw any time: tell any field worker, show the paper slip, or (once an inbound number is set up) SMS `STOP <code>` or give a missed call.
- A child's guardian gets the messages. `STOP <code>` from the guardian's phone withdraws that consent; a plain `STOP` or a missed call from it goes to the inbox for staff to match, because it could mean the guardian or the child.

### Programme manager, DPO, operator, admin (web console)

| Area | Phase 1 features |
| --- | --- |
| **Today** dashboard | Consent records in the last 30 days, confirmed uses, evidence-only uses, records waiting to sync on phones, withdrawals, open requests, "Needs attention" list (overdue requests, chain check) |
| **Beneficiaries** | Search by whole-word name, full phone number, receipt code or ID (names stored encrypted; the list shows names and masked phones, and every view is logged); consent history per person; guardians; "Turned 18: renew consent" list |
| **Programmes** | Purposes (with "allowed for children" and "needs a phone"), verification methods, **How SMS codes are sent**, extra questions, field phones. (The capture-mode and withdrawal-channel lists on the form are not used yet) |
| **Notices and compliance** | Notice versions with a publishing workflow, Rule 3 checklist, translations with reviewer sign-off, audio approval, records of processing (ROPA), breach log, audit log |
| **Requests inbox** | Every withdrawal or rights request with a due date (30 days by default; overdue shown in red in the list), a board view, **Record withdrawal** (pick the programme, optionally the uses); staff are notified of new requests and 3 days before the due date |
| **Analytics** | Consents per week, by purpose, by capture mode, by how the notice was given, by language, by worker |
| **Extra questions** | A library of 20 questions (sensitive ones flagged); totals-only report (counts under 5 hidden) |
| **Access logs** | Every view of a name, phone or evidence file is logged |
| **Setup** | Organisation, DPO, languages, signing key, Sarvam voice, SMS account, onboarding checklist |

### Connected systems (API)

| API | Purpose |
| --- | --- |
| `consent.check` | Allow or deny one purpose for one person, from cache in milliseconds |
| `consent.record`, `consent.withdraw`, `consent.state` | Record and read consent from another system |
| `principal.upsert` | Add or update a person (with extra-question answers and year of birth) |
| `notice.get_active` | The live notice, its translations and extra questions |
| `notifications.feed` | A polling feed of consent and request events |
| `consent.verify`, `consent.public_keys` | Anyone can verify a receipt's signature without seeing personal data |

Full details: [`docs/api.md`](https://github.com/sunandan89/anumati/blob/main/docs/api.md) and `anumati/public/openapi.json`.

## Taking consent in the field

### Who is consenting decides the journey

Screen 1 asks **who is giving consent** first. Everything else follows from that answer.

```mermaid
flowchart TD
  A["Take new consent"] --> Q{"Who is giving consent?"}
  Q -- "The person,<br/>for themself" --> S1["Name, phone yes/no,<br/>can read?, language"]
  Q -- "A parent, for a<br/>child under 18" --> C1["Child's name,<br/>year of birth, language"]
  Q -- "A guardian, for an adult<br/>who can't decide alone" --> G1["Person's name,<br/>language"]
  S1 --> N["Notice and choices"]
  N --> CF["Confirm and save<br/>proof, witness if needed"]
  C1 --> CG["Parent's details<br/>Mother / Father / Other"]
  G1 --> GG["Guardian's details<br/>appointed by, order no."]
  CG --> NG["Notice and choices<br/>declaration, Save"]
  GG --> NG
  GG -- "No order yet" --> STOP["Stop: nothing saved,<br/>coordinator told"]
  CF --> R["Receipt code"]
  NG --> R
```

If the programme has switched on extra questions, an **About the person** screen appears after the choices.

### The four journeys

| Journey | Screens | Proof | Witness |
| --- | --- | --- | --- |
| **A. Reads, has a phone** | Who → Notice and choices → Confirm | SMS code (from the server, or the worker's phone plus voice "haan") | No |
| **B. Needs help reading, or no phone** | Who → Notice and choices → Confirm | Voice "haan" or thumbprint / signature photo (at least one) | Yes, if the notice was read to them |
| **C. Parent for a child** | Who → Parent's details → Notice, choices and Save | SMS code to the parent; ID photo required only if no mobile is given | No |
| **D. Guardian for an adult who can't decide alone** | Who → Guardian's details → Notice, choices and Save | Order number (required), SMS code to the guardian; order photo optional; ID photo required only if no mobile is given | No |

### Proof and witness

| Reads the notice? | Has a phone? | Proof | Witness |
| --- | --- | --- | --- |
| Yes | Yes | SMS code | No |
| Yes | No | Voice "haan" **or** photo of signature / thumbprint | No |
| Needs help | Yes | SMS code **and** voice "haan" or thumbprint | Yes (name required, relation optional) |
| Needs help | No | Voice "haan" or thumbprint | Yes |
| Parent or guardian | Guardian's phone | SMS code to the guardian | No |
| Parent or guardian | No phone | Photo of the guardian's ID | No |

When the code goes from the **worker's phone** (no internet, SMS not set up yet, or the programme's choice), the person's or guardian's **voice "haan" is always required** with it, because the worker sees that code. Codes from the server are **confirmed** when they match; worker's-phone codes stay **recorded**.

A witness is asked only when someone else read the notice to the person, because an independent person then confirms it was read fairly.

### How the SMS code is sent

One programme setting, **How SMS codes are sent**, decides the route. The app also checks for internet by itself; the worker never chooses.

```mermaid
flowchart TD
  P{"Programme setting"} -- "MSG91 when online" --> I{"Internet on the<br/>worker's phone?"}
  P -- "Worker's phone" --> W
  I -- "Yes" --> SV["After Save: tap Send code<br/>Server texts it via MSG91<br/>Person reads it out: confirmed"]
  I -- "No" --> W["Before Save: code from the<br/>worker's phone + voice 'haan'<br/>both required: recorded"]
  W -. "Can't get the code now?" .-> L["Confirm later by SMS<br/>(voice still required)"]
```

| | MSG91 (server) | Worker's phone |
| --- | --- | --- |
| Needs internet | Yes, on the worker's phone | No, only mobile signal |
| Cost | About ₹0.2 per SMS | Free |
| Worker sees the code | Never | Yes, so a voice "haan" is always required with it |
| Status | **Confirmed** when the code matches | **Recorded** (the voice is the strong proof) |

### Adult who can't decide alone, with no appointment order

```mermaid
flowchart LR
  A["Guardian appointed by"] --> B{"Order?"}
  B -- "Local Level Committee / Court /<br/>Other authority" --> C["Order number (required)<br/>→ continue"]
  B -- "No order yet" --> D["Consent can't be taken.<br/>Nothing is saved."]
  D --> E["Inform coordinator<br/>(no personal details)"]
```

A person with a disability who **can** decide with support consents for themself (journey B).

### Children and turning 18

- A child's consent is never used before it is confirmed (a server code that matched, a delivered confirm-later SMS, or evidence only). Connected systems asking `consent.check` get "awaiting confirmation" until then.

- Purposes marked "not allowed for children" (for example anonymised research) are never offered for a child.
- The child's **year of birth** is recorded. The server works out when they turn 18 (31 December of the year they turn 18); a daily job flags them, and their guardian's consent stops counting ("renewal due") until they consent themselves. The field action for this renewal is in Phase 2.

## Screens, journey by journey

Wireframes of the field app with its own wording (fictional names). They are drawn to match the built screens (not screenshots) and regenerated with `tools/guide_wireframes.py` whenever a screen changes. Step labels show "of 3"; in a programme with extra questions (like Village Health Camps) they show "of 4", and guardians save on the About the person screen.

### Home

| Home |
| --- |
| <img src="wireframes/home.png" width="200" alt="Home: records waiting to sync, programme, four actions"> |

### Journey A: the person reads and has a phone

| 1. Who is giving consent? | 2. Notice and choices | 3. Confirm and save (online) | After Save: code from the server |
| --- | --- | --- | --- |
| <img src="wireframes/a1-who.png" width="200" alt="Screen 1 for the person themself"> | <img src="wireframes/a2-notice.png" width="200" alt="Notice and choices, choices unlocked"> | <img src="wireframes/a3-confirm-online.png" width="200" alt="Confirm: tick and Save"> | <img src="wireframes/a4-receipt-code.png" width="200" alt="Receipt with the server-sent code panel"> |

No internet, or the programme set to "Worker's phone": the Confirm screen asks for the code from the worker's phone **and** the voice "haan" before Save.

| 3. Confirm and save (offline / worker's phone) |
| --- |
| <img src="wireframes/a5-confirm-offline.png" width="200" alt="Confirm offline: SMS code from the worker's phone plus voice, both needed"> |

### Journey B: needs help reading, or no phone

| 1. Who (needs help, no phone, Hindi) | 2. Notice in Hindi | 3. Confirm with witness | Reads but no phone |
| --- | --- | --- | --- |
| <img src="wireframes/b1-who-help.png" width="200" alt="Screen 1, needs help and no phone"> | <img src="wireframes/b2-notice-hindi.png" width="200" alt="Hindi notice with Hindi use names; follow-up calls hidden"> | <img src="wireframes/b3-confirm-witness.png" width="200" alt="Voice saved, witness name"> | <img src="wireframes/b4-reads-no-phone.png" width="200" alt="Voice or signature photo, no witness"> |

### Journey C: parent for a child

| 1. Who (child) | 2. Parent's details | 2. Parent's details (offline) | 3. Notice, choices and Save |
| --- | --- | --- | --- |
| <img src="wireframes/c1-who-child.png" width="200" alt="Child's name and year of birth"> | <img src="wireframes/c2-parent.png" width="200" alt="Mother, Father or Other guardian; code after Save"> | <img src="wireframes/c4-parent-offline.png" width="200" alt="Code from the worker's phone plus the parent's voice"> | <img src="wireframes/c3-notice-save.png" width="200" alt="Guardian saves on the notice screen; research not offered"> |

### Journey D: guardian for an adult who can't decide alone

| 2. Guardian's details | No order yet |
| --- | --- |
| <img src="wireframes/d2-guardian.png" width="200" alt="Appointed by, order number, relation, guardian"> | <img src="wireframes/d3-no-order.png" width="200" alt="Consent can't be taken; inform coordinator"> |

### Extra questions and withdrawal

| About the person | Log withdrawal or request |
| --- | --- |
| <img src="wireframes/e1-about.png" width="200" alt="Extra questions after the choices"> | <img src="wireframes/f1-withdraw.png" width="200" alt="How it arrived, find the person, what they want"> |

## After consent

### Receipt and confirmation

1. The app shows the receipt code to write on the slip.
2. With the MSG91 route online, the worker taps **Send code**; the code goes to the person's (or guardian's) phone; they read it out; the consent becomes **confirmed**.
3. Optional: **Send receipt by SMS** opens the worker's SMS app with the receipt text.
4. With SMS set up and **Send SMS receipts** on (the default), the server also texts a receipt, a withdrawal confirmation, or for **confirm later** a message that confirms the consent once it is delivered. Not delivered within 7 days (programme setting) → the consent shows as unconfirmed under **Waiting for confirmation**.

### Sync

```mermaid
flowchart LR
  A["Saved on the phone<br/>(encrypted outbox)"] -- "online" --> B["Person added or updated"]
  B --> C["Evidence uploaded<br/>(encrypted on the server)"]
  C --> D["Guardian and link<br/>(if any)"]
  D --> E["Consent recorded:<br/>signed and chained"]
  E --> F["Receipt / SMS"]
  A -- "server refuses" --> X["Sync issues list:<br/>try again or discard"]
```

Each step can be repeated safely: a sync cut off halfway resumes without duplicates.

### Withdrawal and requests

| How it arrives | Phase 1 | What happens |
| --- | --- | --- |
| Told to a field worker | Yes | "Log withdrawal or request" on the phone; a withdrawal takes effect on the phone at once |
| Paper slip or letter | Yes | Same screen, with the slip number |
| SMS `STOP` / `STOP <code>` / `STOP <n>` | Built; needs an inbound number | Withdraws all optional uses, that consent, or use number n; ambiguous ones go to the inbox. `DATA` opens an access request; anything else a complaint |
| Missed call | Built; needs a missed-call number | Opens a withdrawal request in the inbox |
| Staff in the web console | Yes | "Record withdrawal" on the request (choose the programme): one signed withdrawal, request closed |

```mermaid
flowchart LR
  A["Request arrives"] --> B{"Matched to<br/>a person?"}
  B -- "Yes" --> C["Inbox: open, due in 30 days"]
  B -- "No" --> U["Staff set the person<br/>(Who is this for? when<br/>the number is shared)"]
  U --> C
  C -- "withdrawal" --> W["Record withdrawal<br/>(signed) → closed"]
  C -- "access / correction / erasure /<br/>complaint" --> M["Staff act and close<br/>(automation: Phase 2)"]
```

### Add a use later

When a programme adds a new use, the worker opens **Ask for one more purpose**, picks the person, reads only the new part of the notice, and records Yes or No. Past decisions are shown and not asked again. With a phone, the code follows the same routes (server code after Save, or the worker's phone plus voice); with no phone, the voice "haan" is the proof; a witness is asked if the person needs help reading. A child, or anyone who consented through a guardian, needs a new consent with the guardian instead.

## Web console journeys

### Set up a programme

```mermaid
flowchart TD
  A["Programme: code, name, languages"] --> B["Purposes: essential?<br/>allowed for children? needs a phone?"]
  B --> C["Record of processing per purpose<br/>→ DPO approves"]
  C --> D["Notice: summary, full text,<br/>Rule 3 contents"]
  D --> E["DPO publishes the notice"]
  E --> F["Hindi translation + use names<br/>→ reviewer signs off"]
  F --> G["Audio: Sarvam natural voice<br/>→ reviewer approves"]
  E --> H["Optional: extra questions<br/>(only words the notice mentions)"]
  G --> I["Field workers see it<br/>on next sync"]
  H --> I
```

Rules the console enforces:

- A notice can't be published until every purpose has an approved record of processing and all Rule 3 contents are filled in.
- A translation is never shown in the field until a reviewer is set on it, and a machine-made recording until it is approved.
- An extra question can be switched on only if the published notice mentions it (for example "occupation"). Sensitive ones (caste, religion, disability, pregnancy) show a warning.
- A guardian other than a parent can't be saved without the order number.

### Work the requests inbox

1. Open **Today** (Needs attention lists overdue requests), the **Requests** list (overdue in red) or the **Requests board**.
2. Open a request. If no person is set, fill **Beneficiary**; for SMS or missed calls from a shared number, **Who is this for?** offers the people on that number.
3. Withdrawal: **Record withdrawal**. Other types: act, write the resolution, close.

### Reports and audit

- Analytics charts update from live data.
- **Extra questions: totals** shows counts only, never one person's answers; counts under 5 show as "fewer than 5".
- The **chain** is checked every night (result in Needs attention and Anumati Settings); each consent record has a **Check signature** button.
- Access log and record views show who opened names, phones or evidence.

## Roadmap: Phase 2 and Phase 3

```mermaid
flowchart LR
  P1["Phase 1 · built<br/>Field capture, proof,<br/>withdrawal, inbox, console, API"] --> G1{{"Pilot: 500 real consents<br/>in 2 languages"}}
  G1 --> P2["Phase 2 · rights and channels"]
  P2 --> G2{{"All consortium Musts<br/>met in pilot NGO"}}
  G2 --> P3["Phase 3 · scale and trust"]
```

### Phase 2: rights and channels

| Feature | What it adds |
| --- | --- |
| **Renew at 18** in the app | The person who turned 18 consents on their own record; no duplicate person |
| **ODK connector** | Open Anumati's consent screens from inside an ODK / Kobo form; the survey goes ahead only with consent |
| **Self-service page** | People see and change their own choices from a link |
| **Withdrawal over WhatsApp, IVR and email** | More ways to withdraw, each as easy as giving consent |
| **Access, correction and erasure carried out** | Data export for access requests; erasure fanned out to every connected system, with acknowledgements |
| **Retention and purge** | Data deleted automatically when a purpose's retention period ends, with advance notice |
| **Re-consent and catch-up campaigns** | When a notice changes materially, or for older records collected before consent |
| **Partner (processor) routing** | Withdrawals and erasures passed on to partners, with tracking |
| **Frappe / mGrant client** | Check consent from other Frappe apps |

### Phase 3: scale and trust

| Feature | What it adds |
| --- | --- |
| **Breach notification** | Work out who is affected, message each person in their language, prepare the Data Protection Board report, warn staff as the 72-hour deadline nears |
| **22 Indian languages** | Shared language pack with reviewed translations and audio |
| **Audit pack and evidence certificate** | Exportable PDF + JSON + chain proof; legal evidence certificate (BSA s.63) |
| **CommCare connector and web widget** | Consent inside CommCare apps and websites |
| **External security test** | Independent penetration test |
| **Hosted multi-tenant operations, self-host docs** | Many NGOs on one platform; documentation for running it yourself |

## Setup still needed

| Item | Who | Status |
| --- | --- | --- |
| Deploy the latest code on Frappe Cloud | Admin | After every merge |
| MSG91 Auth key in the site config (`msg91_auth_key`) | MSG91 account owner | Pending; until then the app sends codes from the worker's phone with a voice "haan" by itself |
| Real user accounts; remove the demo password | Admin | Before the pilot |
| MSG91 receipt templates (6 texts drafted) | MSG91 account owner | Optional |
| Inbound number for SMS STOP and missed calls | Admin | Optional |
| Hindi review by a native speaker | Programme team | Later |

## Glossary

| Term | Meaning |
| --- | --- |
| **DPDP** | India's Digital Personal Data Protection Act 2023 and its Rules |
| **Notice** | What the organisation tells people: what data, why, for how long, their rights, how to withdraw |
| **Purpose / use** | One reason data is used (health screening, photos, research); chosen one by one |
| **Essential purpose** | Needed for the service; explained, never a toggle |
| **Receipt code** | `AN-` plus 6 characters, printed on the slip; used to withdraw |
| **Recorded / confirmed** | Recorded = saved with proof; confirmed = the person's phone was verified by a server-sent code or a delivered SMS |
| **Evidence only** | No phone: the voice or photo is the proof |
| **ROPA** | Record of processing for each purpose, approved by the DPO |
| **Rule 3** | The DPDP Rule listing what every notice must say |
| **Local Level Committee** | The National Trust body that can appoint a guardian for an adult who can't decide alone |
| **Chain** | Each consent record carries the hash of the one before, so any change breaks the chain |
