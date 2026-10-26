import logging

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from orchestrator.graph import build_graph
from shared.contracts import PipelineState, utcnow
from shared.files import artifact_inventory, safe_run_dir
from shared.repository import ConflictError, RunRepository

logger = logging.getLogger(__name__)


def execute_run(settings, run_id, owner):
    repository = RunRepository(settings.workspace)
    record = repository.get(run_id)
    run_dir = safe_run_dir(settings.workspace, run_id)
    try:
        with SqliteSaver.from_conn_string(str(settings.workspace / "checkpoints.sqlite")) as checkpointer:
            graph = build_graph(settings, repository, run_dir, owner, checkpointer)
            config = {"configurable": {"thread_id": run_id}, "recursion_limit": 30}
            incoming = (Command(resume=record.approval.model_dump()) if record.approval is not None else
                        PipelineState(run_id=run_id, objective=record.objective, options=record.options).model_dump())
            result = graph.invoke(incoming, config=config)
            interrupted = bool(result.get("__interrupt__"))
            state = PipelineState.model_validate({key: value for key, value in result.items() if key != "__interrupt__"})
            def finish(run):
                run.state = state
                run.approval = None
                run.artifacts = artifact_inventory(run_dir)
                if interrupted:
                    run.status = "awaiting_approval"
                    run.stage = "human_review"
                    run.agents["human_review"].status = "waiting"
                    run.agents["human_review"].summary = "Review the target, features, preprocessing and models before training."
                else:
                    run.status = "completed"
                    run.stage = "completed"
                    run.completed_at = utcnow()
            repository.update(run_id, finish, owner=owner)
            repository.event(run_id, "human_review" if interrupted else "reporting", "Waiting for your review." if interrupted else "Pipeline completed.")
    except ConflictError:
        logger.info("Execution stopped because ownership changed or cancellation was requested: %s", run_id)
    except Exception as exc:
        logger.exception("Pipeline failed: %s", run_id)
        def fail(run):
            run.status = "failed"
            run.error = f"{type(exc).__name__}: {str(exc)[:1500]}"
            run.completed_at = utcnow()
            if run.stage in run.agents:
                run.agents[run.stage].status = "failed"
                run.agents[run.stage].summary = run.error
            run.artifacts = artifact_inventory(run_dir)
        try:
            repository.update(run_id, fail, owner=owner)
            repository.event(run_id, "error", f"{type(exc).__name__}: {str(exc)[:1000]}", "error")
        except ConflictError:
            pass
    finally:
        repository.release(run_id, owner)
