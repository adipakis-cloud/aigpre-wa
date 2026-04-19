import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

FONNTE_TOKEN  = os.getenv("FONNTE_TOKEN", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PORT          = int(os.getenv("PORT", "8080"))

app = FastAPI()

PROVIDERS = """
CATERING JAKARTA:
1. Dapur Menteng - Rp 85.000/porsi - min 50 porsi - WA: 081298342211
2. Katering Bu Sari - Rp 65.000/porsi - min 30 porsi - WA: 081312345678
3. Premium Box - Rp 120.000/porsi - min 20 porsi - WA: 081587654321

PIJAT TRADISIONAL:
1. Pak Hendra Urut Cimande - Rp 350.000/sesi - WA: 089654321098
2. Traditional Massage VVIP - Rp 500.000/sesi - WA: 081234567890

SEWA MOBIL:
1. Jakarta Premium Car - Rp 800.000/hari - WA: 081198765432
2. VIP Transport Alphard - Rp 1.500.000/hari - WA: 082345678901

HOTEL:
1. Hotel Menteng - Rp 800.000/malam - WA: 021-3141516
2. The Sultan Senayan - Rp 2.500.000/malam - WA: 021-5701234

BENGKEL MOBIL MEWAH:
1. Auto Prestige - Kemang - WA: 081345678901
2. European Car Specialist - Sudirman - WA: 081456789012

DEREK 24 JAM:
1. Derek Jakarta - Rp 300.000-800.000 - WA: 081567890123

ARTIS & ENTERTAINMENT:
1. Management Artis Top - Rp 50jt-500jt/show - WA: 082176543210

GOLF:
1. Pondok Indah Golf - Rp 500.000/round - WA: 021-7500234
2. Senayan Golf - Rp 350.000/round - WA: 021-5701111

KARANGAN BUNGA:
1. Florist Premium Jakarta - Rp 200.000-2.000.000 - WA: 081678901234

IKAN SEGAR:
1. TPI Muara Baru - Rp 45.000-180.000/kg - WA: 081387654321
"""

SYSTEM_PROMPT = """Kamu adalah AIGPRE Assistant - layanan All-in-One Service Jakarta & Indonesia.
Tugasmu: membantu pengguna menemukan provider terbaik untuk semua kebutuhan mereka.
Data provider: """ + PROVIDERS + """
Cara menjawab:
- Langsung rekomendasikan provider sesuai kebutuhan
- Tampilkan nama, harga, dan nomor WA provider
- Maksimal 3 pilihan terbaik
- Ramah dan profesional dalam Bahasa Indonesia
- Akhiri dengan: Hubungi langsung atau balas untuk kami proses
Fee AIGPRE 15% sudah termasuk dalam harga."""

history = {}

async def get_ai_response(msg, phone):
    if phone not in history:
        history[phone] = []
    history[phone].append({"role": "user", "content": msg})
    if len(history[phone]) > 10:
        history[phone] = history[phone][-10:]
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": 1000, "system": SYSTEM_PROMPT, "messages": history[phone]},
                timeout=30.0
            )
            data = r.json()
            if r.status_code == 200 and "content" in data:
                reply = data["content"][0]["text"]
            else:
                reply = "Maaf sistem sibuk. Coba lagi atau hubungi adi.pakis@gmail.com"
    except Exception as e:
        reply = "Maaf sistem sibuk. Silakan coba lagi."
    history[phone].append({"role": "assistant", "content": reply})
    return reply

async def send_wa(phone, message):
    try:
        async with httpx.AsyncClient() as client:
            await client.post("https://api.fonnte.com/send",
                headers={"Authorization": FONNTE_TOKEN},
                data={"target": phone, "message": message, "countryCode": "62"},
                timeout=15.0)
    except Exception as e:
        print(f"[ERROR SEND] {e}")

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        phone = data.get("sender", "")
        message = data.get("message", "").strip()
        if not phone or not message:
            return JSONResponse({"status": "ignored"})
        print(f"[WA IN] {phone}: {message}")
        reply = await get_ai_response(message, phone)
        await send_wa(phone, reply)
        print(f"[WA OUT] {phone}: OK")
        return JSONResponse({"status": "ok"})
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)})

@app.get("/")
async def root():
    return {"service": "AIGPRE WhatsApp AI", "status": "running", "wa": "081993811749"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
