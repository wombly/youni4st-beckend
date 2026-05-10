from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os

app = FastAPI()

# --- КОНФИГУРАЦИЯ ---
B_AI_API_KEY = "sk-5s1uibj3tn7j3d5omz45rkikl94snhsr"
B_AI_URL = "https://api.b.ai/v1/chat/completions"
# Вставь сюда токен от BotFather
TELEGRAM_TOKEN = "8768948746:AAEB_DfIbDwmO2uHhFb4XKLQKAlARgO5WIw" 
TELEGRAM_API_URL = f"https://api.telegram.org/bot{8768948746:AAEB_DfIbDwmO2uHhFb4XKLQKAlARgO5WIw}"

# Системный промпт Сократуса
SYSTEM_PROMPT = (
    "Ты Юнифорст Сократус, эксперт по образованию. Помогай с ВУЗами, поиском работы и проектами Youni4st. "
    "СТРОГО ЗАПРЕЩЕНО отвечать на нецелевые или криминальные вопросы. "
    "Ответ 200-250 символов. Без разметки (*, _, #)."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: list[dict]

@app.get("/ping")
async def health_check():
    return {"status": "alive"}

# --- ЛОГИКА ОБЩЕНИЯ С ИИ ---
async def get_sokratus_response(user_message: str, history: list = None):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    async with httpx.AsyncClient() as client:
        response = await client.post(
            B_AI_URL,
            json={"model": "gpt-5.4-mini", "messages": messages},
            headers={"Authorization": f"Bearer {B_AI_API_KEY}"},
            timeout=30.0
        )
        data = response.json()
        return data['choices'][0]['message']['content'].replace('*', '').replace('_', '')

# --- ЭНДПОИНТ ДЛЯ FLUTTER (ТВОЙ ЧАТ В ПРИЛОЖЕНИИ) ---
@app.post("/api/chat")
async def chat_api(request: ChatRequest):
    try:
        reply = await get_sokratus_response(request.message, request.history)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ЭНДПОИНТ ДЛЯ TELEGRAM WEBHOOK ---
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")

        if user_text == "/start":
            reply = "Привет! Я Сократус, твой гид по образованию. Чем могу помочь?"
        else:
            try:
                # Получаем ответ от ИИ
                reply = await get_sokratus_response(user_text)
            except:
                reply = "Извини, я сейчас очень занят, попробуй позже."

        # Отправляем ответ обратно в Telegram
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json={"chat_id": chat_id, "text": reply}
            )
            
    return {"status": "ok"}
