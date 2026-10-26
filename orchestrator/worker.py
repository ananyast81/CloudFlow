"""One persistent queue consumer, with a killable child process per execution segment."""
import argparse
import os
import subprocess
import sys
import time
import uuid

from shared.config import ROOT, Settings
from shared.contracts import utcnow
from shared.files import safe_run_dir
from shared.repository import ConflictError, RunRepository


def work(settings, once=False):
    settings.initialize()
    repository = RunRepository(settings.workspace)
    owner = uuid.uuid4().hex
    while True:
        run = repository.claim(owner, settings.lease_seconds)
        if run is None:
            if once:
                return
            time.sleep(1)
            continue
        start = time.monotonic()
        run_dir = safe_run_dir(settings.workspace, run.run_id)
        environment = {**os.environ, "CLOUDFLOW_WORKSPACE": str(settings.workspace), "PYTHONUNBUFFERED": "1",
                       "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MPLBACKEND": "Agg"}
        with (run_dir / "worker.log").open("a", encoding="utf-8") as log:
            child = subprocess.Popen([sys.executable, "-m", "orchestrator.worker", "--execute", run.run_id, "--owner", owner],
                cwd=ROOT, env=environment, stdout=log, stderr=log,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                while child.poll() is None:
                    current = repository.get(run.run_id)
                    if current.status == "cancelled":
                        child.terminate()
                        child.wait(timeout=10)
                        break
                    if time.monotonic() - start > settings.max_run_seconds:
                        child.kill()
                        child.wait()
                        raise TimeoutError("Execution exceeded the 30-minute segment limit.")
                    if current.status == "running":
                        repository.heartbeat(run.run_id, owner, settings.lease_seconds)
                    time.sleep(0.5)
                if repository.get(run.run_id).status == "running":
                    raise RuntimeError("The execution process exited before saving its final state. Inspect the local worker log.")
            except Exception as exc:
                if child.poll() is None:
                    child.kill()
                    child.wait()
                def fail(record):
                    record.status = "failed"
                    record.error = str(exc)
                    record.completed_at = utcnow()
                    if record.stage in record.agents:
                        record.agents[record.stage].status = "failed"
                try:
                    repository.update(run.run_id, fail, owner=owner)
                except ConflictError:
                    pass
            finally:
                repository.release(run.run_id, owner)
        if once:
            return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute")
    parser.add_argument("--owner")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    if args.execute:
        from orchestrator.execution import execute_run
        execute_run(settings, args.execute, args.owner)
    else:
        work(settings, args.once)
