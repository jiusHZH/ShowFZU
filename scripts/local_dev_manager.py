from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = ROOT / "frontend"
BACKEND_ROOT = ROOT / "backend"
RUNTIME_DIR = BACKEND_ROOT / "tmp-runtime"
FRONTEND_LOG = RUNTIME_DIR / "frontend-dev.log"
BACKEND_LOG = RUNTIME_DIR / "backend-dev.log"
MANAGER_LOG = RUNTIME_DIR / "manager.log"
PID_FILE = RUNTIME_DIR / "local-dev-manager.pid"


def log(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with MANAGER_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def main() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    npm_cmd = shutil.which("npm.cmd") or r"D:\Nodejs\npm.cmd"
    python_path = BACKEND_ROOT / ".venv" / "Scripts" / "python.exe"

    if not Path(npm_cmd).exists():
        raise RuntimeError(f"npm.cmd not found: {npm_cmd}")
    if not python_path.exists():
        raise RuntimeError(f"Backend python not found: {python_path}")

    frontend_handle = FRONTEND_LOG.open("ab")
    backend_handle = BACKEND_LOG.open("ab")

    frontend = subprocess.Popen(
        ["cmd.exe", "/c", f"call {npm_cmd} run dev -- --host 127.0.0.1 --port 5173"],
        cwd=FRONTEND_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=frontend_handle,
        stderr=subprocess.STDOUT,
    )
    log(f"Frontend started with pid={frontend.pid}")

    backend = subprocess.Popen(
        [str(python_path), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=BACKEND_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=backend_handle,
        stderr=subprocess.STDOUT,
    )
    log(f"Backend started with pid={backend.pid}")

    try:
        while True:
            frontend_code = frontend.poll()
            backend_code = backend.poll()
            if frontend_code is not None:
                log(f"Frontend exited with code={frontend_code}")
                break
            if backend_code is not None:
                log(f"Backend exited with code={backend_code}")
                break
            time.sleep(2)
    finally:
        frontend_handle.close()
        backend_handle.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - local runtime helper
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        log(f"Manager crashed: {exc!r}")
        raise
