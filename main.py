from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

app = FastAPI()

# --- КОНФИГУРАЦИЯ TELEGRAM ТОКЕНОВ ДЛЯ УВЕДОМЛЕНИЙ ---
TELEGRAM_TOKEN = "8768948746:AAEB_DfIbDwmO2uHhFb4XKLQKAlARgO5WIw"  # Замени на настоящий токен твоего бота
TELEGRAM_API_URL = f"https://api.telegram.org/bot{8768948746:AAEB_DfIbDwmO2uHhFb4XKLQKAlARgO5WIw}/sendMessage"

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

# --- ЭНДПОИНТ ДЛЯ ЧАТА С ИИ ---
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
        # ИСПОЛЬЗУЕМ АСИНХРОННЫЙ КЛИЕНТ HTTPX
        async with httpx.AsyncClient() as client:
            response = await client.post(
                B_AI_URL, 
                json=payload, 
                headers=headers,
                timeout=30.0 # Увеличили таймаут для ожидания ответа ИИ
            )
            response.raise_for_status()
            data = response.json()
        
        ai_text = data['choices'][0]['message']['content']
        
        # Дополнительная чистка текста от нежелательных символов
        ai_text = ai_text.replace('*', '').replace('_', '')
        
        return {"reply": ai_text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ФУНКЦИЯ ОТПРАВКИ УВЕДОМЛЕНИЙ В ТЕЛЕГРАМ ---
async def send_telegram_notification(chat_id: str, text: str):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(TELEGRAM_API_URL, json=payload, timeout=10.0)
            response.raise_for_status()
    except Exception as e:
        print(f"Ошибка отправки уведомления в Telegram: {e}")


# --- ЭНДПОИНТ ДЛЯ ВЕБХУКА ОТ BITRIX24 ---
@app.post("/api/bitrix-webhook")
async def bitrix_webhook(request: Request):
    # 1. Получаем данные от Битрикс24 (Битрикс отправляет данные как form-data)
    data = await request.form()
    bitrix_lead_id = data.get("lead_id")
    new_bitrix_status = data.get("status") # Например, 'UC_7Y3'
    
    # Получаем chat_id пользователя и название вакансии (передаются из Битрикса или запрашиваются из твоей БД)
    user_chat_id = data.get("user_chat_id")
    job_title = data.get("job_title") or "вакансию"
    
    # 2. Переводим статус Битрикса в понятный статус твоего приложения
    status_map = {
        'NEW': 'pending',
        'UC_7Y3': 'interview', # ID стадии в Битриксе -> твой статус во Flutter
        'LOSE': 'rejected'
    }
    
    status_labels_ru = {
        'pending': 'На рассмотрении',
        'interview': 'Приглашение на интервью',
        'rejected': 'Отказ'
    }
    
    app_status = status_map.get(new_bitrix_status, 'pending')
    status_label = status_labels_ru.get(app_status, 'На рассмотрении')
    
    # 3. Обновляем статус в базе данных приложения
    # TODO: Здесь должен быть твой код для обновления записи в БД
    # Пример SQL: UPDATE applied_jobs SET status = app_status WHERE bitrix_id = bitrix_lead_id
    
    # 4. Отправка мгновенного уведомления пользователю в Telegram
    if user_chat_id:
        message_text = f"🎓 Статус вашего отклика на вакансию *{job_title}* изменился!\nТекущий статус: *{status_label}*."
        await send_telegram_notification(user_chat_id, message_text)
    
    return {"status": "ok"}

# Запуск локально: uvicorn main:app --reload
