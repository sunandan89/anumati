# Setup guide — click by click

No installs and no terminal. Everything happens in GitHub and Frappe Cloud in your browser. You never paste a key anywhere: the signing key is generated on the server when the app installs, and provider credentials (SMS, WhatsApp) go straight into encrypted fields in Anumati later.

Button labels can shift slightly as GitHub and Frappe Cloud update their screens. If a label differs, look for the closest match in the same place.

---

## A. Merge the Phase 0 branch into `main`

The website deploys and Frappe Cloud builds from `main`.

1. Open **github.com/sunandan89/anumati**.
2. You'll see a yellow banner: **claude/frappe-v15-phase-0-vmwcow had recent pushes** → click **Compare & pull request**.
   (No banner? Click **Pull requests** → **New pull request** → set *compare* to `claude/frappe-v15-phase-0-vmwcow` → **Create pull request**.)
3. Click **Create pull request**.
4. Wait for the checks at the bottom to go green: **Static checks** and **Frappe tests and security gates** (about 15–20 minutes the first time).
5. Click **Merge pull request** → **Confirm merge**.

## B. Make CI block merges (branch protection)

Do this after the checks have run at least once (step A4), so GitHub knows their names.

1. In the repo, click **Settings** (top bar) → **Branches** (left sidebar).
2. Click **Add classic branch protection rule**. (If you only see **Add branch ruleset**, use that: target branch `main`, then the same options below.)
3. **Branch name pattern**: `main`.
4. Tick **Require a pull request before merging**.
5. Tick **Require status checks to pass before merging**, then tick **Require branches to be up to date before merging**.
6. In the search box under it, type and select **Static checks**, then **Frappe tests and security gates**.
7. Tick **Do not allow bypassing the above settings**.
8. Click **Create** (or **Save changes**).

From now on nothing reaches `main` unless the security tests pass: unauthenticated routes return 401/403, tenants are isolated, the ledgers are insert-only, and tampering with the chain is detected.

## C. Publish the website on GitHub Pages

1. In the repo: **Settings** → **Pages** (left sidebar).
2. Under **Build and deployment** → **Source**, choose **GitHub Actions**. Nothing else to fill in.
3. Click **Actions** (top bar) → **Website** (left list) → **Run workflow** → branch `main` → **Run workflow**.
   (It also runs by itself whenever something under `site/` changes on `main`.)
4. When it goes green, open the run: the page address is shown under **deploy**. It will be
   **https://sunandan89.github.io/anumati/**
