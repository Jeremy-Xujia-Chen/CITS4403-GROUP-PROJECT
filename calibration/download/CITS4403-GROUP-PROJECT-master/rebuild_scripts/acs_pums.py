"""Rebuild four ACS 2023 young-adult mobility tables from eight local person ZIPs."""

import argparse
import csv
import io
import zipfile
from collections import defaultdict
from pathlib import Path

# Official ACS 2023 1-year person ZIPs: csv_pca.zip, csv_ptx.zip,
# csv_pny.zip, csv_pfl.zip, csv_pma.zip, csv_pnc.zip, csv_pil.zip, csv_pwa.zip.
# Each contains psam_p{FIPS:02d}.csv. Extracted CSVs are also accepted.
# Download source: https://www.census.gov/programs-surveys/acs/microdata/access.2023.html
STATES = {"CA": 6, "TX": 48, "NY": 36, "FL": 12,
          "MA": 25, "NC": 37, "IL": 17, "WA": 53}
FIELDS = ["weighted_population", "weighted_interstate_movers",
          "unweighted_population", "unweighted_interstate_movers"]


def person_rows(folder, state, fips):
    filename = f"psam_p{fips:02d}.csv"
    path = folder / filename
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as stream:
            yield from csv.DictReader(stream)
        return
    path = folder / f"csv_p{state.lower()}.zip"
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist()
                   if Path(name).name.lower() == filename]
        if len(members) != 1:
            raise ValueError(f"{path}: expected exactly one {filename}")
        with archive.open(members[0]) as binary:
            with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as stream:
                yield from csv.DictReader(stream)


def number(row, field, default=-1):
    value = row.get(field, "")
    return int(float(value)) if value and value.strip() else default


def write_table(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def rebuild(input_dir, output_dir):
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    by_state, by_age, external = [], defaultdict(lambda: [0, 0, 0, 0]), []
    for state, fips in STATES.items():
        totals, outside = [0, 0, 0, 0], [0, 0, 0, 0]
        for row in person_rows(input_dir, state, fips):
            age = number(row, "AGEP")
            if not 18 <= age <= 35:
                continue
            current = number(row, "ST", fips)
            if current != fips:
                raise ValueError(f"{state} file contains current-state FIPS {current}")
            weight, previous = number(row, "PWGTP"), number(row, "MIGSP")
            if weight < 0:
                raise ValueError("PWGTP must be a non-negative person weight")
            # Mobility anchor excludes Puerto Rico and foreign origins.
            moved = number(row, "MIG") == 3 and 1 <= previous <= 56 and previous != current
            delta = [weight, weight * moved, 1, int(moved)]
            totals = [a + b for a, b in zip(totals, delta)]
            by_age[age] = [a + b for a, b in zip(by_age[age], delta)]
            # Scope audit additionally counts Puerto Rico (72) as outside,
            # matching the supplied provenance and external-origin cache.
            incoming = number(row, "MIG") == 3 and (1 <= previous <= 56 or previous == 72) and previous != current
            if incoming:
                is_outside = previous not in STATES.values()
                outside = [outside[0] + weight, outside[1] + weight * is_outside,
                           outside[2] + 1, outside[3] + int(is_outside)]
        if not totals[0]:
            raise ValueError(f"{state}: no weighted 18-35 population")
        by_state.append({"state": state, **dict(zip(FIELDS, totals)),
                         "move_rate": totals[1] / totals[0]})
        external.append({"state": state, "weighted_interstate_inmovers": outside[0],
                         "weighted_from_other_us": outside[1],
                         "weighted_from_model_states": outside[0] - outside[1],
                         "unweighted_interstate_inmovers": outside[2],
                         "unweighted_from_other_us": outside[3],
                         "external_origin_share": outside[1] / outside[0] if outside[0] else 0.0})
    sums = [sum(row[field] for row in by_state) for field in FIELDS]
    anchor = {"year": 2023, "age_min": 18, "age_max": 35, "move_rate": sums[1] / sums[0],
              **dict(zip(FIELDS, sums)), "scope": "eight modeled states",
              "source": "2023 ACS 1-year PUMS person records; exact ages 18–35; PWGTP-weighted; scope=eight modeled states",
              "source_files": ";".join(f"psam_p{fips:02d}.csv" for fips in STATES.values())}
    age_rows = [{"age": age, **dict(zip(FIELDS, totals)), "move_rate": totals[1] / totals[0]}
                for age, totals in sorted(by_age.items())]
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in [("acs_young_adult_interstate_move_rate", [anchor]),
                       ("acs_young_adult_interstate_move_rate_by_state", by_state),
                       ("acs_young_adult_interstate_move_rate_by_age", age_rows),
                       ("pums_external_origin_competition", external)]:
        write_table(output_dir / f"{name}.csv", rows)
    return anchor


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path, help="Folder with all eight CSV person ZIPs (or extracted CSVs)")
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "abm_outputs_research_plan_v7")
    args = parser.parse_args()
    print(rebuild(args.input_dir, args.output_dir))
