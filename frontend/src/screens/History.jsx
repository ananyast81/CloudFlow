import { useState } from "react";
import { ArrowRight, Clock3, Plus, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { useResource } from "../lib/useResource";
import { Empty, ErrorMessage, Loading, PageHeader, Status } from "../ui/Common";

export default function HistoryPage() {
  const [offset, setOffset] = useState(0);
  const [query, setQuery] = useState("");
  const { data, error, loading, refresh } = useResource(
    `/runs?limit=25&offset=${offset}`,
    5000,
  );
  const rows =
    data?.runs.filter((r) =>
      `${r.filename} ${r.objective} ${r.status}`
        .toLowerCase()
        .includes(query.toLowerCase()),
    ) || [];
  return (
    <section>
      <PageHeader
        eyebrow="THE WORK THAT BROUGHT YOU HERE"
        title="Every analysis, in one place."
        description="Pick up a review, revisit a finding, or see how your experiments evolved."
      >
        <Link className="primary-button" to="/new-run">
          <Plus size={16} />
          New analysis
        </Link>
      </PageHeader>
      <ErrorMessage retry={refresh}>{error}</ErrorMessage>
      <section className="panel">
        <div className="list-toolbar">
          <h2>
            Run history <span className="count-pill">{data?.total || 0}</span>
          </h2>
          <label className="search-box">
            <Search size={16} />
            <input
              aria-label="Search runs on this page"
              placeholder="Search this page…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
        </div>
        {loading ? (
          <Loading />
        ) : !data?.total ? (
          <Empty title="Your next discovery starts here" icon={Clock3}>
            <p>Launch your first analysis to build a history of results.</p>
            <Link className="text-link" to="/new-run">
              Create an analysis <ArrowRight size={14} />
            </Link>
          </Empty>
        ) : (
          <>
            <div className="table-scroll">
              <table className="runs-table">
                <thead>
                  <tr>
                    <th>Analysis</th>
                    <th>Problem</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {rows.map((run) => (
                    <tr key={run.run_id}>
                      <td>
                        <Link
                          className="run-title"
                          to={`/pipeline/${run.run_id}`}
                        >
                          {run.filename}
                        </Link>
                        <small className="table-subtitle objective-snippet">
                          {run.objective}
                        </small>
                      </td>
                      <td>
                        {run.task_type}
                        <small className="table-subtitle">
                          {run.target_column || "Detecting target"}
                        </small>
                      </td>
                      <td>
                        <Status value={run.status} />
                      </td>
                      <td>
                        {new Date(run.created_at).toLocaleDateString()}
                        <small className="table-subtitle">
                          {new Date(run.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </small>
                      </td>
                      <td>
                        <Link
                          className="icon-button"
                          aria-label={`Open ${run.filename}`}
                          to={`/pipeline/${run.run_id}`}
                        >
                          <ArrowRight size={17} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {rows.length === 0 && (
              <p className="help-text">No matching runs on this page.</p>
            )}
            <div className="pagination">
              <span>
                {offset + 1}–{Math.min(offset + 25, data.total)} of {data.total}{" "}
                runs
              </span>
              <div>
                <button
                  className="secondary-button small"
                  disabled={!offset}
                  onClick={() => setOffset((value) => Math.max(0, value - 25))}
                >
                  Previous
                </button>
                <button
                  className="secondary-button small"
                  disabled={offset + 25 >= data.total}
                  onClick={() => setOffset((value) => value + 25)}
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </section>
    </section>
  );
}
