import { useState } from "react";
import { FlaskConical } from "lucide-react";
import { useResource } from "../lib/useResource";
import { Empty, ErrorMessage, Loading, PageHeader } from "../ui/Common";
import ModelTable from "../ui/ModelTable";

export default function Experiments() {
  const [offset, setOffset] = useState(0);
  const { data, error, loading, refresh } = useResource(
    `/experiments?limit=25&offset=${offset}`,
    5000,
  );
  const [filter, setFilter] = useState("all");
  const rows =
    data?.experiments.filter(
      (row) => filter === "all" || row.task_type === filter,
    ) || [];
  return (
    <section>
      <PageHeader
        eyebrow="LEARN FROM EVERY ITERATION"
        title="A space for better models."
        description="Compare candidates, inspect validation scores, and trace every experiment back to its data."
      />
      <ErrorMessage retry={refresh}>{error}</ErrorMessage>
      <section className="panel">
        <div className="list-toolbar">
          <h2>Model experiments</h2>
          <select
            aria-label="Filter experiments by task"
            className="compact-select"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">All problem types</option>
            <option value="classification">Classification</option>
            <option value="regression">Regression</option>
          </select>
        </div>
        <p className="help-text">
          Compare scores within the same dataset, target and metric. Lower
          MAE/RMSE is better; other displayed scores are higher-is-better.
        </p>
        {loading ? (
          <Loading />
        ) : rows.length ? (
          <ModelTable rows={rows} showRun />
        ) : (
          <Empty title="Experiments will appear here" icon={FlaskConical}>
            <p>Approve a training plan to begin comparing models.</p>
          </Empty>
        )}
        <div className="pagination">
          <span>
            Experiments from runs {data?.total_runs ? offset + 1 : 0}–
            {Math.min(offset + 25, data?.total_runs || 0)}
          </span>
          <div>
            <button
              className="secondary-button small"
              disabled={!offset}
              onClick={() => setOffset((value) => value - 25)}
            >
              Previous
            </button>
            <button
              className="secondary-button small"
              disabled={offset + 25 >= (data?.total_runs || 0)}
              onClick={() => setOffset((value) => value + 25)}
            >
              Next
            </button>
          </div>
        </div>
      </section>
    </section>
  );
}
