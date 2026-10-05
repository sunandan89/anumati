# Anumati Phase 1: manual test cases

For QA testing of the field app (Anumati Collect) and the web console. Each case lists steps and the expected result. Priority: **P0** blocks the pilot, **P1** should pass before the pilot, **P2** nice to have.

> Kept in the `anumati` repository (`docs/guide/`). Every pull request that changes behaviour adds or updates the cases it affects.

## Before you start

| Item | Value |
| --- | --- |
| Site | `https://anumati.nvi.frappe.cloud` (latest code deployed) |
| App | `app-release.apk` from GitHub → `anumati_collect` → Releases → **test-latest** (uninstall any older build first) |
| Field worker login | The demo field worker (ask the admin for the password) |
| Web console logins | One account per role you test: **DPO** (publishes notices), **Programme Manager**, **Operator**, **Admin**. Frappe Cloud → **Login as Administrator** also works. If two-factor login is on, have the authenticator ready |
| Test phones | Phone A runs the app. Phone B is "the person's" phone and must receive SMS. Use your own numbers only |
| Sample data | Anumati Settings → **Actions → Add sample data** (System Manager only): 20 fictional people in Village Health Camps. Their numbers start with 555 and can't receive SMS, so cases that need a code use people you create in the app |
| SMS codes | Until `msg91_auth_key` is set on the site, the app sends codes **from the worker's phone with the voice "haan"**, even online. Cases marked **[MSG91]** need the key |
| Refreshing the app | After changing a programme, notice or translation in the console: on the phone, tap **Sync** (or pull down on Home) while online |

**Step labels:** Village Health Camps asks one extra question (Age), so its screens show "Step x of **4**" and guardians save on **About the person**. After-school Learning Centres and Women's Self-Help Groups have no extra questions: "of **3**", and guardians save on the notice screen.

Use fictional names only, for example "Test Person 01". Record the receipt code of each consent you create; later cases use it.

## 1. Sign-in, app lock and phone safety

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| AU-01 | First sign-in | Install app → enter organisation address, user, password → set a 4-digit PIN (entered twice) | Home appears with a **Choose a programme** card; tap it to pick one (picked automatically if the worker has only one programme) | P0 |
| AU-02 | Wrong password | Enter a wrong password | Clear error; no crash; can retry | P1 |
| AU-03 | App lock | Leave the app in the background for 5+ minutes, or close it fully, then reopen | PIN screen; correct PIN opens Home | P0 |
| AU-04 | Wrong PIN 5 times | On the PIN screen, enter a wrong PIN 5 times | Signed out and the phone's Anumati data wiped; sign in again | P1 |
| AU-05 | Forgot PIN | Tap "Forgot PIN? Sign out" | Signs out and wipes the phone's data after a warning | P2 |
| AU-06 | Sign out with unsynced records | Take a consent offline → Home menu → **Sign out** | A warning says records are not synced yet; Cancel keeps them | P1 |
| AU-07 | Return after a long pause | Leave the app in the background 30+ minutes → reopen | Screen draws normally (no black screen) | P0 |
| AU-08 | Screenshots blocked | Try a screenshot inside the app | Blocked or black (personal data protected) | P1 |
| AU-09 | Lost phone wipe | Console (Admin or Programme Manager): Field phones → this phone → **Report lost** → on the phone, open the app online | Phone wipes its data and signs out; a breach incident is opened in the console | P1 |
| AU-10 | App paused or too old | Admin: switch off the field app in Mobile Configuration (or raise the minimum version) → open the app | "The field app is paused" (or "Please update the app"); switch back on afterwards | P2 |
| AU-11 | Field worker can't use the console | Log in to the website with the field worker account | No Anumati workspaces or menus are shown | P1 |

