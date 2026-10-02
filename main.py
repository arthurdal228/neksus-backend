import os
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="NEKSUS ELD Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DRIVERS = [
    {
        "id": "D001", "name": "Demo Driver 01", "carrier": "NEKSUS",
        "status": "ON", "truck": "TRK-101", "trailer": "TRL-201",
        "location_text": "Dallas, TX", "latitude": 32.7767, "longitude": -96.7970,
        "connected": True, "certified": True, "timezone": "America/Chicago",
        "revision": 1,
    },
    {
        "id": "D002", "name": "Demo Driver 02", "carrier": "NEKSUS",
        "status": "DR", "truck": "TRK-102", "trailer": "TRL-202",
        "location_text": "Houston, TX", "latitude": 29.7604, "longitude": -95.3698,
        "connected": True, "certified": True, "timezone": "America/Chicago",
        "revision": 1,
    },
]

CLIENTS = set()

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def hos_for(driver_id):
    driver = next((d for d in DRIVERS if d["id"] == driver_id), None)
    if not driver:
        raise HTTPException(404, "Driver not found")
    return {
        "driver_id": driver_id,
        "break_remaining": 480,
        "drive_remaining": 660,
        "shift_remaining": 840,
        "cycle_remaining": 4200,
        "current_status": driver["status"],
        "as_of": now_iso(),
        "revision": 1,
    }

@app.get("/")
def root():
    return {"service": "NEKSUS ELD Backend", "status": "ok"}

@app.get("/health")
def health():
    return {"status": "ok", "time": now_iso()}

@app.get("/v1/drivers")
def drivers(limit: int = 500):
    return {"drivers": DRIVERS[:max(0, limit)]}

@app.get("/v1/alerts")
def alerts(status: str = "open"):
    return {"alerts": []}

@app.get("/v1/fleet/live")
def fleet_live():
    return {"drivers": DRIVERS}

@app.get("/v1/hos/current")
def hos_current():
    return {"hos": [hos_for(d["id"]) for d in DRIVERS]}

@app.get("/v1/drivers/{driver_id}/hos")
def driver_hos(driver_id: str):
    return hos_for(driver_id)

@app.get("/v1/drivers/{driver_id}/logs/{date}")
def driver_log(driver_id: str, date: str):
    driver = next((d for d in DRIVERS if d["id"] == driver_id), None)
    if not driver:
        raise HTTPException(404, "Driver not found")
    return {
        "driver_id": driver_id,
        "date": date,
        "timezone": driver["timezone"],
        "revision": 1,
        "segments": [],
        "events": [],
        "hos": hos_for(driver_id),
    }

@app.websocket("/v1/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    CLIENTS.add(ws)
    try:
        await ws.send_json({"type": "connected", "ts": now_iso()})
        while True:
            message = await ws.receive_json()
            if message.get("type") == "ping":
                await ws.send_json({"type": "pong", "ts": now_iso()})
            elif message.get("type") == "authenticate":
                await ws.send_json({"type": "authenticated"})
            elif message.get("type") == "subscribe":
                await ws.send_json({
                    "type": "subscription.confirmed",
                    "topics": message.get("topics", [])
                })
    except WebSocketDisconnect:
        pass
    finally:
        CLIENTS.discard(ws)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
