# Quick Start

## Prerequisites

- Python 3.8+
- Node.js 16+

## 1. Start the Backend

```bash
cd backend
pip install -r requirements.txt
python api_enhanced.py
```

You should see:
```
Starting AiSync server...
API docs at http://localhost:8000/docs
```

If you get config warnings about SEPOLIA_RPC_URL or PRIVATE_KEY, that's fine - the app works without blockchain. See `.env.example` to set those up.

## 2. Start the Frontend

```bash
cd frontend
npm install
npm start
```

Opens at `http://localhost:3000`.

## 3. Try It Out

**Register a model:**
1. Fill in Model ID (e.g. `test_model_1`)
2. Fill in Model Name (e.g. `My First Model`)
3. Optionally add description, owner, tags
4. Choose any file (a `.txt` works fine for testing)
5. Click Register

**Verify a model:**
- Click ✅ Verify on any registered model
- Select the same file you uploaded
- Should show "VERIFIED - Model integrity confirmed"

**Tamper demo:**
- Click 🚨 Demo Tamper on any model
- AiSync copies the file, modifies the copy, compares hashes
- Your original file is never touched

**Export:**
- Click Export Report to download a CSV of all activity

## Default API Key

```
demo_key_12345
```

## Troubleshooting

**Backend won't start:** Make sure you're in the `backend` directory. Try `python3` if `python` doesn't work.

**Frontend blank:** Check the browser console. Make sure backend is running at port 8000.

**CORS errors:** Backend runs with CORS open for all origins - should work fine locally. If not, try a different browser.

**"Module not found":** Run `pip install -r requirements.txt` again.
