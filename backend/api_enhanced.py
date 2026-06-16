import os
import sys
import csv
import shutil
import secrets
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from io import StringIO

from fastapi import (
    FastAPI, File, UploadFile, HTTPException,
    Depends, Header, Request, Query, Form
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import (
    SEPOLIA_RPC_URL, CONTRACT_ADDRESS, CONTRACT_ABI, PRIVATE_KEY,
    SUPPORTED_FORMATS, MAX_FILE_SIZE, API_KEYS, validate_config
)
from utils.hashing import generate_hash
from utils.database_enhanced import DatabaseEnhanced
from blockchain.web3_handler import Web3Handler

validate_config()

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="SentinelAI API",
    description="AI Model Integrity Verification System",
    version="3.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DatabaseEnhanced()
web3 = Web3Handler(SEPOLIA_RPC_URL, CONTRACT_ADDRESS, CONTRACT_ABI, PRIVATE_KEY)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# --- Auth ---

def require_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key


# --- File validation ---

async def validate_model_file(file: UploadFile) -> bytes:
    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(SUPPORTED_FORMATS)}"
        )
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        size_mb = len(content) / (1024 * 1024)
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.2f} MB). Max allowed: {max_mb:.2f} MB"
        )
    return content


# --- Pydantic models ---

class BatchVerificationRequest(BaseModel):
    model_ids: List[str]


# --- Routes ---

@app.get("/")
async def root():
    return {
        "service": "SentinelAI",
        "status": "running",
        "version": "3.0.0",
        "blockchain_connected": web3.is_connected(),
        "features": [
            "Search & Filter",
            "Model Metadata",
            "Export Reports",
            "Batch Verification",
            "Analytics Dashboard"
        ]
    }


@app.get("/api/health")
async def health():
    stats = db.get_statistics()
    return {
        "status": "healthy",
        "db": "connected",
        "blockchain": "connected" if web3.is_connected() else "disconnected",
        "total_models": stats["total_models"],
        "total_verifications": stats["total_verifications"]
    }


@app.post("/api/register")
@limiter.limit("30/minute")
async def register_model(
    request: Request,
    model_id: str = Form(...),
    model_name: str = Form(...),
    description: Optional[str] = Form(None),
    owner: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    file: UploadFile = File(...),
    _key: str = Depends(require_api_key)
):
    try:
        content = await validate_model_file(file)
    except HTTPException as e:
        return {"status": "error", "message": e.detail, "error_type": "validation_error"}

    existing = db.get_model_versions(model_id)
    version = len(existing) + 1

    file_path = UPLOAD_DIR / f"{model_id}_v{version}_{file.filename}"
    file_path.write_bytes(content)

    model_hash = generate_hash(str(file_path))
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    tx_hash = None
    etherscan_url = None
    blockchain_ok = False

    if web3.is_connected():
        try:
            tx_hash = web3.register_model(model_hash, model_name)
            etherscan_url = f"https://sepolia.etherscan.io/tx/{tx_hash}"
            blockchain_ok = True
        except Exception as e:
            print(f"Blockchain write failed: {e}")

    db.register_model(
        model_id=model_id,
        model_name=model_name,
        version=version,
        file_path=str(file_path),
        model_hash=model_hash,
        file_size=len(content),
        tx_hash=tx_hash,
        description=description,
        owner=owner,
        tags=tag_list
    )

    db.log_event(
        event_type="REGISTER",
        model_id=model_id,
        version=version,
        model_hash=model_hash,
        result="SUCCESS",
        blockchain_tx=tx_hash,
        notes=f"blockchain={'ok' if blockchain_ok else 'skipped'}, owner={owner}"
    )

    return {
        "status": "success",
        "message": "Model registered successfully",
        "model_id": model_id,
        "model_name": model_name,
        "version": version,
        "hash": model_hash[:16] + "...",
        "full_hash": model_hash,
        "file_size": len(content),
        "file_size_mb": round(len(content) / (1024 * 1024), 2),
        "blockchain_registered": blockchain_ok,
        "tx_hash": tx_hash,
        "etherscan_url": etherscan_url,
        "metadata": {
            "description": description,
            "owner": owner,
            "tags": tag_list
        }
    }


