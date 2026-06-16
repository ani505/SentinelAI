# SentinelAI — Feature Overview

## What's in this project

### Model Metadata
Each model can be registered with a description, owner name, and comma-separated tags. Tags are stored as a JSON array in SQLite and returned as a list via the API. Version numbers are assigned automatically — re-registering the same model ID creates v2, v3, etc.

### Search & Filter
`GET /api/models` accepts `?search=`, `?tag=`, and `?owner=` query params. Search runs against model ID, name, and description. Filters can be combined. The frontend applies them in real time as you type.

### Analytics Dashboard
`GET /api/analytics` returns aggregate counts: total models, total verifications, pass/fail breakdown, success rate, blockchain tx count, and the 5 most recent audit events. The frontend polls this after every register, verify, or tamper action.

### CSV Export
`GET /api/export/verification-report` streams a CSV of the audit log. Optionally scope it to one model with `?model_id=`. The file downloads directly in the browser.

### Batch Verification
`POST /api/verify/batch` takes a JSON list of model IDs and checks each one against the stored file on disk — no file upload needed. Returns per-model pass/fail and a summary count.

### Tamper Demo
`POST /api/demo/tamper?model_id=` makes a temp copy of the model file, appends a known byte sequence to the copy, hashes both, compares them, then deletes the copy. The original file is never modified. Useful for showing live that hash changes are caught.

### Blockchain (optional)
Set `SEPOLIA_RPC_URL`, `PRIVATE_KEY`, and `CONTRACT_ADDRESS` in `.env` to enable on-chain registration. Without these, the system works in local-only mode — everything still registers and verifies correctly, just without the Ethereum anchor.

## API endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET  | `/` | — | Status and feature list |
| GET  | `/api/health` | — | DB and blockchain status |
| POST | `/api/register` | ✓ | Register a model file |
| POST | `/api/verify` | ✓ | Verify a model file |
| POST | `/api/verify/batch` | ✓ | Batch verify by model IDs |
| GET  | `/api/models` | ✓ | List models with search/filter |
| GET  | `/api/models/{id}` | ✓ | Full detail + all versions |
| GET  | `/api/models/{id}/audit` | ✓ | Audit log for one model |
| GET  | `/api/analytics` | ✓ | Dashboard stats |
| GET  | `/api/export/verification-report` | ✓ | CSV download |
| POST | `/api/demo/tamper` | ✓ | Non-destructive tamper demo |

Auth = `X-API-Key` header required.
