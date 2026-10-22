# YOU DO NOW — Transfer KodiQA App + fix scopes

Saad already set secrets. He will **not** install until the App is owned by **Kodifly**.

Do this while signed in as **`hmik2003`** (App owner — not `ibrahimkayani-kodifly`).

---

## Part A — Fix scopes first (2 min)

1. Open: https://github.com/settings/apps/kodiqa  
2. Left sidebar → **Permissions & events**
3. Under **Repository permissions**:
   - **Issues** → **Read and write**
   - **Pull requests** → **Read-only**  ← must not be Read and write
   - **Metadata** → Read-only (leave)
4. Webhooks → leave **Active** unchecked
5. Scroll to bottom → **Save changes**

If GitHub says existing installs need to accept new permissions, that’s fine for personal sandbox; company install comes after transfer.

---

## Part B — Transfer ownership to Kodifly (5 min)

1. Still on the KodiQA App (as `hmik2003`)
2. Left sidebar → **Advanced**
3. Click **Transfer ownership**
4. Under new owner, type **`Kodifly`**
5. From the dropdown, pick the **organization** named Kodifly (not an enterprise with the same name if both show)
6. Read the warning — transfer may uninstall the App from your **personal** account installs (`ProvePR`, `provepr-demo-shop`). Sandbox can be reinstalled later; company pilot is the priority.
7. Click **Transfer this GitHub App**

### If it asks for org acceptance
- Ping Saad: “Transfer sent — please accept KodiQA under Kodifly org settings.”
- Org owners accept under: Org Settings → something like pending transfer / GitHub Apps

### After transfer succeeds
- App settings move to: **Kodifly org → Settings → Developer settings → GitHub Apps → KodiQA**
- Double-check permissions still = Issues write, PRs read
- DM Saad (message below)

---

## Part C — Ping Saad (copy-paste)

```
Done on my side:

1) KodiQA App transferred to Kodifly (or: transfer sent — please accept if it’s waiting on an org owner)
2) Scopes corrected to:
   • Issues: Read & write (PR comments via Issues API only)
   • Pull requests: Read
   • Metadata: Read
   • No PR write

Ready for you to install on getsifu-dev only. After you install I’ll wire the staging workflow + smoke.
```

---

## Part D — After he installs (tell me in chat)

Reply here with:
- “App installed”
- New installation URL or ID if you see it (`…/installations/########`)

Then I will:
1. Add thin workflow to `getsifu-dev` (PR → `staging`)
2. Help smoke a `KS-xxx:` PR
3. Update Cloud Run `GITHUB_APP_INSTALLATION_ID` if comments fail
4. Rotate `PROVEPR_TRIGGER_SECRET` after smoke (call with Saad — not Slack)

---

## What I already did for you (agent)

- Updated `docs/KODIQA_GITHUB_APP.md` (transfer + correct scopes + Sifu scope)
- Updated `PROJECT.md` open items / phase log
- Workflow template ready: `docs/github-action-cloudrun.yml` (`branches: [staging]`)
- Cannot transfer the App without your `hmik2003` browser login (GitHub login wall)