@app.post("/api/verify")
@limiter.limit("60/minute")
async def verify_model(
    request: Request,
    model_id: str = Form(...),
    version: Optional[int] = Form(None),
    file: UploadFile = File(...),
    _key: str = Depends(require_api_key)
):
    content = await validate_model_file(file)

    record = db.get_model(model_id, version)
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_id}' not found. Register it first."
        )

    tmp = UPLOAD_DIR / f"_verify_{secrets.token_hex(8)}"
    tmp.write_bytes(content)
    try:
        current_hash = generate_hash(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)

    registered_hash = record["model_hash"]
    is_valid = current_hash == registered_hash

    blockchain_verified = False
    if web3.is_connected():
        try:
            blockchain_verified = web3.verify_model(registered_hash)
        except Exception:
            pass

    status_str = (
        "VERIFIED - Model integrity confirmed" if is_valid
        else "TAMPERING DETECTED - Hash mismatch"
    )

    db.log_event(
        event_type="VERIFY",
        model_id=model_id,
        version=record["version"],
        model_hash=current_hash,
        result="PASS" if is_valid else "FAIL",
        blockchain_tx=record.get("tx_hash"),
        notes=f"blockchain_verified={blockchain_verified}"
    )

    return {
        "model_id": model_id,
        "version": record["version"],
        "is_valid": is_valid,
        "status": status_str,
        "registered_hash": registered_hash[:16] + "...",
        "current_hash": current_hash[:16] + "...",
        "blockchain_verified": blockchain_verified,
        "tx_hash": record.get("tx_hash"),
        "etherscan_url": (
            f"https://sepolia.etherscan.io/tx/{record['tx_hash']}"
            if record.get("tx_hash") else None
        )
    }


@app.post("/api/verify/batch")
@limiter.limit("20/minute")
async def batch_verify(
    request: Request,
    body: BatchVerificationRequest,
    _key: str = Depends(require_api_key)
):
    """Verify multiple models at once without uploading files - checks stored hash vs file on disk."""
    results = []

    for model_id in body.model_ids:
        record = db.get_model(model_id)
        if not record:
            results.append({"model_id": model_id, "status": "error", "message": "Model not found"})
            continue

        file_path = Path(record["file_path"])
        if not file_path.exists():
            results.append({"model_id": model_id, "status": "error", "message": "Model file missing from disk"})
            continue

        current_hash = generate_hash(str(file_path))
        is_valid = current_hash == record["model_hash"]

        results.append({
            "model_id": model_id,
            "version": record["version"],
            "is_valid": is_valid,
            "status": "Valid" if is_valid else "Tampered",
            "hash": record["model_hash"][:16] + "..."
        })

    return {
        "total": len(results),
        "verified": sum(1 for r in results if r.get("is_valid")),
        "failed": sum(1 for r in results if not r.get("is_valid") and r.get("status") != "error"),
        "errors": sum(1 for r in results if r.get("status") == "error"),
        "results": results
    }


@app.get("/api/models")
@limiter.limit("60/minute")
async def list_models(
    request: Request,
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    _key: str = Depends(require_api_key)
):
    models = db.list_models(search=search, tag=tag, owner=owner)
    return {
        "models": models,
        "total": len(models),
        "filters_applied": {"search": search, "tag": tag, "owner": owner}
    }


@app.get("/api/models/{model_id}")
@limiter.limit("60/minute")
async def get_model_detail(
    request: Request,
    model_id: str,
    _key: str = Depends(require_api_key)
):
    versions = db.get_model_versions(model_id)
    if not versions:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    latest = versions[-1]
    return {
        "model_id": model_id,
        "model_name": latest["model_name"],
        "description": latest.get("description"),
        "owner": latest.get("owner"),
        "tags": latest.get("tags", []),
        "total_versions": len(versions),
        "latest_version": latest["version"],
        "latest_hash": latest["model_hash"],
        "latest_tx_hash": latest.get("tx_hash"),
        "etherscan_url": (
            f"https://sepolia.etherscan.io/tx/{latest['tx_hash']}"
            if latest.get("tx_hash") else None
        ),
        "created_at": latest.get("created_at"),
        "file_size_mb": round(latest.get("file_size", 0) / (1024 * 1024), 2),
        "versions": versions
    }


