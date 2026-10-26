"""Refresh completed HTML exports from saved artifacts without retraining or LLM calls."""
import argparse

from agents.eval_report_agent.html_report import write_html_report
from shared.config import Settings
from shared.files import artifact_inventory, safe_run_dir
from shared.repository import RunRepository


def repair_report(settings: Settings, run_id: str):
    repository = RunRepository(settings.workspace)
    directory = safe_run_dir(settings.workspace, run_id)
    record = repository.get(run_id)
    if record.status != "completed" or record.state is None:
        raise ValueError("Only completed reports can be refreshed.")
    path = write_html_report(directory, (directory / "report.md").read_text(encoding="utf-8"),
                             record.state.eda.get("plots", []))
    inventory = artifact_inventory(directory)

    def refresh(run):
        run.artifacts = inventory

    repository.update(run_id, refresh)
    repository.event(run_id, "reporting", "HTML export refreshed with embedded EDA images; models and results unchanged.")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--run-id")
    selection.add_argument("--all-completed", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    if args.run_id:
        identifiers = [args.run_id]
    else:
        repository = RunRepository(settings.workspace)
        identifiers = []
        offset = 0
        while True:
            records, total = repository.list(100, offset)
            identifiers.extend(r.run_id for r in records if r.status == "completed")
            offset += len(records)
            if offset >= total or not records:
                break
    for run_id in identifiers:
        print(repair_report(settings, run_id))


if __name__ == "__main__":
    main()
