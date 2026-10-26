"""Execute trusted handlers and export a notebook for inspection/reproduction."""
from pathlib import Path

import nbformat

from agents.data_prep_agent.operations import execute_operation
from shared.data import normalize_frame
from shared.dataset_validation import load_dataset
from shared.files import write_json


def run_notebook(generated_code, input_path, output_dir, timeout=300):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    df = normalize_frame(load_dataset(str(input_path)))
    before = len(df)
    results = {}
    cells = [nbformat.v4.new_markdown_cell("# Data preparation\nOperations were executed by the trusted dispatcher. These notebook cells are supplied for reproduction and have not been executed as a notebook."),
        nbformat.v4.new_code_cell("from agents.data_prep_agent.operations import execute_operation\nfrom shared.data import normalize_frame\nimport pandas as pd\ndf = normalize_frame(pd.read_csv('../input.csv'))\noperation_results = {}")]
    for step in generated_code.cells:
        # Never execute the supplied code string. Only the declared operation is dispatched.
        df, details = execute_operation(df, step.operation, step.params)
        results[f"step_{step.step}"] = {"operation": step.operation, "status": "completed", "result": details}
        source = f"df, details = execute_operation(df, {step.operation!r}, {step.params!r})\noperation_results['step_{step.step}'] = details"
        cells.append(nbformat.v4.new_code_cell(source))
    df.to_csv(output_dir / "cleaned.csv", index=False)
    cells.append(nbformat.v4.new_code_cell("df.to_csv('cleaned-reproduced.csv', index=False)"))
    nbformat.write(nbformat.v4.new_notebook(cells=cells), output_dir / "preparation.ipynb")
    write_json(output_dir / "operation_results.json", results)
    report = {"rows_before": before, "rows_after": len(df), "columns_after": len(df.columns),
              "column_names": list(df.columns), "operation_results": results,
              "execution": "Trusted Python handlers; no generated code execution."}
    return df, report
