import {
  Activity,
  ArrowUpRight,
  Boxes,
  ChevronRight,
  CircleHelp,
  Cloud,
  History,
  Layers3,
  Plus,
  Settings2,
} from "lucide-react";
import {
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { useResource } from "./lib/useResource";
import NewRun from "./screens/NewRun";
import Pipeline from "./screens/Pipeline";
import HistoryPage from "./screens/History";
import Experiments from "./screens/Experiments";
import Settings from "./screens/Settings";
import "./studio.css";

const links = [
  ["/new-run", "New Run", Plus],
  ["/history", "Run history", History],
  ["/experiments", "Experiments", Layers3],
  ["/settings", "Settings", Settings2],
];

export default function Studio() {
  const location = useLocation();
  const { data: health, error } = useResource("/health", 15000);
  const current =
    links.find(([path]) => location.pathname.startsWith(path))?.[1] ||
    "Live pipeline";
  return (
    <div className="studio">
      <aside className="sidebar">
        <NavLink to="/new-run" className="brand">
          <span className="brand-mark">
            <Cloud size={24} />
          </span>
          <span>
            cloudflow<span className="brand-dot">.</span>
          </span>
        </NavLink>
        <div className="workspace-switch">
          <span className="workspace-icon">
            <Boxes size={19} />
          </span>
          <div>
            <strong>Mission control</strong>
            <small>Personal workspace</small>
          </div>
          <ChevronRight size={14} />
        </div>
        <p className="nav-caption">WORKSPACE</p>
        <nav>
          {links.map(([path, label, Icon]) => (
            <NavLink
              key={path}
              to={path}
              aria-label={label}
              className={({ isActive }) =>
                isActive ? "nav-link active" : "nav-link"
              }
            >
              <Icon size={18} />
              {label}
              {path === "/new-run" && <span className="nav-plus">+</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-note">
          <div className="note-orbit">
            <Activity size={23} />
          </div>
          <h3>
            From question
            <br />
            to understanding.
          </h3>
          <p>
            Five specialist agents.
            <br />
            One connected workflow.
          </p>
          <span>
            BUILT FOR CURIOSITY <ArrowUpRight size={13} />
          </span>
        </div>
        <div className="sidebar-bottom">
          <div className="avatar">CF</div>
          <div>
            <strong>CloudFlow workspace</strong>
            <small>Local environment</small>
          </div>
          <CircleHelp size={17} />
        </div>
      </aside>
      <div className="main-shell">
        <div className="topbar">
          <div>
            <span>Workspace</span>
            <ChevronRight size={13} />
            <strong>{current}</strong>
          </div>
          <span className={`connection ${error ? "offline" : ""}`}>
            <i />
            {error
              ? "Backend unavailable"
              : health
                ? "Backend connected"
                : "Connecting…"}
          </span>
        </div>
        <main>
          <Routes>
            <Route path="/new-run" element={<NewRun />} />
            <Route
              path="/pipeline/:runId"
              element={<Pipeline key={location.pathname} />}
            />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/experiments" element={<Experiments />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/new-run" replace />} />
          </Routes>
        </main>
        <footer className="app-footer">
          <span>CloudFlow · Multi-agent data science</span>
          <span>Understand. Experiment. Discover.</span>
        </footer>
      </div>
    </div>
  );
}
