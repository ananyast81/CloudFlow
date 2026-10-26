import {
  Check,
  Code2,
  ExternalLink,
  Server,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { apiUrl } from "../lib/api";
import { useResource } from "../lib/useResource";
import { ErrorMessage, Loading, PageHeader } from "../ui/Common";

export default function Settings() {
  const { data, error, refresh } = useResource("/config");
  return (
    <section>
      <PageHeader
        eyebrow="KNOW YOUR ENVIRONMENT"
        title="Built to be reproducible."
        description="The services, tools and limits behind your workspace."
      />
      <ErrorMessage retry={refresh}>{error}</ErrorMessage>
      {!data ? (
        !error && <Loading />
      ) : (
        <>
          <div className="settings-grid">
            <section className="panel">
              <div className="panel-heading">
                <h2>Reasoning provider</h2>
                <Sparkles size={20} />
              </div>
              <span className="subtle-badge">
                {data.llm.configured
                  ? `${data.llm.provider} configured`
                  : "Local planning"}
              </span>
              <p>
                {data.llm.configured
                  ? `Available model: ${data.llm.model}. Enable AI reasoning for each new run.`
                  : "All numerical analysis works without a provider. To add AI reasoning, configure the backend environment and restart it."}
              </p>
              <pre className="config-snippet">
                LLM_PROVIDER=groq or gemini{"\n"}LLM_API_KEY=your-key{"\n"}
                LLM_MODEL=your-provider-model
              </pre>
              <p className="help-text">
                Keys remain on the server. When enabled, the objective, column
                summaries and computed findings are sent to the configured
                provider.
              </p>
            </section>
            <section className="panel">
              <div className="panel-heading">
                <h2>Execution & limits</h2>
                <Server size={20} />
              </div>
              <dl className="settings-list">
                <div>
                  <dt>Worker</dt>
                  <dd>{data.worker_mode}</dd>
                </div>
                <div>
                  <dt>Maximum upload</dt>
                  <dd>{data.max_file_size_mb} MB</dd>
                </div>
                <div>
                  <dt>Maximum dataset</dt>
                  <dd>
                    {data.max_rows.toLocaleString()} rows · {data.max_columns}{" "}
                    columns
                  </dd>
                </div>
                <div>
                  <dt>Cross-validation</dt>
                  <dd>{data.defaults.cv_folds} folds by default</dd>
                </div>
                <div>
                  <dt>Retry limit</dt>
                  <dd>0–2 improvement rounds</dd>
                </div>
                <div>
                  <dt>Random seed</dt>
                  <dd>{data.defaults.random_state}</dd>
                </div>
              </dl>
              <p className="help-text">
                <ShieldCheck size={14} /> Human approval is required before
                training.
              </p>
              <a
                className="text-link"
                href={apiUrl("/health")}
                target="_blank"
                rel="noreferrer"
              >
                API health <ExternalLink size={13} />
              </a>
            </section>
          </div>
          <section className="panel">
            <div className="panel-heading">
              <h2>Your science stack</h2>
              <Code2 size={21} />
            </div>
            <div className="technology-grid">
              {Object.entries(data.versions).map(([name, version]) => (
                <div key={name}>
                  <span className="technology-icon">
                    <Check size={16} />
                  </span>
                  <strong>{name}</strong>
                  <span>{version || "Not installed"}</span>
                </div>
              ))}
            </div>
          </section>
          <p className="help-text">{data.scope}</p>
        </>
      )}
    </section>
  );
}
