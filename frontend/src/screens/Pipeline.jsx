import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Check,
  Download,
  FileDown,
  LoaderCircle,
  Plus,
  Square,
  Terminal,
  TriangleAlert,
} from "lucide-react";
import { apiUrl, artifactUrl, post } from "../lib/api";
import { useResource } from "../lib/useResource";
import {
  ErrorMessage,
  Loading,
  Metric,
  PageHeader,
  Status,
} from "../ui/Common";
import Workflow from "../ui/Workflow";
import ReviewPanel from "../ui/ReviewPanel";
import Chart from "../ui/Chart";
import ModelTable from "../ui/ModelTable";
import PredictionPanel from "../ui/PredictionPanel";

const done = new Set(["completed", "failed", "cancelled"]);

export default function Pipeline() {
  const { runId } = useParams();
  const [terminal, setTerminal] = useState(false);
  const {
    data: run,
    error,
    refresh,
  } = useResource(`/runs/${runId}`, terminal ? 0 : 1800);
  const [selected, setSelected] = useState("data_understanding");
  const [tab, setTab] = useState("overview");
  const [actionError, setActionError] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const { data: logData } = useResource(
    `/runs/${runId}/events`,
    terminal ? 0 : 2000,
  );
  // Stop polling after the final response; run IDs are keyed in the router.
  if (run && done.has(run.status) && !terminal) setTerminal(true);

  if (!run)
    return (
      <>
        <ErrorMessage retry={refresh}>{error}</ErrorMessage>
        {!error && <Loading text="Opening your analysis…" />}
      </>
    );
  const state = run.state;
  const evaluation = state?.evaluation?.metrics ? state.evaluation : null;
  const activeAgent = run.agents[selected];
  const completedStages = Object.values(run.agents).filter(
    (a) => a.status === "completed",
  ).length;
  async function cancel() {
    setCancelling(true);
    setActionError("");
    try {
      await post(`/runs/${runId}/cancel`, {});
      refresh();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setCancelling(false);
    }
  }

  return (
    <section>
      <Link to="/history" className="back-link">
        <ArrowLeft size={14} /> All analyses
      </Link>
      <PageHeader
        eyebrow={`ANALYSIS / ${runId.slice(0, 8).toUpperCase()}`}
        title={run.filename}
        description={run.objective}
      >
        <div className="header-actions">
          <Status value={run.status} />
          {!done.has(run.status) ? (
            <button
              className="secondary-button small"
              onClick={cancel}
              disabled={cancelling}
            >
              <Square size={12} />
              {cancelling ? "Stopping…" : "Stop run"}
            </button>
          ) : (
            <Link className="secondary-button small" to="/new-run">
              <Plus size={15} />
              New analysis
            </Link>
          )}
        </div>
      </PageHeader>
      <ErrorMessage retry={refresh}>{error || actionError}</ErrorMessage>
      <div className="metrics-row">
        <Metric
          label="DATASET"
          value={state?.profile?.rows?.toLocaleString() ?? "Inspecting…"}
          note="original rows"
        />
        <Metric
          label="TARGET"
          value={
            state?.plan?.target_column ||
            run.options.target_column ||
            "Detecting…"
          }
          note={state?.plan?.task_type || "Awaiting analysis"}
        />
        <Metric
          label="PROGRESS"
          value={`${completedStages} / 6`}
          note="workflow stages"
        />
        <Metric
          label={
            evaluation
              ? evaluation.primary_metric.toUpperCase().replaceAll("_", " ")
              : "PLANNING MODE"
          }
          value={
            evaluation
              ? evaluation.primary_score.toFixed(4)
              : run.options.use_llm
                ? "AI assisted"
                : "Local"
          }
          note={
            evaluation ? "untouched holdout" : "Human review before training"
          }
        />
      </div>
      <div className="panel workflow-panel">
        <div className="orbit-workspace">
          <div className="orbit-canvas">
            <div className="section-label">
              <strong>Orchestrator Orbit</strong>
              <span>
                {run.status === "running" && (
                  <LoaderCircle size={13} className="spin" />
                )}
                {run.stage.replaceAll("_", " ")}
              </span>
            </div>
            <Workflow
              agents={run.agents}
              selected={selected}
              onSelect={setSelected}
            />
          </div>
          <aside className="agent-inspector">
            <span className="step-label">
              {selected === "human_review"
                ? "HUMAN CHECKPOINT"
                : "AGENT DOSSIER"}
            </span>
            <h2>
              {selected === "human_review"
                ? "Review inspector"
                : "Stage inspector"}
            </h2>
            <div>
              <span className={`inspector-dot dot-${activeAgent.status}`} />
              <strong>{selected.replaceAll("_", " ")}</strong>
              <Status value={activeAgent.status} />
            </div>
            <code className="stage-identifier">{selected}</code>
            <p>
              {activeAgent.summary ||
                "No summary has been reported for this stage yet."}
            </p>
            {activeAgent.decisions.length > 0 && (
              <ul>
                {activeAgent.decisions.map((text, i) => (
                  <li key={i}>{text}</li>
                ))}
              </ul>
            )}
          </aside>
        </div>
      </div>
      <section className="panel event-panel">
        <div className="panel-heading">
          <h2>Live execution logs</h2>
          <Terminal size={17} />
        </div>
        {!logData?.events?.length && (
          <p className="help-text">
            Waiting for execution events from the backend.
          </p>
        )}
        <ol className="event-list">
          {(logData?.events || []).map((event) => (
            <li key={event.id}>
              <i className={event.level === "error" ? "event-error" : ""} />
              <div>
                <time>
                  {new Date(event.time).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </time>
                <p>{event.message}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
      {run.status === "awaiting_approval" && (
        <ReviewPanel
          key={JSON.stringify(state.plan)}
          run={run}
          onDone={refresh}
        />
      )}
      {run.error && (
        <div className="failed-panel">
          <TriangleAlert size={23} />
          <div>
            <h3>This analysis needs attention</h3>
            <p>{run.error}</p>
            <Link to="/new-run">
              Adjust the dataset or configuration and start a new analysis{" "}
              <ArrowLeft className="rotate" size={13} />
            </Link>
          </div>
        </div>
      )}
      {run.status === "cancelled" && (
        <p className="info-message">
          This run was stopped. Any completed artifacts are still available
          below.
        </p>
      )}
      <div className="tabs" role="tablist" aria-label="Analysis details">
        {[
          ["overview", "Overview"],
          ["results", "Results & diagnostics"],
          ["artifacts", `Artifacts (${run.artifacts.length})`],
          ["predict", "Predict"],
        ].map(([key, label]) => (
          <button
            role="tab"
            aria-selected={tab === key}
            key={key}
            disabled={key === "predict" && run.status !== "completed"}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "overview" && (
        <div className="overview-grid">
          <div>
            {state?.report?.answer && (
              <section className="answer-card">
                <div className="section-label">
                  <span className="step-label">YOUR QUESTION, ANSWERED</span>
                  <Check size={20} />
                </div>
                <h2>{state.report.answer}</h2>
                <a
                  className="text-link"
                  href={artifactUrl(runId, "report.html")}
                >
                  Download the full report <FileDown size={15} />
                </a>
              </section>
            )}
            {state?.preparation && (
              <section className="panel">
                <div className="panel-heading">
                  <h2>Preparation notes</h2>
                  <span className="subtle-badge">
                    {state.preparation.rows_after} cleaned rows
                  </span>
                </div>
                <ul className="decision-list">
                  {state.preparation.steps?.map((step) => (
                    <li key={step}>
                      <Check size={15} />
                      {step}
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {state?.eda?.plots?.length > 0 && (
              <section className="panel">
                <div className="panel-heading">
                  <h2>A closer look at your data</h2>
                  <span className="subtle-badge">Training rows only</span>
                </div>
                <div className="eda-grid">
                  {state.eda.plots.map((plot) => (
                    <figure key={plot.path}>
                      <a
                        href={artifactUrl(runId, plot.path)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <img
                          src={artifactUrl(runId, plot.path)}
                          alt={plot.title}
                          loading="lazy"
                        />
                      </a>
                      <figcaption>
                        <strong>{plot.title}</strong>
                        <p>{plot.description}</p>
                      </figcaption>
                    </figure>
                  ))}
                </div>
              </section>
            )}
            {!state && (
              <div className="panel">
                <Loading text="Your dataset is queued. Agent decisions will appear here." />
              </div>
            )}
          </div>
          <aside>
            {state?.warnings?.length > 0 && (
              <section className="panel warnings-panel">
                <h3>Keep in mind</h3>
                <ul>
                  {state.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              </section>
            )}
          </aside>
        </div>
      )}
      {tab === "results" && (
        <div className="results-stack">
          {state?.candidates?.length ? (
            <>
              <section className="panel">
                <div className="panel-heading">
                  <h2>The experiment leaderboard</h2>
                  <span className="subtle-badge">
                    {state.plan.primary_metric} · training CV
                  </span>
                </div>
                <ModelTable
                  rows={state.candidates}
                  metric={state.plan.primary_metric}
                  selected={state.selected_candidate_id}
                />
              </section>
              {run.artifacts.some(
                (a) => a.path === "comparison-chart.json",
              ) && <Chart runId={runId} path="comparison-chart.json" />}
            </>
          ) : (
            <div className="panel">
              <p className="help-text">
                Results will appear after you approve the plan and training
                finishes.
              </p>
            </div>
          )}
          {evaluation && (
            <>
              <div className="metrics-row">
                {Object.entries(evaluation.metrics).map(([key, value]) => (
                  <Metric
                    key={key}
                    label={key.toUpperCase().replaceAll("_", " ")}
                    value={value?.toFixed(4) ?? "Unavailable"}
                    note="holdout metric"
                  />
                ))}
              </div>
              <div className="two-chart-grid">
                <Chart runId={runId} path="evaluation-chart.json" />
                {run.artifacts.some(
                  (a) => a.path === "importance-chart.json",
                ) && <Chart runId={runId} path="importance-chart.json" />}
              </div>
              <section className="panel">
                <h2>What the errors tell us</h2>
                <p className="help-text">
                  Same-holdout baseline: {evaluation.baseline_score.toFixed(4)}{" "}
                  ·{" "}
                  {evaluation.beats_baseline
                    ? "The selected model improves on the baseline."
                    : "The selected model does not improve on the baseline."}
                </p>
                {evaluation.retry_reasons?.map((reason) => (
                  <p className="info-message" key={reason}>
                    {reason}
                  </p>
                ))}
                {evaluation.error_examples.length > 0 ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Source row</th>
                          <th>Actual</th>
                          <th>Prediction</th>
                          {state.plan.task_type === "regression" && (
                            <th>Absolute error</th>
                          )}
                        </tr>
                      </thead>
                      <tbody>
                        {evaluation.error_examples.map((row) => (
                          <tr key={row.row_index}>
                            <td>{row.row_index}</td>
                            <td>{String(row.actual)}</td>
                            <td>{String(row.prediction)}</td>
                            {state.plan.task_type === "regression" && (
                              <td>{row.absolute_error.toFixed(4)}</td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p>No prediction errors were found on this holdout.</p>
                )}
                <ul className="plain-list">
                  {evaluation.limitations.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
            </>
          )}
          {state?.report?.recommendations && (
            <section className="panel">
              <h2>Where to go next</h2>
              <ul className="decision-list">
                {state.report.recommendations.map((text) => (
                  <li key={text}>
                    <ArrowLeft className="rotate" size={14} />
                    {text}
                  </li>
                ))}
              </ul>
              {state.report.ai_narrative && (
                <div className="ai-narrative">
                  <h3>AI interpretation</h3>
                  <p>{state.report.ai_narrative.interpretation}</p>
                </div>
              )}
            </section>
          )}
        </div>
      )}
      {tab === "artifacts" && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Everything behind the result</h2>
              <p className="help-text">
                Datasets, models, reports, charts and reproducibility records.
              </p>
            </div>
            {done.has(run.status) && (
              <a
                className="primary-button"
                href={apiUrl(`/runs/${runId}/download`)}
              >
                <Download size={16} />
                Download all
              </a>
            )}
          </div>
          <div className="artifact-grid">
            {run.artifacts.map((artifact) => (
              <a
                className="artifact-card"
                key={artifact.path}
                href={artifactUrl(runId, artifact.path)}
              >
                <span>
                  <FileDown size={22} />
                </span>
                <div>
                  <strong>{artifact.name}</strong>
                  <small>
                    {artifact.path} · {(artifact.size_bytes / 1024).toFixed(1)}{" "}
                    KB
                  </small>
                </div>
                <Download size={15} />
              </a>
            ))}
          </div>
          {!run.artifacts.length && (
            <p className="help-text">
              Artifacts appear as each stage completes.
            </p>
          )}
        </section>
      )}
      {tab === "predict" && run.status === "completed" && (
        <PredictionPanel run={run} />
      )}
    </section>
  );
}
