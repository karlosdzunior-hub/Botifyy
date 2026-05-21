import os
import sys
import asyncio
import logging

logger = logging.getLogger(__name__)

BOTS_DIR = os.getenv("BOTS_DIR", "/app/generated_bots")

_running_processes: dict[int, asyncio.subprocess.Process] = {}


async def install_requirements(bot_id: int) -> tuple[bool, str]:
    bot_dir = os.path.join(BOTS_DIR, f"bot_{bot_id}")
    req_file = os.path.join(bot_dir, "requirements.txt")
    if not os.path.exists(req_file):
        return True, ""
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", "-r", req_file, "-q",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            return False, stderr.decode()[:300]
        return True, ""
    except asyncio.TimeoutError:
        return False, "Тайм-аут установки зависимостей"
    except Exception as e:
        return False, str(e)


async def start_bot_process(bot_id: int, bot_token: str, extra_env: dict = None) -> tuple[bool, str]:
    bot_dir = os.path.join(BOTS_DIR, f"bot_{bot_id}")
    bot_file = os.path.join(bot_dir, "bot.py")

    if not os.path.exists(bot_file):
        return False, "Файл бота не найден"

    await stop_bot_process(bot_id)

    ok, err = await install_requirements(bot_id)
    if not ok:
        return False, f"Ошибка зависимостей: {err}"

    env = os.environ.copy()
    env["BOT_TOKEN"] = bot_token
    if extra_env:
        env.update(extra_env)

    log_file = os.path.join(bot_dir, "bot.log")
    try:
        with open(log_file, "w") as log:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, bot_file,
                stdout=log,
                stderr=log,
                cwd=bot_dir,
                env=env,
            )
        _running_processes[bot_id] = proc
        logger.info(f"Bot {bot_id} запущен как subprocess PID={proc.pid}")
        return True, str(proc.pid)
    except Exception as e:
        return False, str(e)


async def stop_bot_process(bot_id: int) -> bool:
    proc = _running_processes.get(bot_id)
    if proc is None:
        return True
    try:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        del _running_processes[bot_id]
        logger.info(f"Bot {bot_id} subprocess остановлен")
        return True
    except Exception as e:
        logger.error(f"Ошибка остановки bot {bot_id}: {e}")
        return False


def get_process_status(bot_id: int) -> str:
    proc = _running_processes.get(bot_id)
    if proc is None:
        return "stopped"
    if proc.returncode is None:
        return "running"
    return "exited"


def get_process_logs(bot_id: int, lines: int = 30) -> str:
    bot_dir = os.path.join(BOTS_DIR, f"bot_{bot_id}")
    log_file = os.path.join(bot_dir, "bot.log")
    if not os.path.exists(log_file):
        return "Логи отсутствуют"
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
        return "".join(all_lines[-lines:]) or "Логи пустые"
    except Exception as e:
        return f"Ошибка чтения логов: {e}"


def get_all_running_bots() -> list[int]:
    return [bot_id for bot_id, proc in _running_processes.items() if proc.returncode is None]