## 2. Consent: the person, who can read and has a phone

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| CA-01 | Screen 1 basics | Take new consent → "The person, for themself" | Name, "Has a mobile phone?" (Yes/No), Mobile number, "Can read the notice?" (Yes/Needs help), Language (English/हिन्दी), "More: phone shared in the household", "The beneficiary ID is created automatically."; no Beneficiary ID box | P0 |
| CA-02 | Phone box hides | Set "Has a mobile phone?" to No | Mobile number box disappears | P1 |
| CA-03 | Bad number | Enter 5 digits → Continue | "Enter a 10-digit mobile number, or choose No" | P1 |
| CA-04 | Notice must play first | Continue to "Notice and choices" | Optional-use switches and Yes/No to all are disabled until the recording has played to the end | P0 |
| CA-05 | No recording | Use a notice or language with no approved recording | Phone voice card ("Listen to the notice"), or if the phone has no voice for the language, a note to read it aloud; the full notice is open with a button "They have read the whole notice" (or "I have read the whole notice to them" for someone who needs help) that unlocks the choices | P1 |
| CA-06 | Natural voice credit | Play a notice that has a Sarvam recording | "Natural voice · Powered by Sarvam AI" under the player (English and Hindi) | P2 |
| CA-07 | Choices start off | After the notice | Every optional use is off; essential uses show "Required" with no switch | P0 |
| CA-08 | Equal buttons | Tap "Yes to all", then "No to all" | All optional uses turn on, then all off | P1 |
| CA-09 | No published notice | Choose a programme with no published notice → Take new consent | "This programme has no published notice yet." | P2 |
| CA-10 | Confirm, server route **[MSG91]** | Programme "How SMS codes are sent" = MSG91 when online; phone online → Confirm | No code box before Save; note "After Save, you can send a code to their phone from the server…"; "No witness: they read the notice themselves."; Save needs only the tick | P0 |
| CA-11 | Send code **[MSG91]** | Save → receipt → **Send code** | Phone B gets "Your OTP is … -Dhwani RIS"; Phone A shows "Code sent to 9876543XXX. Ask them to read it out." and never shows the code | P0 |
| CA-12 | Code matches **[MSG91]** | Type the code from Phone B | "Code matched · consent confirmed"; in the console the person's current consent shows confirmed (and a Confirmation attempt "confirmed"); the consent record itself is unchanged | P0 |
| CA-13 | Wrong code **[MSG91]** | Type a wrong 6-digit code | "That code does not match. 4 tries left."; after 5 wrong tries a new code is needed | P1 |
| CA-14 | Send limit **[MSG91]** | Tap Send code, then "Send a new code" twice, then once more (within 10 minutes) | The 4th send is refused; the app shows "Could not send the code. Try again in a minute." | P2 |
| CA-15 | SMS not set up | Site without `msg91_auth_key`, phone online → Confirm | "Check their phone · both needed" with "SMS codes from the server are not set up yet: the code goes from your phone…"; code and voice required | P0 |
| CA-16 | Offline route | Mobile data and Wi-Fi off → take consent → Confirm | "No internet: the code goes from your phone. Their voice “haan” is needed with it."; Save disabled until both the code and the voice are done | P0 |
| CA-17 | Worker-phone code | In CA-16, tap "Open SMS app with code" → send to Phone B → type the code read back | "Code matched"; voice still needed | P0 |
| CA-18 | Wrong worker-phone code 5 times | In CA-16, type 5 wrong codes | "Too many wrong codes. Choose another method." | P2 |
| CA-19 | Voice required | In CA-16, record the person's "haan" → Save | Saves; after sync the consent shows **recorded** (never confirmed) with a voice file | P0 |
| CA-20 | Programme set to worker's phone | Console: programme → **How SMS codes are sent = Worker's phone** → sync the app → take consent online | "This programme sends codes from your phone. Their voice “haan” is needed with the code."; code and voice required | P0 |
| CA-21 | Can't get the code | In CA-16, tap "Can't get the code now? Confirm later by SMS" | "Confirm later: an SMS goes to … after sync."; voice still required | P1 |
| CA-22 | Save says what's missing | On Confirm, leave things undone | Red line above Save lists everything missing, e.g. "To save: the SMS code, their voice “haan”, tick the declaration" | P1 |
| CA-23 | Receipt | Save | Receipt code `AN-XXXXXX`, agreed and refused uses, "Verified by"; "Send receipt by SMS" opens the SMS app with the receipt text | P0 |