@app.get("/api/analytics")
@limiter.limit("30/minute")
async def get_analytics(
    request: Request,
    _key: str = Depends(require_api_key)
):
    stats = db.get_statistics()
    recent = db.get_audit_log(model_id=None, limit=10)

    return {
        "overview": {
            "total_models": stats["total_models"],
            "total_versions": stats["total_versions"],
            "total_verifications": stats["total_verifications"],
            "successful_verifications": stats["successful_verifications"],
            "failed_verifications": stats["failed_verifications"],
            "success_rate": round(stats["success_rate"], 2) if stats["success_rate"] else 0
        },
        "blockchain": {
            "connected": web3.is_connected(),
            "total_blockchain_tx": stats.get("blockchain_transactions", 0)
        },
        "recent_activity": recent[:5]
    }


@app.get("/api/export/verification-report")
@limiter.limit("10/minute")
async def export_verification_report(
    request: Request,
    model_id: Optional[str] = Query(None),
    format: str = Query("csv"),
    _key: str = Depends(require_api_key)
):
    events = db.get_audit_log(model_id=model_id, limit=1000)

    if format.lower() != "csv":
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'csv'.")

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "timestamp", "event_type", "model_id", "version",
        "model_hash", "result", "blockchain_tx", "notes"
    ])
    writer.writeheader()
    for event in events:
        writer.writerow({
            "timestamp":    event.get("timestamp", ""),
            "event_type":   event.get("event_type", ""),
            "model_id":     event.get("model_id", ""),
            "version":      event.get("version", ""),
            "model_hash":   (event.get("model_hash", "") or "")[:16] + "...",
            "result":       event.get("result", ""),
            "blockchain_tx": event.get("blockchain_tx", ""),
            "notes":        event.get("notes", "")
        })

    output.seek(0)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"aisync_report_{model_id or 'all'}_{ts}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.post("/api/demo/tamper")
@limiter.limit("10/minute")
async def simulate_tampering(
    request: Request,
    model_id: str,
    _key: str = Depends(require_api_key)
):
    """
    Non-destructive tamper demo - makes a temp copy, modifies the copy,
    compares hashes, then deletes the copy. Original file is never touched.
    """
    record = db.get_model(model_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")

    original_path = Path(record["file_path"])
    if not original_path.exists():
        raise HTTPException(status_code=404, detail="Model file missing from disk.")

    tmp_path = UPLOAD_DIR / f"_tamper_{secrets.token_hex(8)}{original_path.suffix}"
    shutil.copy2(original_path, tmp_path)

    try:
        original_hash = generate_hash(str(original_path))

        with open(tmp_path, "ab") as f:
            f.write(b"\x00TAMPERED_BY_AISYNC_DEMO\x00")

        tampered_hash = generate_hash(str(tmp_path))
    finally:
        tmp_path.unlink(missing_ok=True)

    detected = original_hash != tampered_hash

    db.log_event(
        event_type="TAMPER_DEMO",
        model_id=model_id,
        version=record["version"],
        model_hash=tampered_hash,
        result="DETECTED" if detected else "MISSED",
        notes="non-destructive demo"
    )

    return {
        "status": "success",
        "message": "Tampering demonstration completed",
        "model_id": model_id,
        "version": record["version"],
        "original_hash": original_hash[:16] + "...",
        "tampered_hash": tampered_hash[:16] + "...",
        "hash_mismatch": detected,
        "would_be_blocked": detected,
        "original_file_safe": True,
        "explanation": "In production, this tampered model would be rejected during verification."
    }


@app.get("/api/models/{model_id}/audit")
@limiter.limit("30/minute")
async def get_audit_log(
    request: Request,
    model_id: str,
    limit: int = 50,
    _key: str = Depends(require_api_key)
):
    events = db.get_audit_log(model_id, limit=limit)
    return {"model_id": model_id, "events": events, "total": len(events)}


if __name__ == "__main__":
    import uvicorn
    print("Starting SentinelAI server...")
    print("API docs at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
