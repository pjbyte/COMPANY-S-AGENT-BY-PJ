"""PolicyPilot desktop launcher.

Double-clicking this file (or the PolicyPilot desktop shortcut) starts the
API server inside this process and opens the app in a native window - no
browser, no visible URL, no console.

Closing the window shuts the whole application down: the server runs as a
background thread of this process, so nothing keeps running afterwards.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / "backend" / ".venv" / "Scripts" / "pythonw.exe"

# pythonw.exe has no console: sys.stdout/stderr are None, which crashes any
# library that prints (tqdm progress bars, uvicorn logs). Route them to the
# null device before importing anything heavy.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")


def _ensure_venv() -> None:
    """Re-launch with the project's own Python so all dependencies resolve,
    no matter which Python double-clicked this file."""
    venv_scripts = VENV_PY.resolve().parent
    if VENV_PY.exists() and Path(sys.executable).resolve().parent != venv_scripts:
        subprocess.Popen(
            [str(VENV_PY), str(Path(__file__).resolve())],
            cwd=str(ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        sys.exit(0)


_ensure_venv()
sys.path.insert(0, str(ROOT / "backend"))

HOST, PORT = "127.0.0.1", 8000
URL = f"http://{HOST}:{PORT}"


def server_responsive(timeout: float = 1.0) -> bool:
    try:
        urllib.request.urlopen(f"{URL}/api/health", timeout=timeout)
        return True
    except Exception:
        return False


def alert(message: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, "PolicyPilot", 0x10)
    except Exception:
        print(message)


def run_server() -> None:
    try:
        import uvicorn

        from app.main import app

        uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
    except Exception:
        log = ROOT / "backend" / "storage" / "launcher_error.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(traceback.format_exc(), encoding="utf-8")
        alert("PolicyPilot failed to start. Details were saved to:\n" + str(log))


def wait_until_ready(seconds: float = 120.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if server_responsive():
            return True
        time.sleep(0.5)
    return False


def main() -> None:
    if not server_responsive():
        threading.Thread(target=run_server, daemon=True).start()
        if not wait_until_ready():
            alert(
                "PolicyPilot failed to start.\n\n"
                "Check that no other program is using port 8000, then try again."
            )
            return

    try:
        import webview

        webview.create_window("PolicyPilot", URL, width=1360, height=860, min_size=(980, 620))
        webview.start()  # blocks until the user closes the window
    except Exception:
        # WebView2 unavailable: fall back to the default browser.
        import webbrowser

        webbrowser.open(URL)
        threading.Event().wait()  # keep the server alive; stop via stop.bat


if __name__ == "__main__":
    main()
