import os
import re
from ai_client import client, GROQ_MODELS

BOTS_DIR = "/home/runner/workspace/generated_bots"

CODE_GEN_PROMPT = """Ты — эксперт по разработке Telegram-ботов на Python с использованием aiogram 3.x.
Тебе дают резюме требований к боту — ты должен написать ПОЛНЫЙ, РАБОЧИЙ Python-код бота.

Правила написания кода:
1. Используй ТОЛЬКО aiogram 3.x (import from aiogram)
2. Используй MemoryStorage для FSM если нужны состояния
3. Читай токен из переменной окружения BOT_TOKEN
4. Читай дополнительные ключи из переменных окружения (PAYMENT_TOKEN, SHEETS_KEY и т.д.)
5. Все тексты на русском языке
6. Обязательно обработай /start команду
7. Добавь обработку ошибок
8. В конце файла: if __name__ == "__main__": asyncio.run(main())
9. Выводи ТОЛЬКО код без пояснений и markdown-блоков
10. Если нужна БД — используй sqlite3 (встроенный модуль)
11. Добавь requirements в виде комментария в начале: # REQUIREMENTS: aiogram==3.13.0 aiosqlite ...

Пиши чистый, читаемый код с комментариями на русском."""


async def generate_bot_code(summary: str, bot_name: str, extra_context: str = "") -> str:
    messages = [
        {
            "role": "user",
            "content": f"Создай полный код Telegram-бота по этому резюме:\n\n{summary}\n\nНазвание бота: {bot_name}\n{extra_context}\n\nВыводи только Python-код, без markdown."
        }
    ]

    for i, model in enumerate(GROQ_MODELS):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": CODE_GEN_PROMPT}] + messages,
                max_tokens=4096,
                temperature=0.3,
            )
            code = response.choices[0].message.content
            code = clean_code(code)
            return code
        except Exception as e:
            if i == len(GROQ_MODELS) - 1:
                raise e
            continue


async def fix_bot_code(code: str, error_log: str, attempt: int = 1) -> str:
    messages = [
        {
            "role": "user",
            "content": f"Исправь ошибки в коде Telegram-бота.\n\nОШИБКА:\n{error_log}\n\nКОД:\n{code}\n\nВыводи только исправленный Python-код."
        }
    ]

    for i, model in enumerate(GROQ_MODELS):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": CODE_GEN_PROMPT}] + messages,
                max_tokens=4096,
                temperature=0.2,
            )
            code = response.choices[0].message.content
            return clean_code(code)
        except Exception as e:
            if i == len(GROQ_MODELS) - 1:
                raise e
            continue


def clean_code(code: str) -> str:
    code = re.sub(r"```python\s*", "", code)
    code = re.sub(r"```\s*", "", code)
    code = code.strip()
    return code


def check_syntax(code: str) -> tuple[bool, str]:
    import py_compile, tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        py_compile.compile(tmp_path, doraise=True)
        return True, ""
    except py_compile.PyCompileError as e:
        return False, str(e)
    finally:
        os.unlink(tmp_path)


def save_bot_code(bot_id: int, code: str, bot_name: str) -> str:
    os.makedirs(BOTS_DIR, exist_ok=True)
    bot_dir = os.path.join(BOTS_DIR, f"bot_{bot_id}")
    os.makedirs(bot_dir, exist_ok=True)

    code_path = os.path.join(bot_dir, "bot.py")
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)

    reqs = extract_requirements(code)
    req_path = os.path.join(bot_dir, "requirements.txt")
    with open(req_path, "w") as f:
        f.write("\n".join(reqs))

    dockerfile = f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .
CMD ["python", "bot.py"]
"""
    with open(os.path.join(bot_dir, "Dockerfile"), "w") as f:
        f.write(dockerfile)

    return code_path


def extract_requirements(code: str) -> list:
    default = ["aiogram==3.13.0", "aiosqlite", "aiohttp"]
    match = re.search(r"# REQUIREMENTS:\s*(.+)", code)
    if match:
        extras = match.group(1).strip().split()
        all_reqs = list(set(default + extras))
        return all_reqs
    return default


def get_bot_code_path(bot_id: int) -> str | None:
    path = os.path.join(BOTS_DIR, f"bot_{bot_id}", "bot.py")
    return path if os.path.exists(path) else None
