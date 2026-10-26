"""REST boundary for the persisted CloudFlow workflow."""
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import uuid
import zipfile
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path

import joblib
import pandas as pd
from fastapi import APIRouter, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from shared.config import ROOT, Settings
from shared.contracts import (AnalysisPlan, PredictionRequest, ReviewDecision, RunOptions, RunRecord, TERMINAL, utcnow)
from shared.data import infer_target, infer_task, profile_frame, read_upload, validate_plan_columns, prepare_data
from shared.files import json_safe, safe_run_dir
from shared.repository import ConflictError, RunRepository


def create_app(settings: Settings | None = None):
    settings = settings or Settings()
    settings.initialize()
    repository = RunRepository(settings.workspace)

    @asynccontextmanager
    async def lifespan(application):
        worker = None
        worker_log = None
        if settings.auto_worker:
            worker_log = (settings.workspace / "worker-service.log").open("a", encoding="utf-8")
            worker = subprocess.Popen([sys.executable, "-m", "orchestrator.worker"], cwd=ROOT,
                env={**os.environ, "CLOUDFLOW_WORKSPACE": str(settings.workspace)},
                stdout=worker_log, stderr=worker_log, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        application.state.worker = worker
        try:
            yield
        finally:
            if worker and worker.poll() is None:
                worker.terminate()
                try:
                    worker.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    worker.kill()
            if worker_log:
                worker_log.close()

    application = FastAPI(title="CloudFlow API", version="1.0.0", lifespan=lifespan,
        description="Five-agent data science workflow with durable human review, experiments, reports and inference.")
    application.state.repository = repository
    application.state.settings = settings
    application.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins,
        allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @application.exception_handler(ConflictError)
    async def conflict_handler(request, exception):
        return JSONResponse(status_code=409, content={"detail": str(exception)})

    router = APIRouter()

    def get_run(run_id):
        try:
            safe_run_dir(settings.workspace, run_id)
            return repository.get(run_id)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(404, "Pipeline run not found.") from exc

    async def upload(file):
        try:
            filename = Path((file.filename or "").replace("\\", "/")).name
            if not filename.lower().endswith(".csv"):
                raise HTTPException(400, "Only CSV files are supported.")
            contents = await file.read(settings.max_upload_bytes + 1)
            if len(contents) > settings.max_upload_bytes:
                raise HTTPException(413, "The maximum upload size is 10 MB.")
            try:
                frame = await run_in_threadpool(read_upload, contents, settings)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            return filename, contents, frame
        finally:
            await file.close()

    @router.get("/health")
    def health():
        worker = getattr(application.state, "worker", None)
        return {"status": "ok", "version": "1.0.0", "storage": "sqlite",
                "worker_mode": "automatic" if settings.auto_worker else "external",
                "worker_running": worker.poll() is None if worker else None}

    @router.get("/config")
    def configuration():
        packages = ["langgraph", "mlflow", "scikit-learn", "xgboost", "shap", "pandas", "numpy", "matplotlib", "plotly", "fastapi"]
        versions = {}
        for package in packages:
            try:
                versions[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                versions[package] = None
        return {"max_file_size_mb": 10, "max_rows": settings.max_rows, "max_columns": settings.max_columns,
            "llm": {"provider": settings.llm_provider, "configured": settings.llm_ready,
                    "model": settings.llm_model if settings.llm_ready else None},
            "defaults": RunOptions().model_dump(), "models": ["linear", "random_forest", "svm", "gradient_boosting", "xgboost"],
            "versions": versions, "worker_mode": "automatic" if settings.auto_worker else "external",
            "scope": "Local, single-user application. Add authentication before exposing it to a network."}

    @router.post("/datasets/preview")
    async def preview(file: UploadFile = File(...), objective: str = Form("")):
        filename, contents, frame = await upload(file)
        suggested = infer_target(list(frame.columns), objective)
        return {"filename": filename, "sha256": hashlib.sha256(contents).hexdigest(),
            "profile": profile_frame(frame), "columns": list(frame.columns),
            "rows": json_safe(frame.head(8).to_dict(orient="records")),
            "suggested_target": suggested, "suggested_task": infer_task(frame[suggested]) if suggested else None}

    @router.post("/runs", status_code=202)
    async def create_run(file: UploadFile = File(...), objective: str = Form(...), options: str = Form("{}")):
        objective = objective.strip()
        if not 10 <= len(objective) <= 2000:
            await file.close()
            raise HTTPException(422, "Describe the objective in 10-2,000 characters.")
        try:
            parsed_options = RunOptions.model_validate_json(options)
        except ValidationError as exc:
            await file.close()
            raise HTTPException(422, "Invalid run options: " + str(exc)[:800]) from exc
        if parsed_options.use_llm and not settings.llm_ready:
            await file.close()
            raise HTTPException(422, "AI reasoning is not configured. Configure a Gemini/Groq key and model, or use local planning.")
        filename, contents, frame = await upload(file)
        if parsed_options.target_column and parsed_options.target_column not in frame:
            raise HTTPException(422, "The selected target column does not exist.")
        run_id = uuid.uuid4().hex
        run_dir = safe_run_dir(settings.workspace, run_id)
        run_dir.mkdir()
        try:
            (run_dir / "input.csv").write_bytes(contents)
            record = RunRecord(run_id=run_id, filename=filename, objective=objective,
                options=parsed_options, dataset_sha256=hashlib.sha256(contents).hexdigest())
            repository.create(record)
            repository.event(run_id, "queued", "Dataset accepted. Waiting for the worker.")
        except OSError as exc:
            raise HTTPException(500, "The dataset could not be saved.") from exc
        return {"run_id": run_id, "status": "queued", "url": f"/api/runs/{run_id}"}

    @router.get("/runs")
    def list_runs(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
        runs, total = repository.list(limit, offset)
        return {"runs": [{"run_id": r.run_id, "filename": r.filename, "objective": r.objective,
            "status": r.status, "stage": r.stage, "created_at": r.created_at, "completed_at": r.completed_at,
            "error": r.error, "task_type": r.state.plan.task_type if r.state and r.state.plan else r.options.task_type,
            "target_column": r.state.plan.target_column if r.state and r.state.plan else r.options.target_column,
            "evaluation": r.state.evaluation if r.state else None} for r in runs], "total": total, "limit": limit, "offset": offset}

    @router.get("/runs/{run_id}", response_model=RunRecord)
    def retrieve(run_id: str):
        return get_run(run_id)

    @router.get("/runs/{run_id}/events")
    def events(run_id: str, after: int = Query(0, ge=0)):
        get_run(run_id)
        return {"events": repository.events(run_id, after)}

    @router.post("/runs/{run_id}/approval", status_code=202)
    def approve(run_id: str, decision: ReviewDecision):
        current = get_run(run_id)
        if current.status != "awaiting_approval":
            raise HTTPException(409, "This run is not waiting for approval.")
        if decision.approved:
            plan = decision.plan or current.state.plan
            frame = pd.read_csv(safe_run_dir(settings.workspace, run_id) / "input.csv")
            try:
                validate_plan_columns(plan, frame)
                # Validate edited target/task before consuming the durable checkpoint.
                prepare_data(frame, plan.target_column, plan.task_type, current.state.options)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
        def mutate(run):
            if run.status != "awaiting_approval":
                raise ConflictError("The review was already submitted.")
            run.approval = decision
            run.status = "queued" if decision.approved else "cancelled"
            if not decision.approved:
                run.completed_at = utcnow()
                run.agents["human_review"].status = "cancelled"
                run.agents["human_review"].summary = "The user declined the training plan."
        result = repository.update(run_id, mutate)
        repository.event(run_id, "human_review", "Review submitted." if decision.approved else "Training plan declined.")
        return {"run_id": run_id, "status": result.status}

    @router.post("/runs/{run_id}/cancel")
    def cancel(run_id: str):
        get_run(run_id)
        def mutate(run):
            if run.status in TERMINAL:
                raise ConflictError("This run has already finished.")
            run.status = "cancelled"
            run.completed_at = utcnow()
            if run.stage in run.agents:
                run.agents[run.stage].status = "cancelled"
        result = repository.update(run_id, mutate)
        repository.event(run_id, "cancelled", "Cancellation requested by the user.")
        return {"run_id": run_id, "status": result.status}

    @router.get("/runs/{run_id}/artifacts")
    def artifacts(run_id: str):
        return {"artifacts": get_run(run_id).artifacts}

    @router.get("/runs/{run_id}/artifacts/{artifact_path:path}")
    def artifact(run_id: str, artifact_path: str):
        record = get_run(run_id)
        entry = next((a for a in record.artifacts if a["path"] == artifact_path), None)
        if entry is None:
            raise HTTPException(404, "Artifact not found.")
        directory = safe_run_dir(settings.workspace, run_id)
        path = (directory / artifact_path).resolve()
        if not path.is_relative_to(directory) or not path.is_file():
            raise HTTPException(404, "Artifact not found.")
        return FileResponse(path, filename=path.name, media_type=entry["media_type"],
            content_disposition_type="inline" if path.suffix.lower() in {".png", ".json"} else "attachment",
            headers={"X-Content-Type-Options": "nosniff"})

    @router.get("/runs/{run_id}/download")
    def download(run_id: str):
        record = get_run(run_id)
        if record.status not in TERMINAL:
            raise HTTPException(409, "Wait for the run to finish before downloading the bundle.")
        directory = safe_run_dir(settings.workspace, run_id)
        stream = BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for entry in record.artifacts:
                path = (directory / entry["path"]).resolve()
                if path.is_relative_to(directory) and path.is_file():
                    archive.write(path, entry["path"])
        stream.seek(0)
        return StreamingResponse(stream, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="cloudflow-{run_id[:8]}.zip"'})

    @router.get("/experiments")
    def experiments(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
        runs, total = repository.list(limit, offset)
        rows = []
        for run in runs:
            if run.state:
                for candidate in run.state.candidates:
                    rows.append({**candidate.model_dump(), "run_id": run.run_id, "filename": run.filename,
                        "target_column": run.state.plan.target_column, "task_type": run.state.plan.task_type,
                        "primary_metric": run.state.plan.primary_metric,
                        "selected": candidate.candidate_id == run.state.selected_candidate_id})
        return {"experiments": rows, "total_runs": total, "limit": limit, "offset": offset}

    @router.post("/runs/{run_id}/predict")
    def predict(run_id: str, request: PredictionRequest):
        run = get_run(run_id)
        if run.status != "completed":
            raise HTTPException(409, "Predictions require a completed run.")
        plan = run.state.plan
        if any(set(plan.feature_columns) - set(row) for row in request.rows):
            raise HTTPException(422, "Every row must provide all approved feature columns; use null for missing values.")
        try:
            bundle = joblib.load(safe_run_dir(settings.workspace, run_id) / "model.joblib")
            frame = pd.DataFrame(request.rows)[plan.feature_columns]
            predictions = bundle["pipeline"].predict(frame)
            output = {"predictions": json_safe(predictions), "target_column": plan.target_column}
            if hasattr(bundle["pipeline"], "predict_proba"):
                output["probabilities"] = json_safe(bundle["pipeline"].predict_proba(frame))
                output["classes"] = json_safe(bundle["pipeline"].classes_)
            return output
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, f"Invalid prediction rows: {str(exc)[:400]}") from exc

    application.include_router(router, prefix="/api")
    # Existing clients remain compatible; all new frontend calls use /api.
    application.include_router(router, include_in_schema=False)
    return application


app = create_app()
