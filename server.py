from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# Allow CORS for frontend (adjust origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For testing, replace with your domain for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from 'static' folder
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/favicon.ico")
async def favicon():
    path = os.path.join("static", "favicon.ico")
    if os.path.exists(path):
        return FileResponse(path)
    return HTMLResponse(status_code=404)

@app.get("/")
async def get():
    path = os.path.join("static", "index.html")
    if not os.path.exists(path):
        return HTMLResponse("<h1>index.html not found in static folder</h1>", status_code=404)
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# In-memory message store with IDs for polling
messages = []
message_id = 0

@app.post("/send")
async def send_message(request: Request):
    global message_id
    data = await request.json()
    username = data.get("username")
    text = data.get("text")

    if not username or not text:
        return {"status": "error", "message": "username and text required"}

    message_id += 1
    messages.append({"id": message_id, "username": username, "text": text})
    print(f"[MESSAGE] {username}: {text}")
    return {"status": "ok"}

@app.get("/messages")
async def get_messages(since: int = 0):
    # Return all messages with id > since
    new_msgs = [msg for msg in messages if msg["id"] > since]
    next_index = messages[-1]["id"] if messages else 0
    return {"messages": new_msgs, "next_index": next_index}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
