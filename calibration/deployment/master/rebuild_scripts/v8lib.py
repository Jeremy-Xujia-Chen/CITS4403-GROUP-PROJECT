"""Load the original notebook's model definitions without running its experiment grids."""

import ast
import contextlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "0914-1_v8.ipynb"


def load(notebook=None):
    path = Path(notebook).resolve() if notebook else NOTEBOOK
    cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
    ns = {"__name__": "v8_model", "display": lambda *args, **kwargs: None}
    with contextlib.redirect_stdout(io.StringIO()):
        for index in [2, 4, 5, 7, 8, 9, 10, 14, 16, 18, 20, 22, 24]:
            source = "".join(cells[index]["source"])
            if index == 10:
                source = source.split("display(")[0]
            if index == 14:
                source = source.replace('Path("abm_outputs_research_plan_v7")',
                                        f"Path({str(path.parent / 'abm_outputs_research_plan_v7')!r})")
            if index == 16:
                source = source.split("fig, ax =")[0]
            exec(compile(source, f"{path.name}:cell-{index}", "exec"), ns)
        # Execute definitions verbatim using their original source spans.
        # Skip cache loaders, plots, calibration loops and simulation grids.
        for index in [28, 37, 67, 69]:
            source = "".join(cells[index]["source"])
            lines = source.splitlines(keepends=True)
            for node in ast.parse(source).body:
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)) or (
                    index == 69 and isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "EXTERNAL_ORIGIN_TARGET"
                            for target in node.targets)
                ):
                    original = "".join(lines[node.lineno - 1:node.end_lineno])
                    label = getattr(node, "name", "EXTERNAL_ORIGIN_TARGET")
                    exec(compile(original, f"{path.name}:cell-{index}:{label}", "exec"), ns)
        ns["INTERACTION_LEVELS"] = {"weak": 0.60, "medium": 1.00, "strong": 1.40}
        ns["POLICY_TYPES"] = ["baseline", "housing", "employment", "combined"]
        ns["STANDARD_INTENSITY"] = 1.0
    return ns