## 3. Consent: needs help reading, or no phone

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| CB-01 | Reads, no phone | Has phone = No, Can read = Yes → Confirm | "Record their yes · choose at least one": voice "haan" or "Photo of their signature or thumbprint on the slip"; "No witness: they read the notice themselves." | P0 |
| CB-02 | Photo instead of voice | In CB-01, take only the photo → Save | Saves; verification "Evidence only" | P0 |
| CB-03 | Needs help, no phone | Has phone = No, Can read = Needs help | Screen 1 hint explains voice or thumbprint and a witness; Confirm asks for voice or "Thumbprint on their slip" **and** "Witness name" ("Relation (optional)") | P0 |
| CB-04 | Witness required | In CB-03, leave the witness name empty | Save disabled; the red line includes "the witness's name" | P0 |
| CB-05 | Needs help, has phone, server route **[MSG91]** | Has phone = Yes, Needs help, online | Voice or thumbprint + witness before Save; Send code after Save | P1 |
| CB-06 | Needs help, has phone, worker's phone | As CB-05 but offline | Code from your phone + voice "haan" (thumbprint not offered in this case) + witness | P1 |
| CB-07 | Use needing a phone hidden | Village Health Camps, no phone | "Follow-up calls" is not offered; note "Uses that need a phone are not offered." | P0 |
| CB-08 | Hindi use names | Language हिन्दी | Use names and descriptions in Hindi (for example "फ़ॉलो-अप कॉल") | P1 |
| CB-09 | Voice helper hint | With "Help recognise a spoken yes or no" on in Anumati Settings, record "haan" | A hint "Sounds like yes" (or no / unclear); the worker still decides | P2 |

## 4. Consent: parent for a child

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| CC-01 | Screen 1 for a child | "A parent, for a child under 18" | Child's name, Child's year of birth ("Used only to ask for fresh consent when the child turns 18."), Language; no phone or reading questions | P0 |
| CC-02 | Already 18 | Year of birth 20 years ago | "Born in …: already 18. Choose “The person, for themself”." | P1 |
| CC-03 | Parent's details | Continue | Mother / Father / Other guardian chips; "Parent's name", "Parent's mobile"; with the mobile empty, "Photo of the parent's ID" (required) and the note "No phone? Then the ID photo is required…"; once a number is typed, it reads "(optional)" | P0 |
| CC-04 | Parent online **[MSG91]** | Valid mobile, online | Note "After Save, a code is sent to this number from the server…"; Continue enabled | P0 |
| CC-05 | Parent offline or SMS not set up | Valid mobile, offline (or no MSG91 key) | Code from your phone + "Voice: the guardian’s “haan”" both required before Continue | P0 |
| CC-06 | Parent with no phone | Leave mobile empty, no ID photo | Continue disabled; the red line includes "a photo of the guardian's ID (no phone)" | P0 |
| CC-07 | Other guardian | Choose "Other guardian" | "Order number" (required) and "Photo of the order (optional)"; fields become "Guardian's name" / "Guardian's mobile" | P0 |
| CC-08 | Research hidden for children | Notice and choices | "Anonymised research" (or the learning study) not offered; note "Some uses are not offered for children." | P0 |
| CC-09 | Guardian saves on the last screen | Learning Centres: play notice → choose → tick → Save on the notice screen. Village Health Camps: Continue → About the person → tick → Save | Receipt; Send code goes to the **parent's** phone **[MSG91]** | P0 |
| CC-10 | Child record in console | Open the child in Beneficiaries | "Minor" ticked, year of birth, "Turns 18 by" = 31 December of birth year + 18; guardian link to the parent | P1 |
| CC-11 | Child not used before confirmation | API `consent.check` for the child's optional use right after a worker-phone consent | `allow: false`, status `awaiting_confirmation` | P1 |

## 5. Consent: guardian for an adult who can't decide alone

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| CD-01 | Guardian's details | "A guardian, for an adult who can't decide alone" → Continue | Guardian appointed by (Local Level Committee / Court / Other authority / No order yet), Order number, "Photo of the order (optional)", Relation chips, "Guardian's name", "Guardian's mobile", guardian's ID photo (required until a mobile is typed) | P0 |
| CD-02 | Order number required | Leave order number empty | Continue disabled; the red line includes "the order number" | P0 |
| CD-03 | Relation required | No relation chip | The red line includes "the relation" | P1 |
| CD-04 | No order yet | Choose "No order yet" | "Consent can't be taken yet" panel; **Inform coordinator** and **Back** | P0 |
| CD-05 | Coordinator told | Tap Inform coordinator (online) | "Your coordinator will be told. Nothing about the person was saved."; a Programme Manager sees a Desk notification without the person's name | P0 |
| CD-06 | Full consent | Fill all, notice, Save | Receipt; console shows the guardian link with type committee or court and the order number | P0 |

