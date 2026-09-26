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
