import { useState } from "react";
import { ArrowRight, LoaderCircle, WandSparkles } from "lucide-react";
import { post } from "../lib/api";
import { ErrorMessage } from "./Common";

export default function PredictionPanel({ run }) {
  const [values, setValues] = useState({});
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const features = run.state.plan.feature_columns;
  async function predict(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const row = Object.fromEntries(
        features.map((key) => [key, values[key]?.trim() || null]),
      );
      setResult(await post(`/runs/${run.run_id}/predict`, { rows: [row] }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <span className="step-label">TRY THE FITTED MODEL</span>
          <h2>Make a prediction</h2>
        </div>
        <WandSparkles size={21} />
      </div>
      <p className="help-text">
        Use the original feature values. The saved pipeline applies the same
        transformations used in training. Blank fields use fitted imputation.
      </p>
      <form onSubmit={predict}>
        <div className="prediction-fields">
          {features.map((feature) => (
            <div key={feature}>
              <label htmlFor={`predict-${feature}`}>{feature}</label>
              <input
                id={`predict-${feature}`}
                value={values[feature] || ""}
                disabled={busy}
                onChange={(e) =>
                  setValues((previous) => ({
                    ...previous,
                    [feature]: e.target.value,
                  }))
                }
                placeholder="Enter a value"
              />
            </div>
          ))}
        </div>
        <button className="primary-button" disabled={busy}>
          {busy ? (
            <LoaderCircle size={16} className="spin" />
          ) : (
            <ArrowRight size={16} />
          )}
          Predict {run.state.plan.target_column}
        </button>
      </form>
      <ErrorMessage>{error}</ErrorMessage>
      {result && (
        <div className="prediction-result" role="status">
          <span>Predicted {result.target_column}</span>
          <strong>{String(result.predictions[0])}</strong>
          {result.probabilities && (
            <div className="probabilities">
              {result.classes.map((label, i) => (
                <span key={String(label)}>
                  {String(label)}:{" "}
                  {(result.probabilities[0][i] * 100).toFixed(1)}%
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
