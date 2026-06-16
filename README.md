# SentinelAI

AI Model Integrity Verification on Blockchain

SentinelAI lets you register AI model files and verify they haven't been tampered with. Each model gets a SHA-256 hash that can optionally be anchored to the Ethereum Sepolia testnet. If someone modifies the model file later, the hash won't match and the system flags it.

## Features

- **Register models** with metadata (name, description, owner, tags)
- **Verify integrity** by re-hashing and comparing against the stored hash
- **Blockchain anchoring** via Sepolia testnet (optional - works locally too)
- **Search & filter** models by name, tag, or owner
- **Analytics dashboard** showing verification stats and blockchain status
- **Audit log** with exportable CSV reports
- **Tamper demo** for presentations (non-destructive)
- **Batch verification** to check multiple models at once

## Project Structure

```
SentinelAI/
├── backend/
│   ├── api_enhanced.py          # FastAPI server - all routes here
│   ├── utils/
│   │   ├── config.py            # Env vars and startup validation
│   │   ├── database_enhanced.py # SQLite with search and analytics
│   │   └── hashing.py           # SHA-256 utilities
│   ├── blockchain/
│   │   └── web3_handler.py      # Ethereum/Web3 integration
│   └── requirements.txt
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.jsx              # Main React component
│   │   ├── index.js             # Entry point
│   │   └── App.css              # Styles
│   └── package.json
├── blockchain/
│   └── contracts/
│       └── SentinelAI.sol       # Solidity smart contract
└── .env.example
```

## Quick Start

### Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Copy env file and optionally add blockchain keys
cp ../.env.example .env

# Start the server
python api_enhanced.py
```

Server runs at `http://localhost:8000`
Interactive API docs at `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm start
```

Opens at `http://localhost:3000`

## Configuration

Copy `.env.example` to `.env` in the project root or backend folder.

| Variable | Required | Description |
|---|---|---|
| `SEPOLIA_RPC_URL` | No | Infura/Alchemy endpoint. Blank = local-only mode |
| `CONTRACT_ADDRESS` | No | Your deployed SentinelAI.sol address |
| `PRIVATE_KEY` | No | Wallet private key for signing transactions |
| `API_KEYS` | Yes | Comma-separated API keys. Default: `demo_key_12345` |

The system works without blockchain - models are stored locally in SQLite. Blockchain is optional extra security.

## API Reference

All endpoints require `X-API-Key` header.

| Endpoint | Method | Description |
|---|---|---|
| `/api/register` | POST | Register model file with metadata |
| `/api/verify` | POST | Verify file against stored hash |
| `/api/verify/batch` | POST | Check multiple model IDs at once |
| `/api/models` | GET | List models (supports `?search=`, `?tag=`, `?owner=`) |
| `/api/models/{id}` | GET | Full detail for one model |
| `/api/models/{id}/audit` | GET | Audit log for a model |
| `/api/analytics` | GET | Dashboard stats |
| `/api/export/verification-report` | GET | Download CSV audit trail |
| `/api/demo/tamper` | POST | Non-destructive tamper demonstration |
| `/api/health` | GET | Health check |

### Example: Register a model

```bash
curl -X POST http://localhost:8000/api/register \
  -H "X-API-Key: demo_key_12345" \
  -F "model_id=resnet18_v1" \
  -F "model_name=ResNet18 Classifier" \
  -F "owner=Jane Doe" \
  -F "tags=pytorch,vision" \
  -F "file=@model.pth"
```

### Example: Verify a model

```bash
curl -X POST http://localhost:8000/api/verify \
  -H "X-API-Key: demo_key_12345" \
  -F "model_id=resnet18_v1" \
  -F "file=@model.pth"
```

## Database Schema

### models
```sql
model_id TEXT, model_name TEXT, version INTEGER,
file_path TEXT, model_hash TEXT, file_size INTEGER,
tx_hash TEXT, description TEXT, owner TEXT,
tags TEXT (JSON array), created_at TIMESTAMP
```

### audit_log
```sql
timestamp TIMESTAMP, event_type TEXT, model_id TEXT,
version INTEGER, model_hash TEXT, result TEXT,
blockchain_tx TEXT, notes TEXT
```

## Supported File Types

`.pth` `.pt` `.pkl` `.bin` `.onnx` `.joblib` `.safetensors`

Max file size: 1 GB

## Running Without Blockchain

Leave `SEPOLIA_RPC_URL` and `PRIVATE_KEY` blank. The system runs in local-only mode:
- Models are registered and verified using local SQLite
- Hashes are stored but not anchored on-chain
- All other features work normally

## Smart Contract

`blockchain/contracts/SentinelAI.sol` - deploy this to Sepolia if you want on-chain anchoring. After deployment, put the contract address in `CONTRACT_ADDRESS` in your `.env`.

## Tech Stack

Python 3.8+, FastAPI, SQLite, Web3.py, React 18, Ethereum Sepolia
