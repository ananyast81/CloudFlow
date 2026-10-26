"""One configuration contract shared by API, worker and command-line tools."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass
class Settings:
    workspace: Path = field(default_factory=lambda: Path(os.getenv("CLOUDFLOW_WORKSPACE", str(ROOT / "workspace"))).resolve())
    max_upload_bytes: int = 10 * 1024 * 1024
    max_rows: int = 20_000
    max_columns: int = 100
    max_run_seconds: int = 1800
    lease_seconds: int = 60
    auto_worker: bool = field(default_factory=lambda: os.getenv("CLOUDFLOW_AUTO_WORKER", "true").lower() == "true")
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "none").lower())
    llm_api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""), repr=False)
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", ""))
    mlflow_tracking_uri: str = field(default_factory=lambda: os.getenv("MLFLOW_TRACKING_URI", ""))
    allowed_origins: list[str] = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","))

    @property
    def llm_ready(self) -> bool:
        return self.llm_provider in {"groq", "gemini"} and bool(self.llm_api_key.strip() and self.llm_model.strip())

    @property
    def tracking_uri(self) -> str:
        return self.mlflow_tracking_uri or f"sqlite:///{(self.workspace / 'mlflow.db').as_posix()}"

    def initialize(self) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
