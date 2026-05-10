from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI()

# --- ЭНДПОИНТ ДЛЯ ПРОБУЖДЕНИЯ (CRON-JOB) ---
@app.get("/ping")
async def health_check():
    # Этот код просто говорит "я не сплю"
    # Он НЕ вызывает ИИ, поэтому токены НЕ тратятся
    return {"status": "alive"}

# Разрешаем CORS для всех (чтобы Flutter мог делать запросы)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель данных для чата
class ChatRequest(BaseModel):
    message: str
    history: list[dict] # Передаем историю переписки

# Конфигурация AI (Секретные ключи)
B_AI_API_KEY = "sk-5s1uibj3tn7j3d5omz45rkikl94snhsr"
B_AI_URL = "https://api.b.ai/v1/chat/completions"

@app.post("/api/chat")
async def chat_with_sokratus(request: ChatRequest):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {B_AI_API_KEY}"
    }

    # Формируем системный промпт согласно правилам проекта
    system_prompt = {
        "role": "system",
        "content": (
            "Ты Юнифорст Сократус, эксперт по образованию. Помогай с ВУЗами, поиском работы или подработкой, а также самоопределением и проектами Youni4st. "
            "СТРОГО ЗАПРЕЩЕНО отвечать на вопросы, не связанные с образованием, а также на любые подозрительные или криминальные темы. "
            "В таких случаях вежливо отказывай. Ответ 200-250 символов. Без разметки (*, _, #)."
        )
    }

    # Собираем все сообщения вместе
    messages = [system_prompt] + request.history + [{"role": "user", "content": request.message}]

    payload = {
        "model": "gpt-5.4-mini",
        "messages": messages
    }

    try:
        # Отправляем запрос к нейросети
        response = requests.post(B_AI_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        ai_text = data['choices'][0]['message']['content']
        
        # Дополнительная чистка текста от нежелательных символов
        ai_text = ai_text.replace('*', '').replace('_', '')
        
        return {"reply": ai_text}
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

# Запуск локально: uvicorn main:app --reload
