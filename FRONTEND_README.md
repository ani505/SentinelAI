# Frontend

Built with React 18 and Create React App. No extra UI libraries — just plain CSS with a glass-morphism dark theme.

## Setup

```bash
cd frontend
npm install
npm start
```

Runs on `http://localhost:3000`. Expects the backend at `http://localhost:8000`.

## Structure

```
frontend/
├── public/
│   └── index.html       # HTML shell
└── src/
    ├── index.js         # React entry point
    ├── App.jsx          # Everything - single component app
    └── App.css          # All styles
```

## Changing the API key

The demo key is hardcoded at the top of `App.jsx`:

```js
const API_KEY = 'demo_key_12345';
```

Change it to match whatever is set in `API_KEYS` in your `.env`.

## Changing the backend URL

Also at the top of `App.jsx`:

```js
const API_BASE = 'http://localhost:8000/api';
```

## Building for production

```bash
npm run build
```

Outputs to `frontend/build/`. Serve that folder with any static file server (nginx, serve, etc.).

## Supported file types for upload

`.pth` `.pt` `.pkl` `.bin` `.onnx` `.joblib` `.safetensors`

This is enforced both in the file input `accept` attribute and server-side in `config.py`.
