from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os, asyncio, sys

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get():
    path = os.path.join("static", "index.html")
    if not os.path.exists(path):
        return HTMLResponse("<h1>index.html not found</h1>", status_code=404)
    return HTMLResponse(open(path, encoding="utf-8").read())

class ConnectionManager:
    def __init__(self):
        self.active: dict[WebSocket, int] = {}
        self.next_id = 1
        self.lock = asyncio.Lock()
        self.history: list[str] = []

    async def connect(self, ws: WebSocket) -> int:
        # 1) Accept with ngrok header to skip warning page
        await ws.accept(headers=[(b"ngrok-skip-browser-warning", b"1")])

        # 2) Assign numeric ID
        async with self.lock:
            uid = self.next_id
            self.next_id += 1
            self.active[ws] = uid

        # 3) Replay history
        for line in self.history:
            await ws.send_text(line)
        return uid

    def disconnect(self, ws: WebSocket) -> int | None:
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

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    uid = await mgr.connect(ws)
    await mgr.broadcast(f"** #{uid} joined **")

    try:
        while True:
            data = await ws.receive_text()
            text = data.strip()

            # ignore client-side clear attempts
            if text == "__clear__":
                continue

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

# Background CLI listener for "clear" and "exit"
async def command_line_listener():
    print("Command line listener started. Type 'clear' to clear chat.")
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        cmd = line.strip().lower()
        if cmd == "clear":
            print("Clearing chat history and notifying clients...")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
