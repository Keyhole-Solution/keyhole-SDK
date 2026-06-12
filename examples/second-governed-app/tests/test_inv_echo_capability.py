from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _run_gate():
    gate = Path(__file__).resolve().parent / "invariants" / "inv_echo.py"
    spec = importlib.util.spec_from_file_location("second_governed_app_inv_echo", gate)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.run_gate()


def test_echo_capability_invariant_accepts() -> None:
    assert _run_gate().to_dict()["verdict"] == "ACCEPT"
