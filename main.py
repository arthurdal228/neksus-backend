import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="NEKSUS ELD API", version="3.0.0")

# Frontend may be hosted on Netlify, Vercel, or another HTTPS host.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No hard-coded demo drivers.
# Real driver records should be supplied by the ELD/dispatch system.
drivers: List[Dict[str, Any]] = []


@app.get("/")
def root():
    return {
        "service": "NEKSUS ELD API",
        "status": "ok",
        "version": app.version,
        "drivers": len(drivers),
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/drivers")
def get_drivers():
    return JSONResponse(
        {
            "drivers": drivers,
            "total": len(drivers),
        }
    )


@app.get("/v1/drivers/{driver_id}")
def get_driver(driver_id: str):
    for driver in drivers:
        if str(driver.get("id")) == str(driver_id):
            return driver

    return JSONResponse(
        status_code=404,
        content={"detail": "Driver not found"},
    )


@app.get("/v1/drivers/{driver_id}/logs")
def get_driver_logs(
    driver_id: str,
    date: Optional[str] = None,
):
    for driver in drivers:
        if str(driver.get("id")) == str(driver_id):
            return {
                "driverId": driver_id,
                "date": date,
                "events": [],
                "segments": [],
                "source": "eld",
            }

    return JSONResponse(
        status_code=404,
        content={"detail": "Driver not found"},
    )


@app.get("/v1/drivers/{driver_id}/hos")
def get_driver_hos(
    driver_id: str,
    date: Optional[str] = None,
):
    for driver in drivers:
        if str(driver.get("id")) == str(driver_id):
            # Empty HOS response until a real ELD source is connected.
            return {
                "driverId": driver_id,
                "date": date,
                "segments": [],
                "totals": {
                    "OFF": 0,
                    "SB": 0,
                    "DR": 0,
                    "ON": 0,
                },
                "source": "eld",
            }

    return JSONResponse(
        status_code=404,
        content={"detail": "Driver not found"},
    )


@app.websocket("/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    await websocket.send_json(
        {
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    try:
        while True:
            message = await websocket.receive_json()

            action = message.get("action")

            if action == "ping":
                await websocket.send_json(
                    {
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            elif action == "drivers":
                await websocket.send_json(
                    {
                        "type": "drivers",
                        "drivers": drivers,
                        "total": len(drivers),
                    }
                )
            else:
                await websocket.send_json(
                    {
                        "type": "ack",
                        "action": action,
                    }
                )

    except Exception:
        # Client disconnected.
        return


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
    )
