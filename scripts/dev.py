"""Cross-platform local launcher. Ctrl+C stops the owned frontend/backend processes."""
import os
import shutil
import signal
import subprocess
import sys
import time

from shared.config import ROOT


def stop(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
    else:
        os.killpg(process.pid, signal.SIGTERM)


def main():
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise SystemExit("Install Node.js 22 or newer first.")
    flags = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    processes = []
    try:
        processes.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=ROOT, **flags))
        processes.append(subprocess.Popen([npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"], cwd=ROOT / "frontend", **flags))
        print("\nCloudFlow: http://localhost:5173\nAPI docs: http://localhost:8000/docs\nPress Ctrl+C to stop.\n", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in reversed(processes):
            stop(process)


if __name__ == "__main__":
    main()
