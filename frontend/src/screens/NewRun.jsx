import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Check,
  FileSpreadsheet,
  LoaderCircle,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";
import { request } from "../lib/api";
import { useResource } from "../lib/useResource";
import { ErrorMessage, PageHeader } from "../ui/Common";
import Workflow from "../ui/Workflow";

export default function NewRun() {
  const navigate = useNavigate();
  const input = useRef(null);
  const sequence = useRef(0);
  const { data: config } = useResource("/config");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [objective, setObjective] = useState("");
  const [target, setTarget] = useState("");
  const [task, setTask] = useState("auto");
  const [useLlm, setUseLlm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [testSize, setTestSize] = useState(0.2);
  const [retries, setRetries] = useState(1);

  async function choose(selected) {
    const version = ++sequence.current;
    setError("");
    setFile(null);
    setPreview(null);
    setTarget("");
    if (!selected) {
      setUploading(false);
      return;
    }
    if (!selected.name.toLowerCase().endsWith(".csv")) {
      setError("Choose a CSV file.");
      return;
    }
    if (selected.size > 10 * 1024 * 1024) {
      setError("The maximum file size is 10 MB.");
      return;
    }
    const form = new FormData();
    form.append("file", selected);
    form.append("objective", objective);
    setUploading(true);
    try {
      const result = await request("/datasets/preview", {
        method: "POST",
        body: form,
      });
      if (version !== sequence.current) return;
      setFile(selected);
      setPreview(result);
      setTarget(result.suggested_target || "");
    } catch (err) {
      if (version === sequence.current) setError(err.message);
    } finally {
      if (version === sequence.current) setUploading(false);
    }
  }

  async function launch(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("objective", objective.trim());
      form.append(
        "options",
        JSON.stringify({
          target_column: target,
          task_type: task,
          test_size: testSize,
          max_retries: retries,
          use_llm: useLlm,
        }),
      );
      const result = await request("/runs", { method: "POST", body: form });
      navigate(`/pipeline/${result.run_id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <section>
      <PageHeader
        eyebrow="MISSION CONTROL / NEW RUN"
        title="What will you discover?"
        description="Connect a dataset. Define the objective. Put your agent team in motion."
      >
        <span className="subtle-badge">
          <Sparkles size={14} /> Your research, accelerated
        </span>
      </PageHeader>
      <div className="intro-strip">
        <div className="intro-symbol">
          <Sparkles size={20} />
        </div>
        <p>
          <strong>Meet your data science team.</strong> From the first
          inspection to the final explanation, every decision stays visible.
        </p>
        <span>5 AGENTS + YOU</span>
      </div>
      <Workflow compact />
      <form onSubmit={launch}>
        <div className="new-run-grid">
          <section className="panel upload-panel">
            <div className="panel-heading">
              <div>
                <span className="step-label">01 / YOUR DATA</span>
                <h2>Start with a dataset</h2>
              </div>
              <FileSpreadsheet size={20} />
            </div>
            <input
              ref={input}
              type="file"
              accept=".csv,text/csv"
              className="visually-hidden"
              id="dataset-file"
              aria-label="Upload CSV dataset"
              disabled={busy || uploading}
              onChange={(e) => choose(e.target.files?.[0])}
            />
            {!file ? (
              <button
                type="button"
                className={`dropzone ${dragging ? "dragging" : ""}`}
                disabled={busy || uploading}
                onClick={() => input.current.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragging(false);
                  if (!busy && !uploading) choose(e.dataTransfer.files[0]);
                }}
              >
                <div className="upload-icon">
                  {uploading ? (
                    <LoaderCircle size={29} className="spin" />
                  ) : (
                    <UploadCloud size={29} strokeWidth={1.5} />
                  )}
                </div>
                <strong>
                  {uploading
                    ? "Inspecting your dataset…"
                    : "Drop your dataset here"}
                </strong>
                <span>
                  or <b>browse files</b> to get started
                </span>
                <small>CSV format · Up to 10 MB</small>
              </button>
            ) : (
              <div className="selected-file">
                <span className="file-icon">
                  <FileSpreadsheet size={25} />
                </span>
                <div>
                  <strong>{file.name}</strong>
                  <small>
                    {preview.profile.rows.toLocaleString()} rows ·{" "}
                    {preview.columns.length} columns ·{" "}
                    {(file.size / 1024).toFixed(1)} KB
                  </small>
                </div>
                <Check className="success-color" size={18} />
                <button
                  className="icon-button"
                  type="button"
                  aria-label="Remove dataset"
                  disabled={busy}
                  onClick={() => {
                    choose(null);
                    input.current.value = "";
                  }}
                >
                  <X size={16} />
                </button>
              </div>
            )}
            {preview ? (
              <div className="preview-section">
                <div className="section-label">
                  <strong>Dataset preview</strong>
                  <span>FIRST {preview.rows.length} ROWS</span>
                </div>
                <div className="table-scroll preview-table">
                  <table>
                    <thead>
                      <tr>
                        {preview.columns.map((c) => (
                          <th key={c}>{c}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.rows.map((row, i) => (
                        <tr key={i}>
                          {preview.columns.map((c) => (
                            <td key={c}>
                              {row[c] === null ? (
                                <span className="muted">null</span>
                              ) : (
                                String(row[c])
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="help-text">
                  {preview.profile.missing_cells} missing cells ·{" "}
                  {preview.profile.duplicate_rows} duplicate rows detected
                </p>
              </div>
            ) : (
              <div className="upload-hint">
                <span className="mini-grid">▦</span>
                <div>
                  <strong>A clear view of your data</strong>
                  <p>
                    Preview columns and quality checks as soon as you upload.
                  </p>
                </div>
              </div>
            )}
            <p className="data-note">
              <span className="tiny-dot" />
              Your dataset stays in this workspace. AI reasoning, when enabled,
              receives the objective and summaries.
            </p>
          </section>
          <section className="panel objective-panel">
            <div className="panel-heading">
              <div>
                <span className="step-label">02 / YOUR QUESTION</span>
                <h2>Give your agents a direction</h2>
              </div>
              <Sparkles size={20} />
            </div>
            <label htmlFor="objective">What would you like to predict?</label>
            <textarea
              id="objective"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              maxLength={2000}
              minLength={10}
              required
              disabled={busy}
              placeholder="For example, predict which customers are likely to churn and understand the factors behind it."
              rows={4}
            />
            <div className="input-meta">
              <span>Be specific about the outcome you care about.</span>
              <span>{objective.length}/2000</span>
            </div>
            <div className="example-row">
              <span>TRY A QUESTION</span>
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  setObjective(
                    "Predict customer churn and identify the most influential features.",
                  )
                }
              >
                Customer churn <ArrowRight size={12} />
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  setObjective(
                    "Predict house prices from the available property characteristics.",
                  )
                }
              >
                House prices <ArrowRight size={12} />
              </button>
            </div>
            <div className="two-fields">
              <div>
                <label htmlFor="target">Target column</label>
                <select
                  id="target"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  required
                  disabled={!preview || busy}
                >
                  <option value="">
                    {preview ? "Select an outcome" : "Upload a dataset first"}
                  </option>
                  {preview?.columns.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="task">Problem type</label>
                <select
                  id="task"
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                  disabled={busy}
                >
                  <option value="auto">Detect automatically</option>
                  <option value="classification">Classification</option>
                  <option value="regression">Regression</option>
                </select>
              </div>
            </div>
            <details className="advanced">
              <summary>Run preferences</summary>
              <div className="two-fields">
                <div>
                  <label htmlFor="holdout">Holdout set</label>
                  <select
                    id="holdout"
                    value={testSize}
                    onChange={(e) => setTestSize(Number(e.target.value))}
                    disabled={busy}
                  >
                    <option value={0.2}>20% of rows</option>
                    <option value={0.3}>30% of rows</option>
                    <option value={0.4}>40% of rows</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="retries">Improvement rounds</label>
                  <select
                    id="retries"
                    value={retries}
                    onChange={(e) => setRetries(Number(e.target.value))}
                    disabled={busy}
                  >
                    {[0, 1, 2].map((v) => (
                      <option key={v} value={v}>
                        {v} additional {v === 1 ? "round" : "rounds"}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </details>
            <label className="checkbox-line ai-toggle">
              <input
                type="checkbox"
                checked={useLlm}
                disabled={!config?.llm.configured || busy}
                onChange={(e) => setUseLlm(e.target.checked)}
              />
              <span>
                <strong>Use AI reasoning</strong>
                <small>
                  {config?.llm.configured
                    ? `${config.llm.provider} · ${config.llm.model}`
                    : "Local planning active. Add a Gemini or Groq key to enable AI reasoning."}
                </small>
              </span>
            </label>
          </section>
        </div>
        <ErrorMessage>{error}</ErrorMessage>
        <div className="launch-bar">
          <div className="checkpoint-note">
            <span className="checkpoint-icon">
              <Check size={16} />
            </span>
            <div>
              <strong>You stay in the loop.</strong>
              <p>Review the plan before any model starts training.</p>
            </div>
          </div>
          <button
            className="primary-button launch-button"
            type="submit"
            disabled={
              !file ||
              !target ||
              objective.trim().length < 10 ||
              uploading ||
              busy
            }
          >
            {busy ? (
              <LoaderCircle size={17} className="spin" />
            ) : (
              <Sparkles size={17} />
            )}
            {busy ? "Creating analysis…" : "Launch analysis"}
            <ArrowRight size={17} />
          </button>
        </div>
      </form>
    </section>
  );
}