## 6. Extra questions ("About the person")

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| EQ-01 | Off by default | After-school Learning Centres (no questions) | No "About the person" screen; "Step x of 3" | P0 |
| EQ-02 | Demo question | Village Health Camps (asks Age) | "About the person" after the choices; "Step 3 of 4"; Age required ("To save: answer the required questions") | P0 |
| EQ-03 | Not in notice | Console: Programme → Extra questions → add "Education" (the notice doesn't mention it) → Save | Refused: "Add these to the notice first…" | P0 |
| EQ-04 | Sensitive warning | First publish a new notice version whose text mentions "religion" → add the Religion question | Saves with an orange warning about sensitive questions | P1 |
| EQ-05 | Choice question in Hindi | With a notice that mentions "gender", add Gender → take a Hindi consent | Choices shown in Hindi (महिला…); the console shows the English value | P1 |
| EQ-06 | Totals only | After a few app consents with answers: report **Extra questions: totals** | Counts per answer only; counts under 5 show "fewer than 5". (Each person's own answers are visible on their record to staff) | P1 |

## 7. After consent: sync, find, withdraw, add a use

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| SY-01 | Offline then sync | Take 3 consents offline → go online → Sync | All 3 appear in the console once each; Home shows "0 records on this phone" (the console's "Waiting to sync" card updates at the next sync) | P0 |
| SY-02 | Sync cut off | Start sync, turn data off mid-way, then on and sync again | No duplicate people or consents | P0 |
| SY-03 | Older record arrives late | Withdraw a use on phone A; on phone B (offline) grant the same use with an earlier time; sync B after A | The withdrawal stays: an older record never overrides a newer one | P1 |
| SY-04 | Rejected record | (Developer can force) a record the server refuses | Home shows "… records could not be saved on the server"; the list shows the reason; Try again / Discard | P1 |
| FI-01 | Find offline | Find beneficiary → search by name, then ID (offline); then by receipt code of a consent taken **on this phone** | Person found; each use's status shown. A downloaded person (consent taken on another phone) is found by their latest receipt code too | P0 |
| FI-02 | Find by phone | Find beneficiary → type a person's mobile number, then the same with +91, then only its last 4 digits | The person is found each time, labelled "Their number". Three digits or fewer search names only | P0 |
| FI-03 | Find by guardian's phone | Take a parent consent for a child with the mother's number (journey C) → Find → type the mother's number. Repeat on another phone after both sync | The child is found, labelled "Guardian's number (Mother)"; if the mother is also enrolled, both appear. Works on the other phone too | P0 |
| WD-01 | Withdraw all optional uses | Stop a use or leave → find the person → **Stop all** → Save ("Stop 3 uses for …") | Phone shows those uses withdrawn at once; after sync, the console shows them withdrawn; essential use still granted | P0 |
| WD-02 | Withdraw some uses | Switch off "Photos and stories" and "Follow-up calls", leave "Anonymised research" on | Save reads "Stop 2 uses for …"; only those two withdrawn | P0 |
| WD-03 | Paper slip, person not on phone | Tick "They gave a paper slip or letter" → enter a code not on this phone → "Stop all optional uses" | "Not on this phone. It goes to the office inbox with the code"; the request appears **Open** in the inbox | P0 |
| WD-04 | Other requests | "See or correct my data", "Delete my data", "Complaint" | Inbox shows them as Data access request, Erasure and Grievance, each with a due date 30 days out | P0 |
| WD-05 | Field withdrawal is listed in the inbox | Do WD-01 with the paper slip box ticked and slip number `SLIP-0042` → Sync → console: Requests | One **Closed** withdrawal request for that person, with the slip number, linked to the withdrawal consent record, and the resolution naming the worker. No "new request" alert. Syncing again adds no second request | P0 |
| WD-06 | Slip from someone another worker enrolled | On phone B, find by the receipt code of a consent taken on phone A (after both have synced) | Person found; withdrawal works as WD-01 | P0 |
| WD-07 | Code given, person not on the phone | Enter a real receipt code of a person not downloaded to this phone → "Delete my data" → Save → Sync | The inbox request is already matched to that person (Beneficiary filled) | P1 |
| WD-08 | Nothing left to stop | Find a person who has left the programme (nothing on) | Note "Nothing is on for this person, so there is nothing to stop."; no switches; Save is disabled until another request is chosen | P1 |
| WD-09 | Essential use is locked | Find a person with Health screening on | Health screening shows a lock and "Needed for the programme. To stop it, they leave the programme." No switch | P0 |
| WD-10 | Leave the programme | Find a person → **Leave the programme** → read the warning → **Yes, leave** → Save → Sync | Every use, Health screening too, shows withdrawn on the phone and in the console; the person's record shows **Relationship ended** today; the inbox request's resolution starts "Left the programme". **Cancel** in the warning changes nothing | P0 |
| WD-11 | Withdrawal noted and SMS | After WD-02 | "Withdrawal noted" lists the stopped uses and a withdrawal code (AN-…); **Send by SMS** opens your SMS app with the code and message in the person's language; no button if neither they nor a guardian have a phone. After sync, the console's withdrawal consent record has the same code | P1 |
| WD-12 | Delete my data explained | Find a person → Other requests | "Delete my data" says the office keeps only what the law needs and that services may stop | P2 |
| WD-13 | Withdrawal for a child | Find a child (parent consent, journey C) → stop a use → Save | **Send by SMS** goes to the parent's number | P1 |
| WD-14 | Leave, then undo | Find a person → Leave the programme → Yes, leave → look at the uses → **Don't leave** | While leaving: every use shows "Will stop", switches greyed, warning line. After Don't leave: switches work again and Save is off | P1 |
| WD-15 | Stop all / Keep all | Find a person with 2+ optional uses on → **Stop all** → **Keep all** | Stop all switches all off and the link becomes Keep all; Keep all switches them back on | P2 |
| WD-16 | Find offers both actions | Find beneficiary → tap a person | A choice: **Stop a use or leave** / **Add a use or rejoin**; each opens for that person | P1 |
| AP-01 | Add a use later | Console: add a new optional purpose, approve its record of processing, publish a new notice version → app: Sync → Add a use or rejoin → pick a person | Past decisions shown "not asked again"; only the new use is asked; "I have read it to them" before Yes/No. (Hindi text needs the new version's Hindi translation reviewed) | P1 |
| AP-02 | Add a use, offline | As AP-01, offline, person has a phone | Code from your phone + voice "haan" required before Save | P1 |
| AP-03 | Add a use, no phone | Person without a phone | Voice "haan" required | P1 |
| AP-04 | Add a use, needs help | Person who needs help reading | Witness name required | P1 |
| AP-05 | Add a use, child | A child consented through a parent | "A guardian must consent for this person. Take a new consent with the guardian." | P1 |
| AP-06 | Ask again | After WD-02 → Add a use or rejoin → the same person | The two withdrawn uses show "Ask again"; "Anonymised research" is under "Already agreed"; Yes switches a use back on after sync | P1 |
| AP-07 | Rejoin after leaving | After WD-10 → Add a use or rejoin → the same person | "Rejoin the programme: Health screening" is asked; Yes and Sync turn it back on and clear Relationship ended in the console | P1 |
| AP-08 | Rejoin: other uses wait | After WD-10 → Add a use or rejoin → tap No on "Rejoin the programme" | The other uses can't be answered ("Answer Rejoin the programme first"); note "They do not want to rejoin… Nothing to save"; Save off | P1 |
| AP-09 | Yes to all / No to all | A person with 2+ uses to ask → tick "I have read it to them" on each → **Yes to all**, then **No to all** | The buttons stay off until every part is read; each sets every answer; Save works for either (except No to all while rejoining, as AP-08) | P2 |

## 8. Web console

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| WC-01 | Menus by role | Log in as Programme Manager, DPO, Operator, Admin in turn | Each sees only its workspaces (Setup only for Admin) | P1 |
| WC-02 | Today dashboard | Open Today | Number cards and charts load with sample data; Needs attention lists overdue requests and the chain check | P1 |
| WC-03 | Search beneficiaries | Search by whole first name, full phone number, receipt code | Correct person found; the list shows names and masked phones; each view is logged in the access log | P0 |
| WC-04 | Consent record view | Open a consent | Summary: agreed / said no, how, verified by, notice version and delivery; Evidence tab with labels ("Voice: their “haan”", "Thumbprint", "Signature or thumbprint"); **Check signature** button; the record can't be edited | P0 |
| WC-05 | Guardian photos | Open a guardian link from a guardian consent | Buttons "View order or document" and "View guardian's ID" | P1 |
| WC-06 | Evidence view logged | Open a voice or photo | Plays / shows; an Access Log entry is created | P1 |
| WC-07 | Insert-only | Try to edit and save an existing consent record | Refused | P0 |
| WC-08 | Publish a notice (as **DPO**) | Create a notice with a purpose whose record of processing is not approved, or with a Rule 3 field empty | The **Publish** action is not offered until every record of processing is approved and all five Rule 3 fields are filled | P0 |
| WC-09 | Translation review | Clear the **Reviewer** on the existing Hindi translation → app: Sync → Hindi consent | The app shows the English notice with the note "This language has no reviewed notice yet…"; set the reviewer back afterwards | P0 |
| WC-10 | Translated use names | In the translation, fill "Uses (translated)" → app: Sync | The app shows those names for Hindi consents; the notice's Phone preview shows them | P1 |
| WC-11 | Needs a phone | Tick "Needs the person's phone" on a purpose | Hidden in the app for people without a phone; the preview marks it | P1 |
| WC-12 | SMS code setting | Programme → Capture & verification → "How SMS codes are sent" | Two options; default "MSG91 when online" | P0 |
| WC-13 | Guardian order number | Create a Guardian Link with type Court and no order number | Refused: "Enter the order number that appointed this guardian" | P1 |
| WC-14 | Inbox and SLA | Requests list and board | Due date = received + 30 days; overdue shown in red in the list and in Needs attention | P0 |
| WC-15 | Record withdrawal | Open a matched withdrawal request → **Record withdrawal** | A checklist of the person's uses that are on (optional ones ticked, essential ones marked "(essential)"); untick one → Withdraw: only the ticked uses withdrawn; request closed; doing it again creates no second one. Nothing on: a message instead of the checklist | P0 |
| WC-16 | Shared number | Two people share a phone; send `STOP` from it (needs an inbound number) | Request **Unmatched** with possible matches; **Who is this for?** → pick → Match | P2 |
| WC-17 | Request notifications | Submit a request | DPO and Operator get a Desk notification; another 3 days before the due date | P2 |
| WC-18 | Turned 18 | Open a sample child → set year of birth so they are now 18 or older → Save | "Turned 18: renew consent" is ticked and the person appears under that shortcut; `consent.check` answers `renewal_due` | P2 |
| WC-19 | Chain check | Anumati Settings → Chain verification (after the nightly job), or ask a developer to call `chain.verify` | Chain reported intact | P1 |
| WC-20 | Record withdrawal: leave the programme | As WC-15, tick **Leave the programme** → Withdraw | Every use, essential too, withdrawn; the person's record shows Relationship ended | P1 |

## 9. SMS channels (need an SMS account and inbound number)

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| SM-01 | Receipt SMS from the server | SMS set up, "Send SMS receipts" on → take a consent with a phone | Phone B gets the receipt SMS | P2 |
| SM-02 | Confirm later | Consent with "Confirm later" → sync | SMS sent; when delivered the consent becomes confirmed; with no delivery for 7 days it shows under "Waiting for confirmation" as unconfirmed | P2 |
| SM-03 | STOP with code | From the person's phone send `STOP <code>` | That consent's optional uses withdrawn; a withdrawal confirmation SMS | P2 |
| SM-04 | STOP n, DATA, HELP | Send `STOP 2`, `DATA`, `HELP` | Withdraws use number 2; opens an access request; opens a grievance | P2 |
| SM-05 | Missed call | Give a missed call to the missed-call number | A withdrawal request opens in the inbox (never applied without staff) | P2 |

## 10. Security and data protection

| ID | Scenario | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| SE-01 | API needs login | Call `/api/method/anumati.api.v1.consent.check` without a token | 401 or 403 | P0 |
| SE-02 | Public verify only | `consent.verify` with a receipt hash, no login | Says whether it's on the chain and the signature is valid; no personal data | P1 |
| SE-03 | No personal data in messages log | Console → Communications for an SMS sent | Phone number not shown (hash only); one-time codes shown as `******` | P0 |
| SE-04 | Worker can't send another worker's code | Field worker B tries to send a code for worker A's consent (API) | Refused | P1 |
| SE-05 | Worker-phone code needs voice | API: record a consent with `device_sms_otp` and no audio evidence | Refused | P1 |
| SE-06 | Names encrypted | Database / report view of Beneficiary | Name and phone stored encrypted; whole-word name search still works | P1 |
| SE-07 | Check before use | API `consent.check` for an adult's granted, unconfirmed use with "Allow processing before confirmation" off | `allow: false`, `awaiting_confirmation`; on: `allow: true` | P1 |

## Reporting a bug

Give the test ID, the phone model and Android version, online or offline, the receipt code if any, and a screenshot (cover any real phone number).
