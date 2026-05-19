from groq import AsyncGroq
from config import GROK_API_KEY, GROQ_MODELS
import asyncio

client = AsyncGroq(api_key=GROK_API_KEY)

SYSTEM_PROMPT_BOT = """Ты — помощник по созданию Telegram-ботов на платформе Botify.
Твоя задача — собрать всю необходимую информацию для генерации кода бота.

Правила:
• Задавай строго ОДИН вопрос за раз
• Вопросы должны быть конкретными и понятными
• Адаптируй вопросы под тип бота (магазин, запись, игра, и т.д.)
• Когда информации достаточно (обычно 4-7 вопросов) — выведи резюме в формате:

📋 РЕЗЮМЕ:
Название: [название бота]
Тип: [простой/средний/сложный]
Функции: [список функций]
Интеграции: [если есть]
Сложность: [простой/средний/сложный]

СТОИМОСТЬ: [150/300/600] кредитов

Готов генерировать? ✅

• Диалог истории хранится полностью — помни контекст
• Отвечай на русском языке
• Будь дружелюбным и профессиональным"""

SYSTEM_PROMPT_MINIAPP = """Ты — помощник по созданию Telegram Mini Apps на платформе Botify.
Твоя задача — собрать всю необходимую информацию для создания веб-приложения внутри Telegram.

Правила:
• Задавай строго ОДИН вопрос за раз
• Уточни: тип (магазин, сервис, игра, каталог), дизайн, функционал
• Когда информации достаточно — выведи резюме:

📋 РЕЗЮМЕ Mini App:
Название: [название]
Тип: [простой/сложный]
Функции: [список]
Дизайн: [описание]

СТОИМОСТЬ: [400/800] кредитов

Готов генерировать? ✅

• Отвечай на русском языке"""


async def ask_ai(messages: list, system: str = SYSTEM_PROMPT_BOT, model_idx: int = 0) -> str:
    model = GROQ_MODELS[model_idx % len(GROQ_MODELS)]
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}] + messages,
            max_tokens=1024,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        if model_idx < len(GROQ_MODELS) - 1:
            return await ask_ai(messages, system, model_idx + 1)
        raise e


def detect_summary(text: str) -> bool:
    return "РЕЗЮМЕ" in text and "СТОИМОСТЬ" in text


def extract_cost(text: str) -> int:
    import re
    match = re.search(r"СТОИМОСТЬ:\s*(\d+)", text)
    if match:
        return int(match.group(1))
    if "150" in text:
        return 150
    if "300" in text:
        return 300
    if "600" in text:
        return 600
    if "400" in text:
        return 400
    if "800" in text:
        return 800
    return 300


def extract_bot_type(cost: int) -> str:
    mapping = {150: "simple", 300: "medium", 600: "complex", 400: "miniapp_simple", 800: "miniapp_complex"}
    return mapping.get(cost, "medium")