5. The clickable prototype is at **…/anumati/prototype/**. The site's "Try the field app", "Docs" and "Sign in" buttons open it until the real console is live.

**Two settings for later:** the sandbox form's email address, and the "Sign in" link (your Frappe Cloud site). Send them to me in chat and I'll set them. They aren't secrets.

**Custom domain (optional):** Settings → Pages → **Custom domain** → enter e.g. `anumati.org` → **Save**, then add the DNS record GitHub shows at your domain registrar. Tick **Enforce HTTPS** once it appears.

## D. Deploy the server on Frappe Cloud (Mumbai)

A custom app needs a **private bench group** on Frappe Cloud, which is on a paid plan. Choose the plan when prompted.

### D1. Create the bench group

1. Go to **frappecloud.com** → **Log in** (or **Sign up**; Google login works).
2. Left sidebar → **Bench Groups** → **New Bench Group** (top right).
3. **Title**: `anumati-v15`.
4. **Version**: **Version 15**.
5. **Region**: **Mumbai** (India, ap-south-1). This keeps data in India (spec §9, residency).
6. Leave **Frappe** as the only app for now → **Create Bench Group**.

### D2. Connect the GitHub repo and add the app

1. Open the new bench group → **Apps** tab → **Add App**.
2. Choose **Add from GitHub** → **Connect to GitHub**. A GitHub page opens to install the **Frappe Cloud** GitHub app.
3. On GitHub: choose the account **sunandan89** → **Only select repositories** → pick **anumati** → **Install**. You return to Frappe Cloud.
4. Pick repository **anumati**, branch **main** → **Validate App** (it checks for `hooks.py` and `pyproject.toml`) → **Add App**.

### D3. Deploy

1. Still in the bench group, click **Deploy** (top right; it may read **Update Available**).
2. Tick **anumati** → **Deploy**.
3. Watch the **Deploys** tab. It takes about 10–15 minutes. Wait until the status reads **Success**.

### D4. Create the first tenant site

Each organisation gets its own site. That's the tenant boundary the CI tests prove.

1. In the bench group → **Sites** tab → **New Site**.
2. **Subdomain**: e.g. `aaroh-pilot` (becomes `aaroh-pilot.frappe.cloud`; a custom domain can come later).
3. Under apps, tick **Anumati** → **Create Site**. Wait until it shows **Active**.
4. Open the site dashboard → **Login as Administrator**.

What happens on install, automatically:
- The site's own Ed25519 signing key and phone-hash salt are generated and stored encrypted. You never see them or paste them.
- Roles (Anumati Admin, DPO, Operator, Programme Manager, Field Worker, Developer, Auditor, Processor Partner, Funder Viewer), the **Notice Publishing** and **ROPA Approval** workflows, and custom fields are installed.
- Two-factor login is switched on. Users with the Admin, DPO, Operator or Programme Manager role set up an authenticator app on first login.

### D5. First steps inside the site

1. Search bar → **Anumati Settings** → fill **Organisation legal name**, **DPO name/email** → **Save**. The *Signing key* section shows the key ID; that's all you need to see.
2. Search bar → **User List** → **Add User** for your DPO → **Roles**: tick **Anumati DPO** → **Save**.
3. To limit someone to one programme: search **User Permission** → **New** → User, *Allow* = **Programme**, *For Value* = the programme → **Save**.

### D6. Later deploys

Every merge to `main` shows **Update Available** on the bench group. Click **Deploy** → **anumati** → **Deploy**. Sites update after the deploy; migrations run automatically.

---

## If something goes wrong

- **CI red on a pull request:** open the failing check → the last step's log names the failed gate (e.g. `FAIL: tenant-a key reading tenant-b event -> 200`). Share that line with me.
- **Frappe Cloud deploy fails:** Deploys tab → the failed deploy → copy the last 30 lines of the log to me. Never paste anything from *Site Config* or any key.

---

## E. SMS with MSG91 (receipts, OTP, STOP keyword, missed calls)

Nothing is sent until all four pieces exist: an MSG91 account, DLT-approved templates, a Channel Provider in Anumati, and approved Message Templates. Until then, capture keeps working and simply sends no SMS.

### E1. MSG91 and DLT (outside Anumati)
1. Sign up at **msg91.com** and complete KYC.
2. Register your organisation as a **DLT principal entity** on a telecom DLT portal (e.g. Jio, Vodafone Idea, Airtel), and register a **sender ID** (header, e.g. `AAROHF`).
3. Register one **content template** per message, per language. The four you need first:
   - Receipt: `Consent {#var#} for {#var#}: {#var#}. Reply STOP to withdraw.`
   - Withdrawal confirmation: `Withdrawn: {#var#} ({#var#}).`
   - OTP: `Your code is {#var#}.`
   - Deferred confirmation: `You consented on {#var#} to {#var#}. Reply STOP to withdraw.`
4. In MSG91, create a **Flow** for each approved DLT template and note each flow's **template ID**.
5. In MSG91 → **API**, copy your **Auth Key**. You'll type it straight into Anumati in E2. Never paste it in chat or email.

### E2. Channel Provider (in your Anumati site)
1. Search bar → **Channel Provider** → **+ Add**.
2. **Name** `MSG91`, **Type** `SMS`, **Provider** `MSG91`, tick **Enabled**.
3. **Sender ID**: your DLT header. **DLT entity ID**: from the DLT portal.
4. **API key**: paste the MSG91 Auth Key. It's stored encrypted and shows as dots afterwards.
5. **Inbound webhook secret**: type a long random phrase (20+ characters). SMS callbacks must carry it.
6. **Save**.

### E3. Message Templates (in Anumati)
For each message and language: search bar → **Message Template** → **+ Add**:
- **Event**: `receipt`, `withdrawal_confirmation`, `otp` or `deferred_confirmation`.
- **Channel** `sms`, **Language** (e.g. `hi`).
- **DLT template ID**: the MSG91 **flow template ID** from E1 step 4.
- **Body**: the same text, with these placeholders: `{{ code }}` (receipt code), `{{ programme }}`, `{{ purposes }}`, `{{ date }}`, `{{ otp }}`. They go to MSG91 in this order as var1…var5.
- Tick **Approved** only once DLT has approved the template. Unapproved templates are never sent.

### E4. Inbound SMS and missed calls (in MSG91)
MSG91 → **Inbound SMS** (long code or virtual number) → set the callback URL:
```
https://<your-site>/api/method/anumati.api.v1.channel.inbound_sms?provider=MSG91&token=<your inbound secret>
```
For missed calls, point your missed-call number's webhook to `…/anumati.api.v1.channel.missed_call?provider=MSG91&token=<secret>`. For delivery reports, use `…/anumati.api.v1.channel.delivery_report?provider=MSG91&token=<secret>`.

What people can text to the number (English or Devanagari digits):
- `STOP`: stop all optional uses. If several people share that phone, it goes to your inbox to resolve.
- `STOP AN-7K2Q9C`: stop the consent on that receipt.
- `STOP 2`: stop only the 2nd item on the receipt.
- `DATA`: ask what you hold. `HELP`: ask for a call-back.

A missed call always opens a withdrawal request in the inbox. A person confirms it with the caller before recording it.

### E5. Per programme
**Programme → Send SMS receipts** is on by default. Untick it for programmes that shouldn't send SMS.

---

## F. Field app server side (Anumati Collect)

The app signs in through **Frappe Mobile Control** (`dhwani-ris/frappe-mobile-control`, AGPL). It's a separate app that goes on the same bench. Anumati doesn't depend on it; only the phone does.

### F1. Add Mobile Control to the bench group
1. Frappe Cloud → your bench group → **Apps** tab → **Add App**.
2. **Add from GitHub** → paste `https://github.com/dhwani-ris/frappe-mobile-control` (public, so no GitHub permission needed) → branch **develop** → **Validate App** → **Add App**.
3. **Deploy** (top right) → tick **frappe-mobile-control** and **anumati** → **Deploy**. Wait for **Success**.

### F2. Install it on your site
1. Bench group → **Sites** → your site → **Apps** tab → **Install App** → **Mobile Control** → **Install**.

### One click instead of F3–F5 (pilot or demo)
Log in to your site as **Administrator** → search bar → **Anumati Settings** → **Actions** → **Set up field app** → **Yes**.
It switches on Mobile Configuration for Anumati Collect, creates the fictional **DEMO** programme with a published notice and a reviewed Hindi translation, and creates the test field worker `fieldworker.demo@example.com`. A box shows the organisation address, user ID and a new password: type them into the app. The password is shown only once; run it again for a new one.

### Without logging in to the site (Frappe Cloud dashboard only)
1. Frappe Cloud → **Sites** → your site → **Site Config** tab → **Add Config**.
2. Key: choose **Custom key**, type `anumati_demo_password`. Value: the password you want for the test field worker (type it here yourself). **Save**.
3. Site → **Actions** (or **⋯**) → **Migrate** (or deploy the bench group again).
On that migrate, the site switches on Mobile Configuration, creates the DEMO programme with its published notice, and sets up `fieldworker.demo@example.com` with your password. Delete the key after the pilot so a later migrate doesn't reset the password.

### F3. Switch the app on (inside your site)
1. Search bar → **Mobile Configuration**.
2. Tick **Enabled**. Leave **Offline Mode Enabled** unticked: Anumati Collect keeps its own encrypted offline store.
3. **Package Name**: `org.anumati.collect`. **Minimum App Version**: `1.0.0` (raise it later to force old phones to update).
4. **Save**.

### F4. Create a field worker
1. Search bar → **User List** → **Add User**. Email or username, first name. **Save**.
2. On the user → **Roles**: tick **Anumati Field Worker** and **Mobile User** (Mobile User comes from Mobile Control; without it the app refuses to sign in). **Save**.
3. Set a password: the user form → **Settings / Change Password**, or send the welcome email.
4. To limit the worker to their programmes: search **User Permission** → **New** → User, *Allow* = **Programme**, *For Value* = the programme → **Save**. Repeat per programme.

### F5. What the app needs from the programme
- A **published** notice (Notice Template → Publish). The app shows the live notice and its purposes.
- For Hindi: a **Notice Translation** in `hi` with a named **Reviewer**. Unreviewed translations and machine-made audio are never sent to phones.

### Phones and lost phones
Every phone that signs in appears under **Field Device** with its user, app version, last sync and how many records it still holds. If a phone is lost or stolen: open it → **Report lost** → **Yes**. The phone signs out and deletes its data the next time it connects, and a **Breach Incident** (lost device) opens with the number of records it hadn't synced, so the 72-hour clock starts.

### Receipt codes work offline
The code on the slip (e.g. `AN-7K2Q9C`) is worked out on the phone from the consent's ID, so the worker can write it down before the phone syncs. The server gets the same code. Codes are short, so two people can rarely share one: an SMS `STOP <code>` is then matched by the sender's number, or goes to the inbox for a person to resolve.

## G. The Desk menu: who sees what

After the deploy, the left sidebar has six Anumati sections. Each person sees only the sections for their role. What they can open or change inside a section is still set by the permissions on each record type.

| Section | What's in it | Operator | Programme Manager | DPO | Admin |
|---|---|:-:|:-:|:-:|:-:|
| **Today** | Needs attention, requests board, key numbers, Getting started (admins, until done) | ✓ | ✓ | ✓ | ✓ |
| **Beneficiaries** | Beneficiaries, consents, guardians, receipt lookup | ✓ | ✓ | ✓ | ✓ |
| **Programmes** | Programmes, re-consent campaigns, field phones | | ✓ | view | ✓ |
| **Analytics** | Counts and charts, never names | | ✓ | ✓ | ✓ |
| **Notices and Compliance** | Notices and translations, purposes, records of processing and DPIA, retention, processors, breaches, audit log, access log | | view | ✓ | view |
| **Setup** | Organisation, team, SMS and messaging, message templates, connected systems | | | | ✓ |

Admins can read the DPO's records but only the DPO publishes notices and approves records of processing. Field workers use the phone app and see no Desk sections.

Useful places:
- **Today → Requests board**: drag a request between columns to change its status. Red cards are overdue.
- **Consents list**: type a receipt code (e.g. `AN-7K2Q9C`) in the box at the top. Saved views such as *Withdrawals* and *Guardian consents* are in the left sidebar under **Saved Filters**.
- **A request from a shared phone**: open it → **Who is this for?** → pick the person → **Match**.
- **A breach**: the form shows the hours left of the 72-hour deadline. Click **Board told now** when you have told the Board.
