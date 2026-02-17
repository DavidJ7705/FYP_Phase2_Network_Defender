"""FastAPI dashboard for CAGE4 Network Defense — serves HTML + state JSON."""
import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

BRIDGE_DIR = Path(__file__).parent
STATE_FILE = BRIDGE_DIR / "state.json"
HTML_FILE  = BRIDGE_DIR / "templates" / "dashboard.html"


def read_state() -> dict:
    if not STATE_FILE.exists():
        return {
            "step": 0, "max_steps": 20, "running": False,
            "node_statuses": {}, "highlighted_nodes": {},
            "last_blue_action": {"type": "—", "target": "Waiting for agent…"},
            "last_red_action": {},
            "red_fsm": {"K": 0, "S": 0, "U": 0, "R": 0},
            "events": [],
            "timestamp": datetime.now().isoformat(),
        }
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception as e:
        return {"error": str(e)}


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=HTML_FILE.read_text())


@app.get("/api/state", response_class=JSONResponse)
async def api_state():
    return read_state()


if __name__ == "__main__":
    import uvicorn
    print("Dashboard → http://localhost:5001", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=5001)
