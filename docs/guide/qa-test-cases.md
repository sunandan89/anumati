# Anumati Phase 1: manual test cases

For QA testing of the field app (Anumati Collect) and the web console. Each case lists steps and the expected result. Priority: **P0** blocks the pilot, **P1** should pass before the pilot, **P2** nice to have.

> Kept in the `anumati` repository (`docs/guide/`). Every pull request that changes behaviour adds or updates the cases it affects.

## Before you start

| Item | Value |
| --- | --- |
| Site | `https://anumati.nvi.frappe.cloud` (latest code deployed) |
| App | `app-release.apk` from GitHub → `anumati_collect` → Releases → **test-latest** (uninstall any older build first) |
| Field worker login | The demo field worker (ask the admin for the password) |
| Web console login | An admin / DPO account, or Frappe Cloud → **Login as Administrator** |
| Test phones | Phone A runs the app. Phone B is "the person's" phone and must receive SMS. Use your own numbers only. |
| Sample data | Anumati Settings → **Add sample data** (20 fictional people in Village Health Camps) |
| MSG91 | If `msg91_auth_key` is not set yet, codes go from the worker's phone (cases marked **[MSG91]** need the key) |

Use fictional names only, for example "Test Person 01". Record the receipt code of each consent you create; later cases use it.

## 1. Sign-in and phone safety

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| AU-01 | First sign-in | Install app → enter site address, user, password → set a 4-digit PIN | Home shows the programme chooser, then Home tiles | P0 |
| AU-02 | Wrong password | Enter a wrong password | Clear error; no crash; can retry | P1 |
| AU-03 | App lock | Close the app for a few minutes → reopen | PIN screen; correct PIN opens Home; wrong PIN refused | P0 |
| AU-04 | Return after a long pause | Leave the app in the background 30+ minutes → reopen | App screen draws normally (no black screen) | P0 |
| AU-05 | Screenshots blocked | Try a screenshot inside the app | Blocked or black (personal data protected) | P1 |
| AU-06 | Lost phone wipe | Console: Field phones → this phone → **Report lost** → on the phone, open the app online | Phone wipes its data and signs out; a breach incident is opened in the console | P1 |
| AU-07 | Field worker can't use the console | Log in to the website with the field worker account | No Anumati workspaces or menus are shown | P1 |

