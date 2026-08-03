# KodiQA — GitHub App setup (no second personal account)

ProvePR posts PR comments using whatever GitHub credential is configured.
To show **KodiQA[bot]** (not your personal username), use a **GitHub App** owned by your account.

## Create the App (once)

1. Sign into GitHub as yourself (`hmik2003` / Kodifly account).
2. Open: https://github.com/settings/apps/new  
   (or Organization → Settings → Developer settings → GitHub Apps → New)
3. Fill in:
   - **GitHub App name:** `KodiQA` (must be unique on GitHub; try `KodiQA-Kodifly` if taken)
   - **Homepage URL:** `https://github.com/hmik2003/ProvePR`
   - **Webhook:** uncheck Active (not required for commenting)
4. **Repository permissions:**
   - **Issues:** Read & write (PR comments use the Issues API)
   - **Pull requests:** Read-only
   - **Metadata:** Read-only (default)
5. **Where can this App be installed?** Only on this account (or Kodifly org).
6. Create GitHub App → **Generate a private key** → download the `.pem` (keep secret).
7. Note **App ID** on the app settings page.
8. Click **Install App** → install on `hmik2003/ProvePR` and `hmik2003/provepr-demo-shop` (and later pilot repos).
9. After install, the URL looks like  
   `https://github.com/settings/installations/12345678`  
   That number is **Installation ID**.

## Configure ProvePR

### Local / Cloud Run `.env`

```env
GITHUB_APP_ID=123456
GITHUB_APP_INSTALLATION_ID=12345678
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
```

(You can leave `GITHUB_TOKEN` empty when App env is set.)

### GitHub Actions secrets (per repo)

| Secret | Value |
|--------|--------|
| `KODIQA_APP_ID` | App ID |
| `KODIQA_APP_PRIVATE_KEY` | Full PEM contents |

Workflow mints a short-lived token via `actions/create-github-app-token` so comments appear as **KodiQA[bot]**.

## Verify

After a review or skip-notify run, the PR comment author should be **`KodiQA[bot]`**, and the body title **KodiQA review** / **KodiQA skipped**.
