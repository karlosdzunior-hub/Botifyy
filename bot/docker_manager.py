import os
import subprocess
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BOTS_DIR = os.getenv("BOTS_DIR", "/app/generated_bots")
HOST_BOTS_DIR = os.getenv("HOST_BOTS_DIR", BOTS_DIR)
CONTAINER_PREFIX = "botify_user_bot_"


def is_docker_available() -> bool:
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


async def build_and_run_bot(bot_id: int, bot_token: str, extra_env: dict = None) -> tuple[bool, str]:
    bot_dir = os.path.join(BOTS_DIR, f"bot_{bot_id}")
    if not os.path.exists(bot_dir):
        return False, "Директория бота не найдена"

    host_bot_dir = os.path.join(HOST_BOTS_DIR, f"bot_{bot_id}")
    container_name = f"{CONTAINER_PREFIX}{bot_id}"

    await stop_bot_container(bot_id)

    image_name = f"botify_bot_{bot_id}:latest"
    build_cmd = ["docker", "build", "-t", image_name, host_bot_dir]
    build_env = {**os.environ, "DOCKER_BUILDKIT": "0"}
    try:
        proc = await asyncio.create_subprocess_exec(
            *build_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=build_env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            error = stderr.decode()
            logger.error(f"Docker build failed for bot {bot_id}: {error}")
            return False, f"Ошибка сборки: {error[:500]}"
    except asyncio.TimeoutError:
        return False, "Тайм-аут сборки Docker-образа"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"

    env_args = ["-e", f"BOT_TOKEN={bot_token}"]
    if extra_env:
        for k, v in extra_env.items():
            env_args.extend(["-e", f"{k}={v}"])

    run_cmd = [
        "docker", "run", "-d",
        "--name", container_name,
        "--restart", "unless-stopped",
        *env_args,
        image_name
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *run_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            error = stderr.decode()
            return False, f"Ошибка запуска: {error[:500]}"
        container_id = stdout.decode().strip()[:12]
        return True, container_id
    except Exception as e:
        return False, str(e)


async def stop_bot_container(bot_id: int) -> bool:
    container_name = f"{CONTAINER_PREFIX}{bot_id}"
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return True
    except Exception:
        return False


async def start_bot_container(bot_id: int) -> bool:
    container_name = f"{CONTAINER_PREFIX}{bot_id}"
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "start", container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        return proc.returncode == 0
    except Exception:
        return False


async def restart_bot_container(bot_id: int) -> bool:
    container_name = f"{CONTAINER_PREFIX}{bot_id}"
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "restart", container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0
    except Exception:
        return False


async def get_container_status(bot_id: int) -> str:
    container_name = f"{CONTAINER_PREFIX}{bot_id}"
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "inspect", "--format={{.State.Status}}", container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return "not_found"
        return stdout.decode().strip()
    except Exception:
        return "error"


async def get_container_logs(bot_id: int, lines: int = 50) -> str:
    container_name = f"{CONTAINER_PREFIX}{bot_id}"
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "logs", "--tail", str(lines), container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode()
    except Exception as e:
        return f"Ошибка получения логов: {e}"


async def get_all_running_bots() -> list[int]:
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "ps", "--filter", f"name={CONTAINER_PREFIX}", "--format={{.Names}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        names = stdout.decode().strip().split("\n")
        bot_ids = []
        for name in names:
            if name.startswith(CONTAINER_PREFIX):
                try:
                    bot_ids.append(int(name[len(CONTAINER_PREFIX):]))
                except ValueError:
                    pass
        return bot_ids
    except Exception:
        return []