## 2. Consent: the person, who can read and has a phone

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| CA-01 | Screen 1 basics | Take new consent → "The person, for themself" | Name, Has a mobile phone? (Yes/No), Mobile number, Can read? (Yes/Needs help), Language, "More: phone shared"; no Beneficiary ID box; "Step 1 of 3" | P0 |
| CA-02 | Phone box hides | Set "Has a mobile phone?" to No | Mobile number box disappears | P1 |
| CA-03 | Bad number | Enter 5 digits → Continue | Error: enter a 10-digit number, or choose No | P1 |
| CA-04 | Notice must play first | Continue to "Notice and choices" | Optional-use switches and Yes/No to all are disabled until the notice has played to the end (or "They have read the whole notice" is tapped when there is no recording) | P0 |
| CA-05 | Natural voice credit | Play a notice that has a Sarvam recording | "Natural voice · Powered by Sarvam AI" under the player (English and Hindi) | P2 |
| CA-06 | Choices start off | After the notice | Every optional use is off; essential uses show "Required" with no switch | P0 |
| CA-07 | Equal buttons | Tap "Yes to all", then "No to all" | All optional uses turn on, then all off | P1 |
| CA-08 | Confirm screen, server route online **[MSG91]** | Programme setting "MSG91 when online"; phone online → Confirm | No code box before Save; note "After Save, you can send a code…"; no witness; Save needs only the tick | P0 |
| CA-09 | Send code **[MSG91]** | Save → receipt → **Send code** | Phone B gets "Your OTP is … -Dhwani RIS"; Phone A shows "Code sent to 98765XXX"; Phone A never shows the code | P0 |
| CA-10 | Code matches **[MSG91]** | Type the code from Phone B | "Code matched · consent confirmed"; console shows the consent as confirmed | P0 |
| CA-11 | Wrong code **[MSG91]** | Type a wrong 6-digit code | "That code does not match. 4 tries left"; after 5 wrong tries, a new code is needed | P1 |
| CA-12 | Send limit **[MSG91]** | Tap "Send a new code" 4 times within 10 minutes | 4th attempt refused: try again in 10 minutes | P2 |
| CA-13 | Offline route | Turn off mobile data and Wi-Fi → take consent → Confirm | "No internet: the code goes from your phone…"; "Check their phone · both needed": SMS code from your phone **and** voice "haan"; Save disabled until both | P0 |
| CA-14 | Worker-phone code | In CA-13, tap "Open SMS app with code" → send to Phone B → enter the code | "Code matched"; still needs the voice | P0 |
| CA-15 | Voice required | In CA-13, record the person's "haan" | Voice shows "Saved"; Save enabled; the console later shows the consent as **recorded** with a voice file | P0 |
| CA-16 | Programme set to worker's phone | Console: programme → How SMS codes are sent = **Worker's phone** → sync app → take consent online | Same as CA-13 even with internet | P0 |
| CA-17 | Can't get the code | In CA-13, tap "Can't get the code now? Confirm later by SMS" | Code step marked confirm-later; voice still required | P1 |
| CA-18 | Save says what's missing | On Confirm, leave the tick off | Red line above Save: "To save: tick the declaration" | P1 |
| CA-19 | Receipt | Save | Receipt code `AN-XXXXXX`, agreed and refused uses, "Verified by"; "Send receipt by SMS" opens the SMS app with the receipt text | P0 |

## 3. Consent: needs help reading, or no phone

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| CB-01 | Reads, no phone | Has phone = No, Can read = Yes → Confirm | "Record their yes · choose at least one": voice "haan" or photo of signature/thumbprint; no witness ("No witness: they read the notice themselves") | P0 |
| CB-02 | Photo instead of voice | In CB-01, take only the signature photo → Save | Saves; verification "Evidence only" | P0 |
| CB-03 | Needs help, no phone | Has phone = No, Can read = Needs help | Hint on screen 1 explains voice/thumbprint and witness; Confirm asks for voice or thumbprint **and** a witness name (relation optional) | P0 |
| CB-04 | Witness required | In CB-03, leave the witness name empty | Save disabled: "To save: the witness's name" | P0 |
| CB-05 | Needs help, has phone | Has phone = Yes, Can read = Needs help, online with MSG91 | Voice or thumbprint + witness before Save; Send code after Save **[MSG91]** | P1 |
| CB-06 | Use needing a phone hidden | Village Health Camps, no phone | "Follow-up calls" is not offered; note "Uses that need a phone are not offered" | P0 |
| CB-07 | Hindi use names | Language हिंदी | Use names and descriptions in Hindi (for example "फ़ॉलो-अप कॉल") | P1 |
| CB-08 | Voice helper hint | With the voice helper on in settings, record "haan" | A hint "Sounds like yes" (or no / unclear); worker still decides | P2 |

