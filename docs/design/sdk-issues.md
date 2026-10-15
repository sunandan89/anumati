# Issues to raise on dhwani-ris/frappe-mobile-sdk

Drafted from a read of `frappe_mobile_sdk` 2.0.0-beta.4 (merge `ea162ec`) for the Anumati move onto the
SDK. File references are to that version. Post #1 privately (GitHub → Security → Report a
vulnerability, or to the maintainers directly), not as a public issue.

---

## 1. (Security, report privately) Login token stored unencrypted and written to the log

**What happens**
- `AuthService._processLoginResponse` stores the access and refresh tokens in the SDK's SQLite database
  (`auth_service.dart:444-465`, `AuthTokenEntity`). The database is plain SQLite, so anyone with the
  phone's files can read a live token.
- `auth_service.dart:288` and `:400` log the token: `dev.log('access_token: $accessToken')`.

**Ask**
- Remove both log lines (and any other token or password logging).
- Keep tokens in `FlutterSecureStorage`, as the OAuth path already does (`auth_service.dart:955-960`),
  or only in an encrypted database (issue 2).

---

## 2. Opt-in encrypted local database (SQLCipher)

**Why:** field apps hold names, phone numbers and survey answers offline. A lost phone should not expose
them.

**Today:** `AppDatabase.getInstance` already takes a `factoryResolver` (`app_database.dart:18-21,
124-166`), but `FrappeSDK` doesn't pass one (`frappe_sdk.dart:412-415`). Anumati works around this by
calling `AppDatabase.getInstance(appName:, factoryResolver:)` before `initialize()`, with a factory that
wraps `sqflite_sqlcipher` and adds the password.

**Ask**
- A `FrappeSDK` setting, for example `databaseFactoryResolver`, passed through at `frappe_sdk.dart:412`.
- A ready option, for example `FrappeSDK(encryptDatabase: true)`: a 32-byte key made on first run and
  kept in secure storage, opened with SQLCipher.
- It is off by default; existing apps are unchanged. A documented path for phones that already have a
  plain database (start fresh on sign-in, or migrate).

**Done when:** an app turns it on with one setting; the database file can't be read without the key.
Anumati's `CipherDatabaseFactory` (packages/anumati_consent in anumati_collect) can be the starting
point.

---

## 3. Personal fields that sync (with Mobile Control)

**Why:** `Password` fields are skipped on purpose (`field_type_mapping.dart:42-50`), and Frappe never
returns them over REST anyway, so encrypted personal fields can't reach the phone at all.

**Ask (design to agree with the SDK team)**
- A field can be marked **personal** in Mobile Control (or as a field property). It is an ordinary Data
  field in the schema.
- **Server (Mobile Control):** encrypted at rest with the site key, plus a salted hash column for exact
  search; sent in clear only to roles the DocType's permission rule allows; each clear read logged.
- **SDK:** stores personal fields only when the local database is encrypted (issue 2), and drops them
  otherwise, as it does `Password` fields now.

**Done when:** a personal field syncs to a permitted field worker, never to others, and never into an
unencrypted phone database.

---

## 4. Encrypted attachments from capture to upload

**Today:** `MediaStore.stageToOutbox` copies captures in plain form to
`<AppDocuments>/mform_attachments/outbox/<uuid>/` (`media_store.dart:15, 161-188`) until upload. Uploads
are private but unattached until Mobile Control relinks them (`attachment_relink.py`).

**Ask**
- Encrypt staged files on the phone (same key as issue 2), and decrypt only in memory for upload or
  preview.
- Optionally, a Mobile Control hook to encrypt private files on the server's disk and log each view
  (Anumati's `evidence.py` does this for its own DocTypes).

**Done when:** no plain copy of a capture exists on the phone at any time, including after a crash.

---

## 5. Write back server-set fields after an insert

**Today:** `ResponseWriteback.applyInTxn` (`response_writeback.dart:45-227`) keeps only `name`,
`modified` and the audit columns from the server's reply. Other fields the server sets on insert (for
Anumati: signature, hash, verification status) arrive only on the next pull.

**Ask:** an opt-in per DocType (or a callback) to write the whole returned document back into the local
row after a successful insert.

**Done when:** a value the server sets on insert shows on the phone right after the push.

---

## 6. Send the device ID with requests

**Today:** the SDK keeps a per-install `mobile_uuid` (`auth_service.dart:222-229`), but no request
carries it. Mobile Control's device log reads it from an `X-Client-Info` header
(`api/helpers/client_log.py`) that the SDK never sends, so devices are hard to tell apart on the server.

**Ask:** send the device ID (and app version) in that header on every request, so Mobile Control's
Mobile Device Log can be the device registry for all apps (Anumati would then drop its own Field Device
check-in).
