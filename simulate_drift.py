# Inspect drift scores for any scenario without running the full pipeline.
#
# Usage:
#   python simulate_drift.py normal
#   python simulate_drift.py night_shift
#   python simulate_drift.py high_value
#   python simulate_drift.py foreign

import sys
from adapters.fraud import load_baseline, simulate_drift, CATEGORICAL_COLUMNS
from core.drift import calculate_drift


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else 'normal'
    print(f"\n🔍 Drift report for scenario: '{scenario}'\n")

    baseline = load_baseline()
    current = simulate_drift(baseline, scenario)

    reports = calculate_drift(baseline, current, categorical_columns=CATEGORICAL_COLUMNS)

    print(f"{'Feature':<30} {'PSI Score':>10}  {'Status'}")
    print("-" * 55)
    for feature, report in reports.items():
        status = "🔴 DRIFT" if report.drifted else "🟢 OK"
        print(f"{feature:<30} {report.psi_score:>10.4f}  {status}")


if __name__ == '__main__':
    main()