## 4. Consent: parent for a child

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| CC-01 | Screen 1 for a child | "A parent, for a child under 18" | Child's name, Child's year of birth (with "used only to ask for fresh consent at 18"), Language; no phone or reading questions | P0 |
| CC-02 | Already 18 | Year of birth 20 years ago | Error: already 18, choose "The person, for themself" | P1 |
| CC-03 | Parent's details | Continue | Mother / Father / Other guardian chips, parent's name, parent's mobile, ID photo (optional) | P0 |
| CC-04 | Parent online **[MSG91]** | Valid mobile, online | Note "After Save, a code is sent to this number from the server"; Continue enabled | P0 |
| CC-05 | Parent offline | Offline, valid mobile | Code from your phone + guardian's voice "haan" both required before Continue | P0 |
| CC-06 | Parent with no phone | Leave mobile empty | ID photo becomes required: "To save: a photo of the guardian's ID (no phone)" | P0 |
| CC-07 | Other guardian | Choose "Other guardian" | Order number (required) and order photo (optional) appear | P0 |
| CC-08 | Research hidden for children | Notice and choices | "Anonymised research" not offered; note "Some uses are not offered for children" | P0 |
| CC-09 | Guardian saves on screen 3 | Play notice → choose → tick → Save | Saves from the notice screen; receipt; Send code goes to the **parent's** phone **[MSG91]** | P0 |
| CC-10 | Child record in console | Open the child in Beneficiaries | Minor ticked, year of birth, "Turns 18 by" date; guardian link to the parent | P1 |

## 5. Consent: guardian for an adult who can't decide alone

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| CD-01 | Guardian's details | "A guardian, for an adult who can't decide alone" → Continue | Appointed by (Local Level Committee / Court / Other authority / No order yet), Order number, order photo (optional), Relation chips, guardian name, mobile, ID photo (optional) | P0 |
| CD-02 | Order number required | Leave order number empty | "To save: the order number" | P0 |
| CD-03 | Relation required | No relation chip | "To save: the relation" | P1 |
| CD-04 | No order yet | Choose "No order yet" | "Consent can't be taken yet" panel; **Inform coordinator** and **Back** | P0 |
| CD-05 | Coordinator told | Tap Inform coordinator (online) | Toast confirms; nothing about the person saved; a Programme Manager sees a Desk notification without the person's name | P0 |
| CD-06 | Full consent | Fill all, notice, Save | Receipt; console shows guardian link with type committee/court and the order number | P0 |

