import { useEffect, useRef, useState } from "react";
import { artifactRequest } from "../lib/api";
import { ErrorMessage } from "./Common";

export default function Chart({ runId, path }) {
  const element = useRef(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    let plotly;
    const container = element.current;
    const controller = new AbortController();
    let observer;
    Promise.all([
      import("plotly.js-dist-min"),
      artifactRequest(runId, path, { signal: controller.signal }),
    ])
      .then(async ([module, figure]) => {
        if (!active) return;
        plotly = module.default;
        await plotly.newPlot(
          container,
          figure.data,
          {
            ...figure.layout,
            autosize: true,
            font: { family: "Inter, system-ui, sans-serif", color: "#b6c3d7" },
            paper_bgcolor: "#111c2e",
            plot_bgcolor: "#111c2e",
          },
          {
            responsive: true,
            displaylogo: false,
            modeBarButtonsToRemove: ["lasso2d", "select2d"],
          },
        );
        if (!active) {
          plotly.purge(container);
          return;
        }
        observer = new ResizeObserver(() => plotly.Plots.resize(container));
        observer.observe(container);
      })
      .catch((err) => {
        if (active && err.name !== "AbortError") setError(err.message);
      });
    return () => {
      active = false;
      controller.abort();
      observer?.disconnect();
      if (plotly) plotly.purge(container);
    };
  }, [runId, path]);
  return (
    <div className="chart-card">
      <ErrorMessage>{error}</ErrorMessage>
      <div
        className="plot"
        ref={element}
        aria-label={path.replace("-chart.json", " chart")}
      />
    </div>
  );
}
