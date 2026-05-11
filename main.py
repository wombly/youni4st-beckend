import os
import json
import httpx
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# --- КОНФИГУРАЦИЯ (Через переменные окружения для безопасности) ---
# На Render добавь их в Settings -> Environment Variables
TELEGRAM_TOKEN = os.getenv("8768948746:AAEB_DfIbDwmO2uHhFb4XKLQKAlARgO5WIw")
B_AI_API_KEY = os.getenv("sk-5s1uibj3tn7j3d5omz45rkikl94snhsr")
B_AI_URL = "https://api.b.ai/v1/chat/completions"
TELEGRAM_API_URL = f"https://api.telegram.org/bot8768948746:AAEB_DfIbDwmO2uHhFb4XKLQKAlARgO5WIw"

# Разрешаем CORS для связи с Flutter (Web и Mobile)
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

# --- ЛОГИКА ИИ СОКРАТУС ---
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
        try:
            response = await client.post(
                B_AI_URL,
                json={"model": "gpt-5.4-mini", "messages": messages},
                headers={"Authorization": f"Bearer {B_AI_API_KEY}"},
                timeout=30.0
            )
            data = response.json()
            # Убираем разметку для совместимости с Telegram и Flutter
            reply = data['choices'][0]['message']['content']
            return reply.replace('*', '').replace('_', '').replace('#', '')
        except Exception as e:
            print(f"AI Error: {e}")
            return "Извини, я сейчас не могу ответить. Попробуй позже."

# --- ЭНДПОИНТ ДЛЯ СОХРАНЕНИЯ РЕЗЮМЕ (Убирает ошибку 404) ---
@app.post("/api/resume/save")
async def save_resume(resume_data: dict = Body(...)):
    try:
        # Здесь данные из Flutter (телефон, опыт, навыки и т.д.)
        # Пока просто выводим в консоль сервера для проверки
        print("📥 Получены данные резюме:")
        print(json.dumps(resume_data, indent=2, ensure_ascii=False))
        
        # В будущем здесь будет логика записи в базу данных
        return {"status": "success", "message": "Resume saved successfully"}
    except Exception as e:
        print(f"Save Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

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
        
        if "web_app_data" in data["message"]:
            app_data = data["message"]["web_app_data"]["data"]
            reply = f"Получил данные из Mini App: {app_data}"
        else:
            user_text = data["message"].get("text", "")
            if user_text == "/start":
                reply = "Привет! Я Сократус. Открой меню, чтобы запустить Mini App, или спроси меня об образовании."
            else:
                reply = await get_sokratus_response(user_text)

        # Отправка ответа пользователю в Телеграм
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json={"chat_id": chat_id, "text": reply}
            )
            
    return {"status": "ok"}
