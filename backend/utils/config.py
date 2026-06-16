import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Blockchain settings - loaded from .env
SEPOLIA_RPC_URL  = os.getenv("SEPOLIA_RPC_URL", "")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000")
PRIVATE_KEY      = os.getenv("PRIVATE_KEY", "")

# ABI for the deployed SentinelAI.sol contract
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_modelHash", "type": "bytes32"},
            {"internalType": "string",  "name": "_modelName", "type": "string"}
        ],
        "name": "registerModel",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "_modelHash", "type": "bytes32"}],
        "name": "verifyModel",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "_modelHash", "type": "bytes32"}],
        "name": "isModelRegistered",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "_modelHash", "type": "bytes32"}],
        "name": "getModelDetails",
        "outputs": [
            {"internalType": "address", "name": "registeredBy", "type": "address"},
            {"internalType": "uint256", "name": "registeredAt",  "type": "uint256"},
            {"internalType": "string",  "name": "modelName",     "type": "string"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "internalType": "bytes32", "name": "hash",         "type": "bytes32"},
            {"indexed": True,  "internalType": "address", "name": "registeredBy", "type": "address"},
            {"indexed": False, "internalType": "string",  "name": "modelName",    "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp",    "type": "uint256"}
        ],
        "name": "ModelRegistered",
        "type": "event"
    }
]

# API keys - comma-separated in .env, e.g. API_KEYS=key1,key2
# Default key matches the frontend demo key
_raw = os.getenv("API_KEYS", "demo_key_12345")
API_KEYS = set(k.strip() for k in _raw.split(",") if k.strip())

# Server
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

# File upload limits
SUPPORTED_FORMATS = {".pth", ".pt", ".pkl", ".bin", ".onnx", ".joblib", ".safetensors"}
MAX_FILE_SIZE = 1_000 * 1024 * 1024  # 1 GB


def validate_config():
    """
    Called at startup. Warns about missing blockchain config but doesn't crash -
    the app works fine in local-only mode without blockchain.
    Only hard-fails if API_KEYS is empty (would lock everyone out).
    """
    warnings = []

    if not SEPOLIA_RPC_URL:
        warnings.append("SEPOLIA_RPC_URL not set - blockchain features disabled.")
    elif "YOUR_INFURA_KEY" in SEPOLIA_RPC_URL:
        warnings.append("SEPOLIA_RPC_URL still has placeholder - replace with your real key.")

    if not PRIVATE_KEY:
        warnings.append("PRIVATE_KEY not set - blockchain writes disabled.")

    if CONTRACT_ADDRESS == "0x0000000000000000000000000000000000000000":
        warnings.append("CONTRACT_ADDRESS is zero address - deploy the contract first.")

    for w in warnings:
        print(f"[CONFIG WARNING] {w}", flush=True)

    if not API_KEYS:
        print("[FATAL] API_KEYS is empty - cannot start safely.", flush=True)
        sys.exit(1)
