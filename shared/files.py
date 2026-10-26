import hashlib
import json
import mimetypes
import re
from pathlib import Path

import numpy as np
import pandas as pd


def safe_run_dir(workspace: Path, run_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}", run_id):
        raise ValueError("Invalid run ID.")
    result = (workspace / run_id).resolve()
    if not result.is_relative_to(workspace.resolve()):
        raise ValueError("Invalid run directory.")
    return result


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, Path):
        return value.as_posix()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(json_safe(value), indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def artifact_inventory(run_dir: Path) -> list[dict]:
    artifacts = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file() or path.name.endswith((".tmp", ".log")) or path.name in {"input.csv", "split.json"}:
            continue
        relative = path.relative_to(run_dir).as_posix()
        if relative.startswith("internal/"):
            continue
        artifacts.append({"path": relative, "name": path.name, "size_bytes": path.stat().st_size,
                          "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return artifacts
