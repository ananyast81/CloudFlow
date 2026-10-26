import { AlertCircle, ArrowUpRight, LoaderCircle } from "lucide-react";

export function Status({ value }) {
  return (
    <span className={`status status-${value}`}>
      <i />
      {value?.replaceAll("_", " ")}
    </span>
  );
}

export function ErrorMessage({ children, retry }) {
  if (!children) return null;
  return (
    <div role="alert" className="error-message">
      <AlertCircle size={18} />
      <span>{children}</span>
      {retry && (
        <button className="text-button" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function Loading({ text = "Loading your workspace…" }) {
  return (
    <div className="empty-state">
      <LoaderCircle className="spin" size={24} />
      <p>{text}</p>
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, children }) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {children}
    </header>
  );
}

export function Empty({ title, children, icon: Icon = ArrowUpRight }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Icon size={26} />
      </div>
      <h3>{title}</h3>
      {children}
    </div>
  );
}

export function Metric({ label, value, note }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
      {note && <small>{note}</small>}
    </div>
  );
}
