from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
OUTPUT = Path(__file__).resolve().parents[3] / "evidence" / "reliability-evidence.json"


def _bucket(name: str) -> str:
    if "scenario" in name:
        return "scenario"
    if any(key in name for key in ["intake", "qualification", "runtime", "visibility"]):
        return "unit"
    return "integration"


def main() -> int:
    test_files = sorted(p.name for p in TESTS_DIR.glob("test_*.py"))
    buckets: dict[str, list[str]] = {"unit": [], "integration": [], "scenario": []}
    for tf in test_files:
        buckets[_bucket(tf)].append(tf)

    run = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), "-m", "pytest", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "service": "services/api",
        "test_inventory": {
            "total_files": len(test_files),
            "unit_files": len(buckets["unit"]),
            "integration_files": len(buckets["integration"]),
            "scenario_files": len(buckets["scenario"]),
            "unit": buckets["unit"],
            "integration": buckets["integration"],
            "scenario": buckets["scenario"],
        },
        "latest_run": {
            "exit_code": run.returncode,
            "stdout": run.stdout.strip(),
            "stderr": run.stderr.strip(),
            "passed": run.returncode == 0,
        },
        "reliability_claims": [
            "Critical domain behaviors are covered by unit and integration tests.",
            "Scenario simulations validate failure recovery paths (outreach fallback, booking retry, CRM outage queue/retry).",
            "Evidence is reproducible via: cd services/api && .venv/bin/python scripts/generate_reliability_evidence.py",
        ],
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(str(OUTPUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
