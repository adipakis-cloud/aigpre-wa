import os
import httpx
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import anthropic

app = FastAPI()

FONNTE_TOKEN = os.getenv("FONNTE_TOKEN", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PORT = int(os.getenv("PORT", "8005"))

SYSTEM_PROMPT = """You are AIGPRE Assistant — the AI representative of AIGPRE Global Trade Platform.

AIGPRE is a professional B2B commodity brokerage platform connecting verified buyers and suppliers of strategic industrial commodities: Nickel, Coal, Copper, Bauxite, and other minerals.

Your role:
- Respond professionally to all inquiries in the same language as the sender
- For commodity trade inquiries: collect key details (commodity, volume, delivery terms, timeline)
- For general questions: explain AIGPRE's services briefly and direct to trade@aigpre.com
- Always be concise — WhatsApp messages should be short and clear
- Never make specific price commitments — say "our trade team will follow up with detailed pricing"
- End every response with: "For formal inquiries: trade@aigpre.com | aigpre.com"

AIGPRE Services:
- Nickel Ore & NPI supply facilitation
- Thermal Coal supply agreements
- Copper & industrial minerals
- Verified supplier network
- Structured deal facilitation

Tone: Professional, concise, institutional."""

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

async def send_whatsapp(target: str, message: str):
    if not FONNTE_TOKEN:
        print("[ERROR] FONNTE_TOKEN not set")
        return
    async with httpx.AsyncClient() as http:
        try:
            resp = await http.post(
                "https://api.fonnte.com/send",
                headers={"Authorization": FONNTE_TOKEN},
                data={"target": target, "message": message},
                timeout=30
            )
            print(f"[FONNTE SEND] status={resp.status_code} body={resp.text[:100]}")
        except Exception as e:
            print(f"[FONNTE ERROR] {e}")

def get_ai_reply(sender: str, message: str) -> str:
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Message from {sender}:\n{message}"}]
        )
        return response.content[0].text
    except Exception as e:
        print(f"[AI ERROR] {e}")
        return "Thank you for contacting AIGPRE. Our trade team will respond shortly. For urgent inquiries: trade@aigpre.com"

@app.post("/webhook")
async def webhook(request: Request):
    try:
        content_type = request.headers.get("content-type", "")
        print(f"[WEBHOOK] content-type: {content_type}")

        # Try form data first
        sender = ""
        message = ""

        if "application/json" in content_type:
            data = await request.json()
            print(f"[WEBHOOK JSON] {str(data)[:200]}")
            sender = data.get("sender", "") or data.get("from", "") or data.get("phone", "")
            message = data.get("message", "") or data.get("text", "") or data.get("pesan", "")
        else:
            data = await request.form()
            raw = dict(data)
            print(f"[WEBHOOK FORM] {str(raw)[:200]}")
            sender = raw.get("sender", "") or raw.get("from", "") or raw.get("phone", "")
            message = raw.get("message", "") or raw.get("text", "") or raw.get("pesan", "")

        print(f"[PARSED] sender={sender} message={str(message)[:100]}")

        if not sender or not message:
            print("[SKIP] No sender or message found")
            return JSONResponse({"status": "ok"})

        print(f"[AIGPRE WA] Message from {sender}: {str(message)[:80]}")

        reply = get_ai_reply(sender, message)
        await send_whatsapp(sender, reply)
        print(f"[AIGPRE WA] Reply sent to {sender}")

        return JSONResponse({"status": "ok"})

    except Exception as e:
        print(f"[WEBHOOK ERROR] {e}")
        return JSONResponse({"status": "error", "message": str(e)})

@app.get("/health")
async def health():
    return {
        "status": "online",
        "service": "AIGPRE WhatsApp AI",
        "fonnte": "configured" if FONNTE_TOKEN else "missing",
        "claude": "configured" if ANTHROPIC_KEY else "missing"
    }

@app.get("/")
async def root():
    return {"service": "AIGPRE WhatsApp AI — Railway Production v2"}

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("AIGPRE WhatsApp AI — Railway Production v2")
    print(f"Fonnte : {'ACTIVE' if FONNTE_TOKEN else 'MISSING'}")
    print(f"Claude : {'ACTIVE' if ANTHROPIC_KEY else 'MISSING'}")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=PORT)
