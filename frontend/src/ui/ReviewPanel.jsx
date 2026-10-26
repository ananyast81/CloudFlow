import { useState } from "react";
import { ArrowRight, Check, LoaderCircle, ShieldCheck } from "lucide-react";
import { post } from "../lib/api";
import { ErrorMessage } from "./Common";

const modelLabels = {
  linear: "Logistic regression / Ridge",
  random_forest: "Random forest",
  svm: "Support vector machine",
  gradient_boosting: "Gradient boosting",
  xgboost: "XGBoost",
};

export default function ReviewPanel({ run, onDone }) {
  const [plan, setPlan] = useState(run.state.plan);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [comment, setComment] = useState("");
  const columns = run.state.profile.column_names;
  const changedTarget =
    plan.target_column !== run.state.plan.target_column ||
    plan.task_type !== run.state.plan.task_type;
  const set = (key, value) =>
    setPlan((previous) => ({ ...previous, [key]: value }));
  const toggle = (key, value) =>
    set(
      key,
      plan[key].includes(value)
        ? plan[key].filter((v) => v !== value)
        : [...plan[key], value],
    );

  async function submit(approved) {
    setBusy(true);
    setError("");
    try {
      await post(`/runs/${run.run_id}/approval`, { approved, plan, comment });
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="review-panel" aria-label="Review training plan">
      <div className="review-title">
        <span>
          <ShieldCheck size={23} />
        </span>
        <div>
          <p className="eyebrow">AWAITING HUMAN APPROVAL</p>
          <h2>A moment for your review</h2>
          <p>
            Your agents have prepared a plan. Check the decisions below before
            training begins.
          </p>
        </div>
      </div>
      <div className="two-fields">
        <div>
          <label htmlFor="review-target">Target column</label>
          <select
            id="review-target"
            value={plan.target_column}
            disabled={busy}
            onChange={(e) =>
              setPlan((previous) => ({
                ...previous,
                target_column: e.target.value,
                feature_columns: [
                  ...new Set([
                    ...previous.feature_columns,
                    previous.target_column,
                  ]),
                ].filter((c) => c !== e.target.value),
              }))
            }
          >
            {columns.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="review-task">Problem type</label>
          <select
            id="review-task"
            value={plan.task_type}
            disabled={busy}
            onChange={(e) =>
              setPlan((previous) => ({
                ...previous,
                task_type: e.target.value,
                primary_metric:
                  e.target.value === "classification" ? "f1_weighted" : "rmse",
              }))
            }
          >
            <option value="classification">Classification</option>
            <option value="regression">Regression</option>
          </select>
        </div>
      </div>
      <div className="review-grid">
        <div>
          <h3>
            Selected features <span>{plan.feature_columns.length}</span>
          </h3>
          <div className="feature-options">
            {columns
              .filter((c) => c !== plan.target_column)
              .map((c) => (
                <label key={c} className="checkbox-line">
                  <input
                    type="checkbox"
                    checked={plan.feature_columns.includes(c)}
                    disabled={busy}
                    onChange={() => toggle("feature_columns", c)}
                  />
                  <span>{c}</span>
                </label>
              ))}
          </div>
        </div>
        <div>
          <h3>Candidate models</h3>
          {Object.entries(modelLabels).map(([key, label]) => (
            <label key={key} className="checkbox-line">
              <input
                type="checkbox"
                checked={plan.models.includes(key)}
                disabled={busy}
                onChange={() => toggle("models", key)}
              />
              <span>{label}</span>
            </label>
          ))}
          <p className="help-text">A dummy baseline is always included.</p>
        </div>
      </div>
      <details className="review-details">
        <summary>Preprocessing, scoring and cleaning decisions</summary>
        <div className="two-fields">
          <div>
            <label htmlFor="imputation">Numeric imputation</label>
            <select
              id="imputation"
              value={plan.numeric_imputation}
              disabled={busy}
              onChange={(e) => set("numeric_imputation", e.target.value)}
            >
              <option value="median">Median</option>
              <option value="mean">Mean</option>
            </select>
          </div>
          <div>
            <label htmlFor="metric">Primary metric</label>
            <select
              id="metric"
              value={plan.primary_metric}
              disabled={busy}
              onChange={(e) => set("primary_metric", e.target.value)}
            >
              {(plan.task_type === "classification"
                ? ["f1_weighted", "accuracy"]
                : ["rmse", "mae", "r2"]
              ).map((m) => (
                <option key={m}>{m}</option>
              ))}
            </select>
          </div>
        </div>
        {[
          ["scale_numeric", "Scale numeric features"],
          ["derive_dates", "Derive year, month and weekday from dates"],
          [
            "select_features",
            "Select the top 75% of encoded features within each fold",
          ],
          ...(plan.task_type === "classification"
            ? [
                [
                  "balance_classes",
                  "Balance class weights for supported models",
                ],
              ]
            : []),
        ].map(([key, text]) => (
          <label key={key} className="checkbox-line">
            <input
              type="checkbox"
              checked={plan[key]}
              disabled={busy}
              onChange={(e) => set(key, e.target.checked)}
            />
            <span>{text}</span>
          </label>
        ))}
        <ul className="decision-list">
          {run.state.preparation.steps.map((s) => (
            <li key={s}>
              <Check size={14} />
              {s}
            </li>
          ))}
        </ul>
        <p className="help-text">{plan.reasoning}</p>
      </details>
      <label htmlFor="review-comment">
        Review note <span className="muted">(optional)</span>
      </label>
      <input
        id="review-comment"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        maxLength={1000}
        disabled={busy}
        placeholder="Record context for this experiment…"
      />
      {changedTarget && (
        <p className="info-message">
          Changing the target or problem type rebuilds the analysis. You will
          review the updated plan again before training.
        </p>
      )}
      <ErrorMessage>{error}</ErrorMessage>
      <div className="review-actions">
        <button
          type="button"
          className="secondary-button"
          disabled={busy}
          onClick={() => submit(false)}
        >
          Decline & stop
        </button>
        <button
          type="button"
          className="primary-button"
          disabled={busy || !plan.feature_columns.length || !plan.models.length}
          onClick={() => submit(true)}
        >
          {busy ? (
            <LoaderCircle size={16} className="spin" />
          ) : (
            <Check size={16} />
          )}
          {changedTarget ? "Update analysis & review again" : "Approve & train"}
          <ArrowRight size={16} />
        </button>
      </div>
    </section>
  );
}
