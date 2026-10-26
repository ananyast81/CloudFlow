import { Check, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";

export default function ModelTable({
  rows,
  metric,
  selected,
  showRun = false,
}) {
  return (
    <div className="table-scroll">
      <table className="model-table">
        <thead>
          <tr>
            <th>Model</th>
            {showRun && <th>Dataset / target</th>}
            <th>Round</th>
            <th>CV score</th>
            <th>Std. deviation</th>
            <th>Fit time</th>
            <th>Tracking</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const scoring = row.primary_metric || metric;
            const lower = ["mae", "rmse"].includes(scoring);
            const isSelected = row.selected || row.candidate_id === selected;
            return (
              <tr
                key={`${row.run_id || ""}-${row.candidate_id}`}
                className={isSelected ? "selected-row" : ""}
              >
                <td>
                  <strong>{row.model_name.replaceAll("_", " ")}</strong>
                  {isSelected && (
                    <span className="winner-label">
                      <Check size={11} /> Selected
                    </span>
                  )}
                </td>
                {showRun && (
                  <td>
                    <Link className="table-link" to={`/pipeline/${row.run_id}`}>
                      {row.filename}
                      <ExternalLink size={12} />
                    </Link>
                    <small className="table-subtitle">
                      {row.target_column}
                    </small>
                  </td>
                )}
                <td>{row.round + 1}</td>
                <td>
                  <strong>
                    {(lower ? -row.cv_score : row.cv_score).toFixed(4)}
                  </strong>
                  <small className="table-subtitle">{scoring}</small>
                </td>
                <td>± {row.cv_std.toFixed(4)}</td>
                <td>{row.duration_seconds.toFixed(1)}s</td>
                <td>
                  <span
                    className={`tracking-label ${row.mlflow_run_id ? "tracked" : ""}`}
                  >
                    {row.mlflow_run_id ? "MLflow" : "Local only"}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
