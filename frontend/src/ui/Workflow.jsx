import {
  Activity,
  BrainCircuit,
  Check,
  Circle,
  Database,
  FileText,
  FlaskConical,
  ScanSearch,
  ShieldCheck,
  UserRoundCheck,
} from "lucide-react";

const stages = [
  ["data_understanding", "Data understanding", Database, "Profile & clean"],
  [
    "analysis_features",
    "Analysis & features",
    ScanSearch,
    "Explore & transform",
  ],
  ["human_review", "Human review", UserRoundCheck, "Validate the plan"],
  ["modeling", "Modeling", BrainCircuit, "Train & compare"],
  ["evaluation", "Evaluation", FlaskConical, "Diagnose & improve"],
  ["reporting", "Reporting", FileText, "Explain & deliver"],
];

export default function Workflow({
  agents = {},
  selected,
  onSelect,
  compact = false,
}) {
  return (
    <div className={`workflow ${compact ? "workflow-compact" : ""}`}>
      {!compact && (
        <>
          <svg
            className="orbit-paths"
            viewBox="0 0 700 560"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <ellipse cx="350" cy="280" rx="255" ry="205" />
            <ellipse cx="350" cy="280" rx="195" ry="150" />
            {[
              [175, 100],
              [525, 100],
              [595, 280],
              [525, 460],
              [175, 460],
              [105, 280],
            ].map(([x, y]) => (
              <line key={`${x}-${y}`} x1="350" y1="280" x2={x} y2={y} />
            ))}
          </svg>
          <div className="orchestrator-core">
            <Activity size={30} strokeWidth={1.5} />
            <span>CONTROL CENTER</span>
            <strong>Orchestrator</strong>
            <small>Workflow coordination</small>
          </div>
        </>
      )}
      {stages.map(([id, label, Icon, caption], index) => {
        const status = agents[id]?.status || "pending";
        return (
          <button
            key={id}
            type="button"
            onClick={() => onSelect?.(id)}
            disabled={!onSelect}
            className={`workflow-node stage-${id} node-${status} ${selected === id ? "is-selected" : ""}`}
            aria-label={`${label}: ${status}`}
            aria-pressed={selected === id}
          >
            <div className="node-top">
              <span className="node-number">0{index + 1}</span>
              {status === "completed" ? (
                <Check size={13} />
              ) : status === "waiting" ? (
                <ShieldCheck size={13} />
              ) : (
                <Circle size={7} fill="currentColor" />
              )}
            </div>
            <div className="node-icon">
              <Icon size={23} strokeWidth={1.7} />
            </div>
            <strong>{label}</strong>
            <small>{caption}</small>
            <span className="node-state">{status}</span>
          </button>
        );
      })}
    </div>
  );
}
