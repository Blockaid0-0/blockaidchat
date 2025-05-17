# fetch_ngrok.py
import asyncio
import httpx

async def main():
    url = "http://localhost:8000"  # or your ngrok URL
    headers = {
        "ngrok-skip-browser-warning": "69420"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            print("Status:", response.status_code)
            print("Response:")
            print(response.text)  # or response.json() if it's JSON
        except Exception as e:
            print("Error:", e)

asyncio.run(main())
