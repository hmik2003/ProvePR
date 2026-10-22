# KodiQA — GitHub App setup

ProvePR posts PR comments using the **KodiQA** GitHub App so comments appear as **`kodiqa[bot]`** (not a personal username).

## Ownership (company rule)

| Stage | Owner |
|-------|--------|
| Personal / sandbox | Was: `hmik2003` |
| **Wrong transfer (2026-09-10)** | `ibrahimkayani-kodifly` — this is a **user**, not the org |
| **Company** | **Kodifly organization** (`github.com/Kodifly`) |

`ibrahimkayani-kodifly` is your work **login**. Membership in Kodifly ≠ App owned by Kodifly. If you leave, a user-owned App + private key leave with you.

CTO requirement: App registration must be owned by the **Kodifly org**. Transfer destination must show type **Organization**, not User.

### Transfer to Kodifly org (current owner: `ibrahimkayani-kodifly`)

Docs: [Transferring ownership of a GitHub App](https://docs.github.com/en/apps/maintaining-github-apps/transferring-ownership-of-a-github-app)

1. Sign in as the **current App owner** (`ibrahimkayani-kodifly`).
2. Open: https://github.com/settings/apps/kodiqa  
   (or Settings → Developer settings → GitHub Apps → **KodiQA**)
3. Left sidebar → **Advanced**
4. **Transfer ownership**
5. Type / select **`Kodifly`**. Confirm the row is the **organization** (not your user, not an enterprise with the same name). If GitHub blocks the transfer, ask an org owner to make you a GitHub App manager.
6. Read any uninstall warning (personal installs on `ProvePR` / `provepr-demo-shop` may be removed — reinstall later on personal if still needed for sandbox)
7. **Transfer this GitHub App**
8. If the org must **accept** the transfer, ask a Kodifly org owner (CTO) to accept, then ping him to install

After transfer, manage the App under:  
**Kodifly → Settings → Developer settings → GitHub Apps → KodiQA**

### Install on company pilot

1. Install App on **Kodifly** → only **`getsifu-dev`** (not the other Sifu repos, not prod).
2. Note new **Installation ID** from the install URL (`…/installations/<id>`).
3. Update Cloud Run / `.env`: `GITHUB_APP_INSTALLATION_ID=<new id>` (App ID + private key usually stay the same after transfer; regenerate key only if rotated).

---

## Permissions (locked — match CTO ask)

| Permission | Level | Why |
|------------|-------|-----|
| **Pull requests** | **Read & write** | Required to post PR comments (`kodiqa[bot]`). Does **not** mean merge / approve / push. |
| **Metadata** | Read-only | Default |
| **Issues** | **None** | Dropped after first successful company smoke (2026-09-14). PR write is enough for comments. |
| **Webhooks** | Off | Not used |

**Do not** request Contents write, Administration, or Workflows. We do **not** merge, approve, or push code.

---

## Create the App (historical / new apps)

1. Prefer creating under **Kodifly** org (Settings → Developer settings → GitHub Apps → New).
2. Name: `KodiQA` (or `KodiQA-Kodifly` if taken)
3. Homepage: company ProvePR repo URL once moved; until then personal is fine
4. Webhook: uncheck Active
5. Permissions: table above
6. Generate private key → store only in Cloud Run / local `.env` (never commit)
7. Note **App ID**; after install note **Installation ID**

## Configure ProvePR

### Local / Cloud Run `.env`

```env
GITHUB_APP_ID=123456
GITHUB_APP_INSTALLATION_ID=12345678
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
```

(You can leave `GITHUB_TOKEN` empty when App env is set.)

### GitHub Actions (thin Cloud Run path)

Repos only need:

| Secret | Value |
|--------|--------|
| `PROVEPR_URL` | Cloud Run base URL |
| `PROVEPR_TRIGGER_SECRET` | Same Bearer as Cloud Run |

No App PEM on the repo when using `/v1/pr-hook` — Cloud Run holds the App credentials.

## Company pilot scope (Sifu)

- Repo: **`getsifu-dev` only**
- Trigger: PR → **`staging`**
- Other Sifu repos + `main`: out of scope

## Verify

After a review or skip-notify run, the PR comment author should be **`kodiqa[bot]`**, body titled **KodiQA review** / **KodiQA skipped**.
