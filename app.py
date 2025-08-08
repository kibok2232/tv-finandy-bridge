import json, logging
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
import httpx
import os

app = FastAPI(title="TradingView → Finandy Bridge")

# ==== ① 환경변수에서 secret→url 매핑 읽기 ====
SECRET_TO_URL: Dict[str, str] = json.loads(os.getenv("SECRET_MAP", "{}"))

TIMEOUT = float(os.getenv("FORWARD_TIMEOUT", "6.0"))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bridge")

@app.post("/tv")
async def tv_webhook(req: Request):
    try:
        payload: Dict[str, Any] = await req.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    secret = str(payload.get("secret", "")).strip()
    if not secret:
        raise HTTPException(400, "Missing 'secret'")
    if secret not in SECRET_TO_URL:
        raise HTTPException(403, f"Unknown secret: {secret}")

    target = SECRET_TO_URL[secret]
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(target, json=payload)
        if not (200 <= r.status_code < 300):
            log.error("Finandy error %s: %s", r.status_code, r.text[:200])
            raise HTTPException(r.status_code, f"Finandy returned {r.status_code}")
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Forwarding failed")
        raise HTTPException(502, f"Forwarding failed: {e}")

    return {"status": "ok", "routed_to": target, "secret": secret}
