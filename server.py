from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve favicon
@app.get("/favicon.ico")
async def favicon():
    path = os.path.join(os.getcwd(), "favicon.ico")
    if os.path.exists(path):
        return FileResponse(path)
    return HTMLResponse(status_code=404)

# Serve index.html
@app.get("/", response_class=HTMLResponse)
async def get_index():
    path = os.path.join(os.getcwd(), "index.html")
    if not os.path.exists(path):
        return HTMLResponse("<h1>index.html not found</h1>", status_code=404)
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# In-memory chat storage
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
    new_msgs = [msg for msg in messages if msg["id"] > since]
    next_index = messages[-1]["id"] if messages else 0
    return {"messages": new_msgs, "next_index": next_index}

# Only used locally; not by Render
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
