# ProvePR — Security & permissions

ProvePR is designed as a **reviewer service**, not a ticket rewriter or status machine.

## Permission matrix (what ProvePR does)

| System | ProvePR needs | ProvePR must NOT |
|--------|----------------|------------------|
| **Jira** | **Read** issue summary/description/subtasks + best-effort Development panel; **write issue comments only** for the soft PRD quality gate | Create/edit/transition/delete issues or fields; bounce tickets backlog ↔ To Do |
| **GitHub** | Read PR + diff; **write PR comments** when `--post` / Action publish / skip-notify | Push code, merge, change settings, delete repos |
| **Slack** | Optional: DM via bot (`chat:write`, `im:write`) | Post to product channels unless you later choose that |
| **Gemini** | Call generate API with your key | N/A |
| **Cloud Run trigger** | Caller must send `Authorization: Bearer PROVEPR_TRIGGER_SECRET` | Public unauthenticated `/v1/review` or `/v1/prd-gate` |

## Jira: mostly read; comments only for PRD gate

[`src/provepr/jira_client.py`](src/provepr/jira_client.py) exposes **GET** helpers plus **`add_comment`** for the Story PRD gate.

ProvePR **never** transitions issues (no moving To Do → Backlog). Soft gate only.

**Important:** A Jira API token inherits **whatever your Atlassian user can do**. Prefer a bot that can **Browse + Comment** but not Edit/Transition.

### Recommended company setup

1. Create a dedicated Atlassian user (e.g. `provepr-bot@company.com`) **or** a bot account.
2. Grant **Browse projects** + **Add comments** on boards ProvePR should review.
3. Optionally grant **View Development Tools** for Development-panel advisory on PRs.
4. Do **not** grant Create issues, Edit issues, Transition issues, or Administer projects.
5. Create the API token **as that bot user**.
6. Put that token in Cloud Run / GitHub Actions secrets — never in git.

Demo tickets (PROV-*) were created manually during sandbox setup; that is **not** a ProvePR product feature.

## GitHub: minimal write

For posting review comments the token needs permission to comment on PRs, e.g.:

- Fine-grained PAT: Repository access to target repos; **Issues: Read and write** (PR comments use the issues API) + **Pull requests: Read**
- Or classic PAT: `repo` (narrower fine-grained is preferred for company)

Actions can use the default `GITHUB_TOKEN` with `pull-requests: write` (already set in our workflow).

## Secrets never in the image

The Docker image must **not** contain `.env`. Cloud Run / Actions inject secrets at runtime. See [`.dockerignore`](./.dockerignore).

## Trigger secret

`PROVEPR_TRIGGER_SECRET` protects `POST /v1/review` and `POST /v1/prd-gate`. Treat it like a password. Rotate if leaked.

## If a token was pasted in chat

Rotate it in GitHub / Jira / Slack / Google and update `.env` + any cloud secrets.
