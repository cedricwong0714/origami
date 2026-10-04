"""Markdown residual report from a plate-versus-freeze comparison."""

from __future__ import annotations

from typing import Any


def freeze_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Prediction versus observation",
        "",
        "calibrated: false",
        "",
        report.get("note", ""),
        "",
        "| construct | n | status | observed | predicted | residual | in interval |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in report.get("comparisons", []):
        if row.get("status") != "compared":
            lines.append(
                f"| {row.get('construct')} | {row.get('n_repeats')} | {row.get('status')} | — | — | — | — |"
            )
            continue
        flag = "yes" if row.get("within_95ci") else "no"
        lines.append(
            "| {c} | {n} | compared | {obs:.4g} | {pred:.4g} | {err:.4g} | {flag} |".format(
                c=row.get("construct"),
                n=row.get("n_repeats"),
                obs=row["observed"],
                pred=row["predicted"],
                err=row["error"],
                flag=flag,
            )
        )
    lines.append("")
    lines.append(f"untested frozen keys: {len(report.get('untested_predictions', []))}")
    pe = report.get("parameter_error") or {}
    lines.append(
        f"parameter_error_propagated: {pe.get('parameter_error_propagated', False)}"
    )
    return "\n".join(lines) + "\n"
