from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx # Используем асинхронный клиент

app = FastAPI()

# --- КОНФИГУРАЦИЯ ---
# ТВОЙ_ТЕЛЕГРАМ_ТОКЕН - возьми его у BotFather
TELEGRAM_TOKEN = "ТВОЙ_ТОКЕН_ОТ_BOTFATHER"
B_AI_API_KEY = "sk-5s1uibj3tn7j3d5omz45rkikl94snhsr"
B_AI_URL = "https://api.b.ai/v1/chat/completions"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Разрешаем CORS
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

# --- ЛОГИКА ИИ ---
async def get_sokratus_response(message: str, history: list = None):
    system_prompt = {
        "role": "system",
        "content": (
            "Ты Юнифорст Сократус, эксперт по образованию. Помогай с ВУЗами, поиском работы и проектами Youni4st. "
            "СТРОГО ЗАПРЕЩЕНО отвечать на нецелевые или криминальные вопросы. "
            "Ответ 200-250 символов. Без разметки (*, _, #)."
        )
    }
    messages = [system_prompt]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    async with httpx.AsyncClient() as client:
        response = await client.post(
            B_AI_URL,
            json={"model": "gpt-5.4-mini", "messages": messages},
            headers={"Authorization": f"Bearer {B_AI_API_KEY}"},
            timeout=30.0
        )
        data = response.json()
        return data['choices'][0]['message']['content'].replace('*', '').replace('_', '')

# --- ЧАТ ДЛЯ FLUTTER ПРИЛОЖЕНИЯ ---
@app.post("/api/chat")
async def chat_api(request: ChatRequest):
    try:
        reply = await get_sokratus_response(request.message, request.history)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ОБРАБОТЧИК ДЛЯ ТЕЛЕГРАМ (WEBHOOK) ---
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        
        # Если это данные из твоего Mini App (sendData)
        if "web_app_data" in data["message"]:
            app_data = data["message"]["web_app_data"]["data"]
            # Тут логика обработки данных из твоего Flutter-приложения
            reply = f"Получил данные из Mini App: {app_data}"
        else:
            # Обычное текстовое сообщение
            user_text = data["message"].get("text", "")
            if user_text == "/start":
                reply = "Привет! Я Сократус. Открой меню, чтобы запустить Mini App, или спроси меня об образовании."
            else:
                try:
                    reply = await get_sokratus_response(user_text)
                except:
                    reply = "Сейчас я занят, попробуй позже."

        # Отправка ответа пользователю в Телеграм
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json={"chat_id": chat_id, "text": reply}
            )
            
    return {"status": "ok"}
