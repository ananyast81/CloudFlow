"""Five agents, durable human review and bounded CV feedback in LangGraph."""
from functools import partial
from pathlib import Path

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agents.data_prep_agent.main import run as understand
from agents.eda_agent.main import run as analyze
from agents.evaluation_agent.main import run as evaluate
from agents.eval_report_agent.main import run as report
from agents.feature_ml_agent.main import run as model
from shared.contracts import PipelineState, ReviewDecision, utcnow
from shared.data import load_prepared, validate_plan_columns
from shared.files import artifact_inventory, write_json
from shared.features import describe_strategy

SUMMARIES = {
    "data_understanding": "Profiled and cleaned the dataset; reserved the holdout.",
    "analysis_features": "Generated training-only EDA and proposed features.",
    "modeling": "Compared approved candidates with cross-validation.",
    "evaluation": "Evaluated diagnostics and the retry decision.",
    "reporting": "Generated the final report, explanations and reproducibility artifacts.",
}


def build_graph(settings, repository, run_dir: Path, owner, checkpointer):
    def agent_node(state: PipelineState, stage, function):
        def starting(record):
            record.stage = stage
            record.agents[stage].status = "running"
            record.agents[stage].started_at = utcnow()
            record.agents[stage].summary = f"Executing {stage.replace('_', ' ')}."
        repository.update(state.run_id, starting, owner=owner)
        repository.event(state.run_id, stage, f"Started {stage.replace('_', ' ')} (round {state.attempt}).")
        patch = function(state, run_dir, settings)
        updated = PipelineState.model_validate({**state.model_dump(), **patch})
        def finished(record):
            record.state = updated
            record.agents[stage].status = "completed"
            record.agents[stage].completed_at = utcnow()
            record.agents[stage].summary = SUMMARIES[stage]
            decisions = []
            if updated.plan:
                decisions = [f"Target: {updated.plan.target_column} ({updated.plan.task_type})."]
            if stage == "modeling":
                decisions += [f"Selected {updated.selected_candidate_id} by training CV."]
            if stage == "evaluation":
                decisions += updated.evaluation.get("retry_reasons", [])
                if updated.retry:
                    decisions += [f"Retrying with a different bounded parameter grid, round {updated.attempt}."]
            record.agents[stage].decisions = decisions
            record.artifacts = artifact_inventory(run_dir)
        repository.update(state.run_id, finished, owner=owner)
        repository.event(state.run_id, stage, SUMMARIES[stage])
        return patch

    def review(state: PipelineState):
        # No side effects before interrupt: this node is replayed on resume.
        decision = ReviewDecision.model_validate(interrupt({"plan": state.plan.model_dump(), "preparation": state.preparation, "warnings": state.warnings}))
        if not decision.approved:
            return {"approved": False}
        plan = decision.plan or state.plan
        validate_plan_columns(plan, load_prepared(run_dir, state.plan))
        if plan.target_column != state.plan.target_column or plan.task_type != state.plan.task_type:
            # A changed target/task invalidates EDA and the split. Rebuild and ask again.
            options = state.options.model_copy(update={"target_column": plan.target_column, "task_type": plan.task_type})
            repository.event(state.run_id, "human_review", "Target or task changed. Rebuilding preparation and EDA for a second review.")
            return {"options": options.model_dump(), "plan": plan.model_dump(), "approved": False, "eda": {}, "warnings": [], "candidates": []}
        write_json(run_dir / "approved-plan.json", plan.model_dump())
        write_json(run_dir / "plan.json", plan.model_dump())
        write_json(run_dir / "review.json", decision.model_dump())
        eda = {**state.eda, "feature_strategy": describe_strategy(plan),
               "excluded_features": {column: reason for column, reason in state.eda.get("excluded_features", {}).items()
                                     if column not in plan.feature_columns}}
        write_json(run_dir / "eda/summary.json", eda)
        def approved(record):
            record.agents["human_review"].status = "completed"
            record.agents["human_review"].summary = "The user approved the training plan."
            record.agents["human_review"].completed_at = utcnow()
        repository.update(state.run_id, approved, owner=owner)
        repository.event(state.run_id, "human_review", "Training plan approved.")
        return {"plan": plan.model_dump(), "eda": eda, "approved": True}

    graph = StateGraph(PipelineState)
    for stage, function in [("data_understanding", understand), ("analysis_features", analyze), ("modeling", model), ("evaluation", evaluate), ("reporting", report)]:
        graph.add_node(stage, partial(agent_node, stage=stage, function=function))
    graph.add_node("human_review", review)
    graph.add_edge(START, "data_understanding")
    graph.add_edge("data_understanding", "analysis_features")
    graph.add_edge("analysis_features", "human_review")
    graph.add_conditional_edges("human_review", lambda state: "modeling" if state.approved else "data_understanding")
    graph.add_edge("modeling", "evaluation")
    graph.add_conditional_edges("evaluation", lambda state: "modeling" if state.retry else "reporting")
    graph.add_edge("reporting", END)
    return graph.compile(checkpointer=checkpointer)