## 6. Extra questions ("About the person")

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| EQ-01 | Off by default | A programme with no questions | No "About the person" screen | P0 |
| EQ-02 | Demo question | Village Health Camps (asks Age) | "About the person" after choices; step label "of 4"; Age required | P0 |
| EQ-03 | Not in notice | Console: programme → Extra questions → add "Education" (notice doesn't mention it) → Save | Refused: "Add these to the notice first…" | P0 |
| EQ-04 | Sensitive warning | Add a sensitive question the notice mentions | Saves with an orange warning | P1 |
| EQ-05 | Answer in Hindi | Hindi consent with a choice question | Choices shown in Hindi; stored as the English value | P1 |
| EQ-06 | Totals only | Console: report **Extra questions: totals** | Counts per answer only; counts under 5 show "fewer than 5" | P1 |

## 7. After consent: sync, find, withdraw, add a use

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| SY-01 | Offline then sync | Take 3 consents offline → go online → Sync | All 3 appear in the console once each; "waiting to sync" goes to 0 | P0 |
| SY-02 | Sync cut off | Start sync, turn data off mid-way, then on and sync again | No duplicate people or consents | P0 |
| SY-03 | Rejected record | (Developer can force) a record the server refuses | Appears in "Records that need attention" with the reason; Try again / Discard | P1 |
| FI-01 | Find offline | Find beneficiary → search by name, ID, then receipt code (offline) | Person found; each use's status shown | P0 |
| WD-01 | Withdraw all optional uses | Log withdrawal or request → In person → find the person → "Stop all optional uses" → Save | Phone shows those uses withdrawn at once; after sync, console Consent state = withdrawn; essential use still granted | P0 |
| WD-02 | Withdraw one use | Choose "Stop only: Photos and stories" | Only that use withdrawn | P0 |
| WD-03 | Paper slip, person not on phone | Paper slip → code not on this phone | "Not on this phone. It goes to the office inbox with the code"; request appears in the console inbox | P0 |
| WD-04 | Other requests | "See or correct my data", "Delete my data", "Complaint" | Each appears in the inbox with type and due date (30 days) | P0 |
| AP-01 | Add a use later | Console: add a new optional purpose to the programme and publish a new notice version → app sync → Ask for one more purpose → pick a person | Past decisions shown as "not asked again"; only the new use is asked; read-to-them tick before Yes/No | P1 |
| AP-02 | Add a use, offline | As AP-01, offline | Code from your phone + voice "haan" required before Save | P1 |
| AP-03 | Add a use, needs help | Person who needs help reading | Witness name required | P1 |

## 8. Web console

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| WC-01 | Menus by role | Log in as Programme Manager, DPO, Operator, Admin in turn | Each sees only its workspaces (Setup only for Admin) | P1 |
| WC-02 | Today dashboard | Open Today | Number cards and charts load with sample data; "Needs attention" list | P1 |
| WC-03 | Search beneficiaries | Search by whole first name, full phone number, receipt code | Correct person found; list shows IDs, names revealed only on request (logged) | P0 |
| WC-04 | Consent record view | Open a consent | Summary: agreed / said no, how, verified by, notice version and delivery, evidence with labels (Voice "haan", Signature or thumbprint, Guardian's ID, Appointment order); record can't be edited | P0 |
| WC-05 | Evidence view logged | Open a voice or photo | Plays / shows; an Access Log entry is created | P1 |
| WC-06 | Insert-only | Try to edit and save an existing Consent Event | Refused | P0 |
| WC-07 | Publish a notice | Create a notice with a purpose whose record of processing is not approved, or with a Rule 3 field empty | The **Publish** action is not offered until every ROPA is approved and all five Rule 3 fields are filled | P0 |
| WC-08 | Translation review | Add a Hindi translation without a reviewer | App does not show it (English shown with a note) until a reviewer is set | P0 |
| WC-09 | Translated use names | In the translation, fill "Uses (translated)" | App shows those names for Hindi consents; Notice phone preview shows them | P1 |
| WC-10 | Needs a phone | Tick "Needs the person's phone" on a purpose | Hidden in the app for people without a phone; preview marks it | P1 |
| WC-11 | SMS code setting | Programme → Capture → How SMS codes are sent | Two options; default "MSG91 when online" | P0 |
| WC-12 | Guardian order number | Create a Guardian Link with type Court and no order number | Refused: "Enter the order number…" | P1 |
| WC-13 | Inbox and SLA | Requests board | Requests in columns by status; overdue highlighted; due date = received + 30 days | P0 |
| WC-14 | Record withdrawal | Open a withdrawal request → **Record withdrawal** | One signed withdrawal created; request closed; doing it twice does not create a second | P0 |
| WC-15 | Unmatched request | A request with no person → Who is this for? | Pick the person; request becomes matched | P1 |
| WC-16 | Turned 18 list | Beneficiaries workspace → "Turned 18: renew consent" | Shows people flagged by the daily job (QA: ask a developer to set a test child's "Turns 18 by" to yesterday and run the job) | P2 |
| WC-17 | Chain verify | Run chain verify (DPO/Admin) | Reports the chain intact | P1 |

## 9. Security and data protection

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| SE-01 | API needs login | Call `/api/method/anumati.api.v1.consent.check` without a token | 401 or 403 | P0 |
| SE-02 | Public verify only | `consent.verify` with a receipt hash, no login | Says whether it's on the chain and the signature is valid; no personal data | P1 |
| SE-03 | No personal data in messages log | Console → Communications for an SMS sent | Phone number not shown (hash only); one-time codes shown as `******` | P0 |
| SE-04 | Worker can't send another worker's code | Field worker B tries to send a code for worker A's consent (API) | Refused | P1 |
| SE-05 | Worker-phone code needs voice | API: record a consent with `device_sms_otp` and no audio evidence | Refused | P1 |
| SE-06 | Names encrypted | Database / report view of Beneficiary | Name and phone stored encrypted; whole-word name search still works | P1 |

## Reporting a bug

Give the test ID, the phone model and Android version, online or offline, the receipt code if any, and a screenshot (cover any real phone number).
