from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, List, Optional
import os, asyncio, sys

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── 1) Global middleware: add ngrok header to every HTTP response ──────────────
@app.middleware("http")
async def add_ngrok_skip_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "69420"
    return response

# ── 2) Serve index.html ───────────────────────────────────────────────────────
@app.get("/")
async def get_index():
    path = os.path.join("static", "index.html")
    if not os.path.exists(path):
        return HTMLResponse("<h1>index.html not found</h1>", status_code=404)
    return HTMLResponse(open(path, encoding="utf-8").read())

# ── 3) Connection manager with history + ngrok header on WS.accept ──────────
class ConnectionManager:
    def __init__(self):
        self.active: Dict[WebSocket, int] = {}
        self.next_id = 1
        self.lock = asyncio.Lock()
        self.history: List[str] = []

    async def connect(self, ws: WebSocket) -> int:
        # Skip ngrok’s browser warning on WS handshake:
        await ws.accept(headers=[(b"ngrok-skip-browser-warning", b"1")])

        async with self.lock:
            uid = self.next_id
            self.next_id += 1
            self.active[ws] = uid

        # Replay last 250 messages
        for line in self.history:
            await ws.send_text(line)
        return uid

    def disconnect(self, ws: WebSocket) -> Optional[int]:
        return self.active.pop(ws, None)

    async def broadcast(self, msg: str, store: bool = False):
        if store:
            self.history.append(msg)
            if len(self.history) > 250:
                self.history.pop(0)

        dead = []
        for sock in list(self.active):
            try:
                await sock.send_text(msg)
            except:
                dead.append(sock)
        for sock in dead:
            self.active.pop(sock, None)

    async def clear_history(self):
        self.history.clear()
        dead = []
        for sock in list(self.active):
            try:
                await sock.send_text("__clear__")
            except:
                dead.append(sock)
        for sock in dead:
            self.active.pop(sock, None)

mgr = ConnectionManager()

# ── 4) WebSocket endpoint ─────────────────────────────────────────────────────
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    uid = await mgr.connect(ws)
    await mgr.broadcast(f"** #{uid} joined **")

    try:
        while True:
            data = await ws.receive_text()
            text = data.strip()

            # ignore client clear attempts
            if text == "__clear__":
                continue

            # broadcast real messages
            if text and not text.startswith("__"):
                line = f"#{uid}: {text}"
                await mgr.broadcast(line, store=True)

    except WebSocketDisconnect:
        left = mgr.disconnect(ws)
        if left is not None:
            await mgr.broadcast(f"** #{left} left **")
    except Exception:
        left = mgr.disconnect(ws)
        if left is not None:
            await mgr.broadcast(f"** #{left} left due to error **")

# ── 5) CLI listener to clear or exit ──────────────────────────────────────────
async def command_line_listener():
    print("Command line listener started. Type 'clear' to clear chat or 'exit' to quit.")
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        cmd = line.strip().lower()
        if cmd == "clear":
            print("Clearing chat history...")
            await mgr.clear_history()
            await mgr.broadcast("** Chat cleared by server command **")
        elif cmd in ("quit", "exit"):
            print("Shutting down server...")
            os._exit(0)
        else:
            print(f"Unknown command: {cmd}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(command_line_listener())

# ── 6) Run the server ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
