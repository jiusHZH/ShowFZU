from __future__ import annotations

import json
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = ROOT / "frontend"
BACKEND_ROOT = ROOT / "backend"
RUNTIME_DIR = BACKEND_ROOT / "tmp-runtime"
FRONTEND_LOG = RUNTIME_DIR / "frontend-dev.log"
BACKEND_LOG = RUNTIME_DIR / "backend-dev.log"

FRONTEND_URL = "http://127.0.0.1:5173/"
BACKEND_HEALTH_URL = "http://127.0.0.1:8000/api/health"

DETACHED_FLAGS = 0
for name in ("DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP", "CREATE_BREAKAWAY_FROM_JOB"):
    DETACHED_FLAGS |= int(getattr(subprocess, name, 0))


def is_up(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def tail_lines(path: Path, limit: int = 20) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]


def launch_frontend() -> int:
    npm_cmd = shutil.which("npm.cmd") or r"D:\Nodejs\npm.cmd"
    if not Path(npm_cmd).exists():
        raise RuntimeError(f"npm.cmd not found: {npm_cmd}")

    with FRONTEND_LOG.open("ab") as handle:
        process = subprocess.Popen(
            [
                "cmd.exe",
                "/c",
                f"\"{npm_cmd}\" run dev -- --host 127.0.0.1 --port 5173",
            ],
            cwd=FRONTEND_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.STDOUT,
            creationflags=DETACHED_FLAGS,
            close_fds=True,
        )
    return process.pid


def launch_backend() -> int:
    python_path = BACKEND_ROOT / ".venv" / "Scripts" / "python.exe"
    if not python_path.exists():
        raise RuntimeError(f"Backend virtualenv python not found: {python_path}")

    with BACKEND_LOG.open("ab") as handle:
        process = subprocess.Popen(
            [str(python_path), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=BACKEND_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.STDOUT,
            creationflags=DETACHED_FLAGS,
            close_fds=True,
        )
    return process.pid


def main() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    frontend_before = is_up(FRONTEND_URL)
    backend_before = is_up(BACKEND_HEALTH_URL)

    frontend_pid: int | None = None
    backend_pid: int | None = None

    if not frontend_before:
        frontend_pid = launch_frontend()
    if not backend_before:
        backend_pid = launch_backend()

    frontend_after = False
    backend_after = False
    for _ in range(20):
        frontend_after = is_up(FRONTEND_URL)
        backend_after = is_up(BACKEND_HEALTH_URL)
        if frontend_after and backend_after:
            break
        time.sleep(1)

    result = {
        "frontend_before": frontend_before,
        "backend_before": backend_before,
        "frontend_pid": frontend_pid,
        "backend_pid": backend_pid,
        "frontend_after": frontend_after,
        "backend_after": backend_after,
    }

    if not frontend_after:
        result["frontend_log_tail"] = tail_lines(FRONTEND_LOG)
    if not backend_after:
        result["backend_log_tail"] = tail_lines(BACKEND_LOG)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
