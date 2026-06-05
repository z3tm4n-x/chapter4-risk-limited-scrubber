#!/usr/bin/env python3
"""Import the Chapter 3 proton-only upsets.xlsx file and reconstruct nu_total(t).

The script uses only the Python standard library, so it does not require
openpyxl or pandas inside WSL.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import statistics
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "ch3_main_1pct.json"
XLSX_PATH = REPO_ROOT / "data" / "raw" / "upsets.xlsx"
OUTPUT_CSV = REPO_ROOT / "data" / "ch3_five_year_upsets.csv"
SUMMARY_CSV = REPO_ROOT / "results" / "schedules" / "ch3_series_import_summary.csv"
SUMMARY_JSON = REPO_ROOT / "results" / "schedules" / "ch3_series_import_summary.json"

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
}


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def excel_serial_to_utc_iso(value: float) -> str:
    # Convert Excel serial time to an hourly UTC timestamp.  The spreadsheet
    # stores hourly values as fractions of a day, and values such as
    # 44197.0416667 can otherwise land at 00:59:59.999... due to floating
    # representation.  Rounding absolute hours preserves the intended hourly
    # grid.
    base = dt.datetime(1899, 12, 30, tzinfo=dt.timezone.utc)
    absolute_hours = round(value * 24.0)
    timestamp = base + dt.timedelta(hours=absolute_hours)
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []

    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []

    for si in root.findall("main:si", NS):
        parts = []
        for text_node in si.findall(".//main:t", NS):
            parts.append(text_node.text or "")
        values.append("".join(parts))

    return values


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value_node = cell.find("main:v", NS)

    if value_node is None:
        inline = cell.find("main:is/main:t", NS)
        return inline.text if inline is not None else ""

    raw = value_node.text or ""

    if cell_type == "s":
        return shared_strings[int(raw)]

    return raw


def cell_column(cell_ref: str) -> str:
    return "".join(ch for ch in cell_ref if ch.isalpha())


def first_sheet_path(zf: zipfile.ZipFile) -> str:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))

    rel_map = {}
    for rel in rels:
        rel_map[rel.attrib["Id"]] = rel.attrib["Target"]

    first_sheet = workbook.find("main:sheets/main:sheet", {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    })
    if first_sheet is None:
        raise RuntimeError("workbook has no sheets")

    rid = first_sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
    target = rel_map[rid]

    if target.startswith("/"):
        return target[1:]
    if target.startswith("xl/"):
        return target
    return "xl/" + target


def read_upsets_xlsx() -> list[dict[str, str]]:
    if not XLSX_PATH.exists():
        raise FileNotFoundError(f"missing input file: {XLSX_PATH}")

    with zipfile.ZipFile(XLSX_PATH) as zf:
        shared_strings = read_shared_strings(zf)
        sheet_path = first_sheet_path(zf)
        root = ET.fromstring(zf.read(sheet_path))

        parsed_rows: list[dict[str, str]] = []

        for row_node in root.findall("main:sheetData/main:row", NS):
            row_values: dict[str, str] = {}

            for cell in row_node.findall("main:c", NS):
                ref = cell.attrib.get("r", "")
                col = cell_column(ref)
                row_values[col] = cell_value(cell, shared_strings).strip()

            if row_values:
                parsed_rows.append(row_values)

    if not parsed_rows:
        raise RuntimeError("no rows found in xlsx")

    header_index = None

    for idx, candidate in enumerate(parsed_rows):
        a_value = candidate.get("A", "").strip().lower()
        b_value = candidate.get("B", "").strip().lower()
        c_value = candidate.get("C", "").strip().lower()

        # Some versions of upsets.xlsx have an empty A header and only
        # B="time", C="upsets". Accept both forms.
        if b_value == "time" and c_value == "upsets" and a_value in ("", "index"):
            header_index = idx
            break

    if header_index is None:
        preview = parsed_rows[:10]
        raise RuntimeError(f"could not find header row with B=time and C=upsets; preview={preview!r}")

    data_rows: list[dict[str, str]] = []

    for row_offset, row in enumerate(parsed_rows[header_index + 1 :], start=0):
        row_number = header_index + 2 + row_offset

        index_raw = row.get("A", "")
        excel_raw = row.get("B", "")
        upsets_raw = row.get("C", "")

        if not index_raw and not excel_raw and not upsets_raw:
            continue

        try:
            hour_index = int(float(index_raw)) if index_raw != "" else len(data_rows)
            excel_time = float(excel_raw)
        except ValueError as exc:
            raise RuntimeError(f"invalid row {row_number}: {row}") from exc

        upsets_value = None
        if upsets_raw != "":
            try:
                upsets_value = float(upsets_raw)
            except ValueError as exc:
                raise RuntimeError(f"invalid upsets value at row {row_number}: {upsets_raw!r}") from exc

        data_rows.append(
            {
                "hour_index": str(hour_index),
                "excel_time": f"{excel_time:.12g}",
                "timestamp_utc": excel_serial_to_utc_iso(excel_time),
                "upsets_proton_raw": "" if upsets_value is None else f"{upsets_value:.12g}",
            }
        )

    # Validate that the canonical timestamps form a strict hourly grid.
    parsed_times = [
        dt.datetime.strptime(row["timestamp_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        for row in data_rows
    ]

    for idx in range(1, len(parsed_times)):
        delta = parsed_times[idx] - parsed_times[idx - 1]
        if delta != dt.timedelta(hours=1):
            raise RuntimeError(
                "non-hourly timestamp grid at row "
                f"{idx}: {data_rows[idx - 1]['timestamp_utc']} -> {data_rows[idx]['timestamp_utc']}"
            )

    return data_rows


def linear_fill(values: list[float | None]) -> tuple[list[float], list[str]]:
    filled = [0.0 for _ in values]
    methods = ["" for _ in values]

    known_indices = [idx for idx, value in enumerate(values) if value is not None]
    if not known_indices:
        raise RuntimeError("all proton values are missing")

    for idx, value in enumerate(values):
        if value is not None:
            filled[idx] = value
            methods[idx] = "raw"
            continue

        left = next((known for known in reversed(known_indices) if known < idx), None)
        right = next((known for known in known_indices if known > idx), None)

        if left is not None and right is not None:
            left_value = values[left]
            right_value = values[right]
            assert left_value is not None and right_value is not None
            ratio = (idx - left) / (right - left)
            filled[idx] = left_value + ratio * (right_value - left_value)
            methods[idx] = "linear_interpolation"
        elif left is not None:
            left_value = values[left]
            assert left_value is not None
            filled[idx] = left_value
            methods[idx] = "forward_fill"
        elif right is not None:
            right_value = values[right]
            assert right_value is not None
            filled[idx] = right_value
            methods[idx] = "backward_fill"
        else:
            raise RuntimeError("unreachable fill state")

    return filled, methods


def quantile_linear(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("empty quantile input")

    sorted_values = sorted(values)

    if len(sorted_values) == 1:
        return sorted_values[0]

    position = q * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return sorted_values[lower]

    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def rolling_background(values: list[float], window_hours: int, q: float) -> list[float]:
    background = []

    for idx in range(len(values)):
        start = max(0, idx - window_hours + 1)
        window = values[start : idx + 1]
        background.append(quantile_linear(window, q))

    return background


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def population_variance(values: list[float]) -> float:
    mu = mean(values)
    return sum((value - mu) ** 2 for value in values) / len(values)


def cv2(values: list[float]) -> float:
    mu = mean(values)
    if mu == 0.0:
        return float("inf")
    return population_variance(values) / (mu * mu)


def positive_log_growth_stats(values: list[float]) -> dict[str, float]:
    logs = []
    positive = []

    for prev, current in zip(values, values[1:], strict=False):
        if prev <= 0.0 or current <= 0.0:
            continue

        delta = math.log10(current / prev)
        logs.append(delta)

        if delta > 0.0:
            positive.append(delta)

    if not logs:
        return {
            "positive_log_growth_q99": 0.0,
            "positive_growth_factor_q99": 1.0,
            "max_growth_factor": 1.0,
            "max_log_growth": 0.0,
        }

    q99 = quantile_linear(positive, 0.99) if positive else 0.0
    max_log = max(logs)

    return {
        "positive_log_growth_q99": q99,
        "positive_growth_factor_q99": 10.0 ** q99,
        "max_growth_factor": 10.0 ** max_log,
        "max_log_growth": max_log,
    }


def missing_intervals(rows: list[dict[str, str]], raw_values: list[float | None]) -> list[dict[str, str]]:
    intervals = []
    start = None

    extended = raw_values + [0.0]
    for idx, value in enumerate(extended):
        is_missing = value is None if idx < len(raw_values) else False

        if is_missing and start is None:
            start = idx

        if not is_missing and start is not None:
            end = idx - 1
            intervals.append(
                {
                    "start_hour_index": rows[start]["hour_index"],
                    "end_hour_index": rows[end]["hour_index"],
                    "start_timestamp_utc": rows[start]["timestamp_utc"],
                    "end_timestamp_utc": rows[end]["timestamp_utc"],
                    "length_hours": str(end - start + 1),
                }
            )
            start = None

    return intervals


def write_output_rows(
    rows: list[dict[str, str]],
    proton_filled: list[float],
    fill_methods: list[str],
    background: list[float],
    event_component: list[float],
    total: list[float],
    config: dict,
) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "hour_index",
        "timestamp_utc",
        "excel_time",
        "upsets_proton_raw",
        "upsets_proton_filled",
        "is_missing_proton",
        "fill_method",
        "background_proton_gp",
        "event_proton_sp",
        "gcl_ratio",
        "skl_ratio",
        "upsets_total_nu",
    ]

    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for row, filled, method, gp, sp, nu in zip(
            rows, proton_filled, fill_methods, background, event_component, total, strict=True
        ):
            raw = row["upsets_proton_raw"]
            writer.writerow(
                {
                    "hour_index": row["hour_index"],
                    "timestamp_utc": row["timestamp_utc"],
                    "excel_time": row["excel_time"],
                    "upsets_proton_raw": raw,
                    "upsets_proton_filled": f"{filled:.12g}",
                    "is_missing_proton": str(raw == "").lower(),
                    "fill_method": method,
                    "background_proton_gp": f"{gp:.12g}",
                    "event_proton_sp": f"{sp:.12g}",
                    "gcl_ratio": f"{config['gcl_ratio']:.12g}",
                    "skl_ratio": f"{config['skl_ratio']:.12g}",
                    "upsets_total_nu": f"{nu:.12g}",
                }
            )


def build_summary(config, rows, raw_values, proton_filled, background, event_component, total):
    valid_raw = [value for value in raw_values if value is not None]
    missing_count = len(raw_values) - len(valid_raw)
    log_stats = positive_log_growth_stats(total)
    missing_spans = missing_intervals(rows, raw_values)

    metrics = {
        "input_xlsx_sha256": sha256_file(XLSX_PATH),
        "hour_count": len(rows),
        "valid_proton_count": len(valid_raw),
        "missing_proton_count": missing_count,
        "missing_interval_count": len(missing_spans),
        "start_timestamp_utc": rows[0]["timestamp_utc"],
        "end_timestamp_utc": rows[-1]["timestamp_utc"],
        "proton_filled_sum": sum(proton_filled),
        "proton_filled_mean": mean(proton_filled),
        "proton_filled_median": statistics.median(proton_filled),
        "proton_filled_max": max(proton_filled),
        "proton_filled_cv2": cv2(proton_filled),
        "proton_filled_eta_const": 1.0 + cv2(proton_filled),
        "background_gp_mean": mean(background),
        "event_sp_mean": mean(event_component),
        "total_nu_sum": sum(total),
        "total_nu_mean": mean(total),
        "total_nu_median": statistics.median(total),
        "total_nu_max": max(total),
        "total_nu_cv2": cv2(total),
        "total_nu_eta_const": 1.0 + cv2(total),
        **log_stats,
    }

    metric_rows = []
    for key, value in metrics.items():
        if isinstance(value, float):
            metric_rows.append({"metric": key, "value": f"{value:.12g}"})
        else:
            metric_rows.append({"metric": key, "value": str(value)})

    for idx, interval in enumerate(missing_spans):
        metric_rows.append({"metric": f"missing_interval_{idx}_start", "value": interval["start_timestamp_utc"]})
        metric_rows.append({"metric": f"missing_interval_{idx}_end", "value": interval["end_timestamp_utc"]})
        metric_rows.append({"metric": f"missing_interval_{idx}_length_hours", "value": interval["length_hours"]})

    expected = config.get("expected_checks", {})
    tolerances = config.get("tolerances", {})

    if "mean_total_per_hour_reference" in expected:
        ref = float(expected["mean_total_per_hour_reference"])
        rel = abs(metrics["total_nu_mean"] - ref) / ref
        metric_rows.append({"metric": "check_mean_total_relative_error", "value": f"{rel:.12g}"})
        metric_rows.append({"metric": "check_mean_total_within_tolerance", "value": str(rel <= tolerances.get("mean_total_relative", 0.02)).lower()})

    if "cv2_total_reference" in expected:
        ref = float(expected["cv2_total_reference"])
        rel = abs(metrics["total_nu_cv2"] - ref) / ref
        metric_rows.append({"metric": "check_cv2_total_relative_error", "value": f"{rel:.12g}"})
        metric_rows.append({"metric": "check_cv2_total_within_tolerance", "value": str(rel <= tolerances.get("cv2_total_relative", 0.02)).lower()})

    if "eta_const_reference" in expected:
        ref = float(expected["eta_const_reference"])
        rel = abs(metrics["total_nu_eta_const"] - ref) / ref
        metric_rows.append({"metric": "check_eta_const_relative_error", "value": f"{rel:.12g}"})
        metric_rows.append({"metric": "check_eta_const_within_tolerance", "value": str(rel <= tolerances.get("eta_const_relative", 0.02)).lower()})

    return metric_rows, metrics, missing_spans


def main() -> int:
    config = read_config()
    rows = read_upsets_xlsx()

    raw_values = []
    for row in rows:
        raw = row["upsets_proton_raw"]
        raw_values.append(None if raw == "" else float(raw))

    proton_filled, fill_methods = linear_fill(raw_values)
    proton_scale = float(config.get("proton_scale", 1.0))
    proton_filled = [value * proton_scale for value in proton_filled]

    background = rolling_background(
        proton_filled,
        int(config["background_window_hours"]),
        float(config["background_quantile"]),
    )
    event_component = [max(value - gp, 0.0) for value, gp in zip(proton_filled, background, strict=True)]

    gcl_ratio = float(config["gcl_ratio"])
    skl_ratio = float(config["skl_ratio"])
    total = [
        gp * (1.0 + gcl_ratio) + sp * (1.0 + skl_ratio)
        for gp, sp in zip(background, event_component, strict=True)
    ]

    write_output_rows(rows, proton_filled, fill_methods, background, event_component, total, config)
    metric_rows, metrics, missing_spans = build_summary(
        config, rows, raw_values, proton_filled, background, event_component, total
    )

    SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(metric_rows)

    with SUMMARY_JSON.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "config": config,
                "metrics": metrics,
                "missing_intervals": missing_spans,
                "output_csv": str(OUTPUT_CSV.relative_to(REPO_ROOT)),
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("Imported:", XLSX_PATH)
    print("Wrote:", OUTPUT_CSV)
    print("Wrote:", SUMMARY_CSV)
    print("hours:", metrics["hour_count"])
    print("missing_proton_count:", metrics["missing_proton_count"])
    print("proton_eta_const:", f"{metrics['proton_filled_eta_const']:.6f}")
    print("total_mean:", f"{metrics['total_nu_mean']:.6f}")
    print("total_cv2:", f"{metrics['total_nu_cv2']:.6f}")
    print("total_eta_const:", f"{metrics['total_nu_eta_const']:.6f}")
    print("total_max:", f"{metrics['total_nu_max']:.6f}")
    print("q99 positive growth factor:", f"{metrics['positive_growth_factor_q99']:.6f}")
    print("max growth factor:", f"{metrics['max_growth_factor']:.6f}")

    expected = config.get("expected_checks", {})

    if "hour_count" in expected and metrics["hour_count"] != int(expected["hour_count"]):
        raise RuntimeError(f"hour count mismatch: {metrics['hour_count']} != {expected['hour_count']}")

    if "missing_proton_count" in expected and metrics["missing_proton_count"] != int(expected["missing_proton_count"]):
        raise RuntimeError(
            f"missing count mismatch: {metrics['missing_proton_count']} != {expected['missing_proton_count']}"
        )

    if "start_timestamp_utc" in expected and metrics["start_timestamp_utc"] != expected["start_timestamp_utc"]:
        raise RuntimeError("start timestamp mismatch")

    if "end_timestamp_utc" in expected and metrics["end_timestamp_utc"] != expected["end_timestamp_utc"]:
        raise RuntimeError("end timestamp mismatch")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
