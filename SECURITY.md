# ProvePR — Security & permissions

ProvePR is designed as a **reviewer service**, not a ticket writer or repo rewriter.

## Permission matrix (what ProvePR does)

| System | ProvePR needs | ProvePR must NOT |
|--------|----------------|------------------|
| **Jira** | **Read** issue summary/description (`GET /rest/api/3/myself`, `GET /rest/api/3/issue/{key}`) | Create/edit/transition/delete issues, comments, or fields |
| **GitHub** | Read PR + diff; **write PR comments** when `--post` / Action publish | Push code, merge, change settings, delete repos |
| **Slack** | Optional: DM via bot (`chat:write`, `im:write`) | Post to arbitrary channels unless you later choose that |
| **Gemini** | Call generate API with your key | N/A |
| **Cloud Run trigger** | Caller must send `Authorization: Bearer PROVEPR_TRIGGER_SECRET` | Public unauthenticated `/v1/review` |

## Jira: read-only in code (already true)

[`src/provepr/jira_client.py`](src/provepr/jira_client.py) only implements **GET**. There is no create/update API in the product.

**Important:** A Jira API token inherits **whatever your Atlassian user can do**. Code being read-only is not enough if the human account can create tickets.

### Recommended company setup

1. Create a dedicated Atlassian user (e.g. `provepr-bot@company.com`) **or** a bot account.
2. Grant that account **Browse projects** / view issues only on the boards ProvePR should read (SpatialSense, Sifu, …).
3. Do **not** grant Create issues, Edit issues, or Administer projects.
4. Create the API token **as that bot user**.
5. Put that token in Cloud Run / GitHub Actions secrets — never in git.

Demo tickets (PROV-*) were created manually during sandbox setup; that is **not** a ProvePR product feature.

## GitHub: minimal write

For posting review comments the token needs permission to comment on PRs, e.g.:

- Fine-grained PAT: Repository access to target repos; **Issues: Read and write** (PR comments use the issues API) + **Pull requests: Read**
- Or classic PAT: `repo` (narrower fine-grained is preferred for company)

Actions can use the default `GITHUB_TOKEN` with `pull-requests: write` (already set in our workflow).

## Secrets never in the image

The Docker image must **not** contain `.env`. Cloud Run / Actions inject secrets at runtime. See [`.dockerignore`](./.dockerignore).

## Trigger secret

`PROVEPR_TRIGGER_SECRET` protects `POST /v1/review`. Treat it like a password. Rotate if leaked.

## If a token was pasted in chat

Rotate it in GitHub / Jira / Slack / Google and update `.env` + any cloud secrets.
