"""
Main pipeline: reads the 3 raw CSVs -> cleans file-specific issues ->
normalizes fields -> resolves entities (dedup across files) -> writes
everything into MySQL (staging tables + people master + match_log).

Run with:  python scripts/run_pipeline.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import mysql.connector

from config import DB_CONFIG
from normalize import (
    normalize_phone, normalize_email, normalize_city, normalize_date,
    normalize_ctc, normalize_rate, normalize_skills, normalize_name,
)
from entity_resolution import resolve_entities

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
ISSUES_LOG = []


def log_issue(source, ref, issue_type, detail, action):
    ISSUES_LOG.append(
        {"source": source, "row_reference": ref, "issue_type": issue_type,
         "detail": detail, "action_taken": action}
    )


def load_naukri():
    df = pd.read_csv(os.path.join(RAW_DIR, "source1_naukri_applicants.csv"), dtype=str)
    df.columns = [c.strip() for c in df.columns]

    df["email_norm"] = df["Email"].apply(normalize_email)
    df["phone_norm"] = df["Phone"].apply(normalize_phone)
    df["city_norm"] = df["City"].apply(normalize_city)
    df["name_norm"] = df["Full Name"].apply(normalize_name)
    df["date_norm"] = df["Applied Date"].apply(normalize_date)
    df["ctc_norm"] = df["Current CTC"].apply(normalize_ctc)

    df["_name_len"] = df["name_norm"].str.len()
    df = df.sort_values("_name_len", ascending=False)
    dup_mask = df.duplicated(subset=["email_norm", "phone_norm"], keep="first")
    dropped = df[dup_mask]
    for _, r in dropped.iterrows():
        log_issue("source1_naukri", r["name_norm"], "intra_file_duplicate",
                   "same email+phone as another row (kept the fuller name instead)",
                   "dropped this row, kept the more complete-name duplicate")
    df = df[~dup_mask].drop(columns=["_name_len"]).sort_index()

    dup_phone_mask = df.duplicated(subset=["phone_norm"], keep="first")
    dropped2 = df[dup_phone_mask]
    for _, r in dropped2.iterrows():
        log_issue("source1_naukri", r["name_norm"], "intra_file_duplicate",
                   "same phone number, different email - looks like a repeat application",
                   "dropped this row, kept the first submission")
    df = df[~dup_phone_mask]

    log_issue("source1_naukri", "Phone column", "type_coercion_risk",
               "pandas silently reads Phone as int64 if not forced to string, "
               "stripping '+' and leading '0' formatting", "loaded with dtype=str explicitly")
    log_issue("source1_naukri", "Current CTC column", "unit_inconsistency",
               "CTC mixes lakhs (e.g. 2.4) and absolute rupees (e.g. 327287) in the same column",
               "any value < 100 treated as lakhs and multiplied by 100000")
    log_issue("source1_naukri", "Applied Date column", "format_inconsistency",
               "4 different date formats mixed in one column; some values like 07/03/2026 "
               "are genuinely ambiguous",
               "parsed with a 4-format cascade; ambiguous MM/DD-style values assumed MM/DD/YYYY")
    log_issue("source1_naukri", "Phone column", "format_inconsistency",
               "3 phone formats mixed: '+91XXXXXXXXXX', '0XXXXXXXXXX', plain 10-digit",
               "normalized to a plain 10-digit string by stripping all non-digits and country code")
    log_issue("source1_naukri", "City column", "format_inconsistency",
               "case and whitespace inconsistent; 'Bangalore'/'Bengaluru' and "
               "'Gurgaon'/'Gurugram' used as synonyms",
               "canonicalized via a lookup map to one spelling per city")

    return df.reset_index(drop=True)


def load_gig_workers():
    df = pd.read_csv(os.path.join(RAW_DIR, "source2_gig_workers.csv"), dtype=str)

    blank_mask = df.isnull().all(axis=1)
    if blank_mask.sum():
        log_issue("source2_gig_workers", f"row(s) {list(df[blank_mask].index)}",
                   "blank_row", "entire row is empty", "dropped")
    df = df[~blank_mask]

    shifted_mask = ~df["email_id"].str.contains("@", na=False)
    shifted_rows = df[shifted_mask]
    for _, r in shifted_rows.iterrows():
        log_issue("source2_gig_workers", f"row with worker_name field='{r['worker_name']}'",
                   "column_shift_corruption",
                   "row's values are shifted one column left; appears to be a corrupted "
                   "duplicate of an already-present correct row",
                   "dropped this malformed row (correct duplicate row was kept)")
    df = df[~shifted_mask]

    df["email_norm"] = df["email_id"].apply(normalize_email)
    df["name_norm"] = df["worker_name"].apply(normalize_name)
    df["city_norm"] = df["location"].apply(normalize_city)
    df[["rate_amount", "rate_unit"]] = df["rate"].apply(lambda x: pd.Series(normalize_rate(x)))

    log_issue("source2_gig_workers", "email_id column", "case_inconsistency",
               "some emails are fully uppercase", "lowercased for matching")
    log_issue("source2_gig_workers", "rate column", "unit_inconsistency",
               "rate mixes hourly ('1415/hr') and monthly ('72k/month') pay in one column",
               "parsed into separate rate_amount + rate_unit fields")

    return df.reset_index(drop=True)


def load_cbnexus():
    df = pd.read_csv(os.path.join(RAW_DIR, "source3_cbnexus_contacts.csv"), dtype=str)

    header_mask = df["Name"] == "Name"
    if header_mask.sum():
        log_issue("source3_cbnexus", f"row(s) {list(df[header_mask].index)}",
                   "embedded_header_row", "the column header row appears again as a data row",
                   "dropped")
    df = df[~header_mask]

    df["phone_norm"] = df["Phone Number"].apply(normalize_phone)
    df["city_norm"] = df["City"].apply(normalize_city)
    df["name_norm"] = df["Name"].apply(normalize_name)

    log_issue("source3_cbnexus", "Phone Number column", "format_inconsistency",
               "3 phone formats mixed", "normalized to a plain 10-digit string")
    log_issue("source3_cbnexus", "'Arjun Mehta' (2 rows)", "name_collision_different_people",
               "two rows named 'Arjun Mehta', same city, DIFFERENT phone numbers",
               "kept as two separate person records - name+city alone is not reliable "
               "enough evidence to merge people")

    return df.reset_index(drop=True)


def build_row_pool(naukri, gig, cbnexus):
    rows = []
    for i, r in naukri.iterrows():
        rows.append({"uid": ("naukri", i), "name": r["name_norm"],
                     "email_norm": r["email_norm"], "phone_norm": r["phone_norm"],
                     "city_norm": r["city_norm"]})
    for i, r in gig.iterrows():
        rows.append({"uid": ("gig", i), "name": r["name_norm"],
                     "email_norm": r["email_norm"], "phone_norm": None,
                     "city_norm": r["city_norm"]})
    for i, r in cbnexus.iterrows():
        rows.append({"uid": ("cbnexus", i), "name": r["name_norm"],
                     "email_norm": None, "phone_norm": r["phone_norm"],
                     "city_norm": r["city_norm"]})
    return rows


def pick_best_name(names):
    names = [n for n in names if n]
    return max(names, key=len) if names else None


def main():
    print("Loading and cleaning each source file...")
    naukri = load_naukri()
    gig = load_gig_workers()
    cbnexus = load_cbnexus()
    print(f"  naukri: {len(naukri)} clean rows, gig: {len(gig)} clean rows, "
          f"cbnexus: {len(cbnexus)} clean rows")

    print("Resolving entities across files...")
    rows = build_row_pool(naukri, gig, cbnexus)
    groups, match_notes = resolve_entities(rows)
    print(f"  {len(rows)} total rows -> {len(groups)} unique people")

    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("Inserting staging tables...")
    naukri_id_map, gig_id_map, cbnexus_id_map = {}, {}, {}

    for i, r in naukri.iterrows():
        cur.execute(
            "INSERT INTO staging_naukri (full_name,email,phone,city,experience_years,"
            "current_ctc,applied_date,skills) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (r["name_norm"], r["email_norm"], r["phone_norm"], r["city_norm"],
             float(r["Experience (Years)"]), r["ctc_norm"], r["date_norm"], r["Skills"])
        )
        naukri_id_map[i] = cur.lastrowid

    for i, r in gig.iterrows():
        cur.execute(
            "INSERT INTO staging_gig_workers (email,worker_name,rate_amount,rate_unit,"
            "location,status,skill_tags) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (r["email_norm"], r["name_norm"], r["rate_amount"], r["rate_unit"],
             r["city_norm"], r["status"], r["skill_tags"])
        )
        gig_id_map[i] = cur.lastrowid

    for i, r in cbnexus.iterrows():
        cur.execute(
            "INSERT INTO staging_cbnexus (name,phone,city,verified,projects_completed) "
            "VALUES (%s,%s,%s,%s,%s)",
            (r["name_norm"], r["phone_norm"], r["city_norm"], r["Verified"],
             int(r["Projects Completed"]))
        )
        cbnexus_id_map[i] = cur.lastrowid

    conn.commit()

    print("Building master people table + match_log...")
    by_uid = {r["uid"]: r for r in rows}
    src_map = {"naukri": naukri_id_map, "gig": gig_id_map, "cbnexus": cbnexus_id_map}
    src_table = {"naukri": "staging_naukri", "gig": "staging_gig_workers", "cbnexus": "staging_cbnexus"}

    people_created = 0
    for group in groups:
        names = [by_uid[u]["name"] for u in group]
        emails = [by_uid[u]["email_norm"] for u in group if by_uid[u]["email_norm"]]
        phones = [by_uid[u]["phone_norm"] for u in group if by_uid[u]["phone_norm"]]
        cities = [by_uid[u]["city_norm"] for u in group if by_uid[u]["city_norm"]]

        cur.execute(
            "INSERT INTO people (full_name,email,phone,city) VALUES (%s,%s,%s,%s)",
            (pick_best_name(names), emails[0] if emails else None,
             phones[0] if phones else None, cities[0] if cities else None)
        )
        person_id = cur.lastrowid
        people_created += 1

        for uid in group:
            source, local_idx = uid
            row_id = src_map[source][local_idx]
            cur.execute(
                f"UPDATE {src_table[source]} SET person_id=%s WHERE row_id=%s",
                (person_id, row_id)
            )
            method, confidence, note = match_notes.get(uid, ("first_seen", 100.0, "first row for this person"))
            cur.execute(
                "INSERT INTO match_log (person_id,source_table,source_row_id,match_method,"
                "match_confidence,notes) VALUES (%s,%s,%s,%s,%s,%s)",
                (person_id, src_table[source], row_id, method, confidence, note)
            )

    conn.commit()
    cur.close()
    conn.close()

    print(f"Done. {people_created} unique people created from "
          f"{len(naukri)+len(gig)+len(cbnexus)} source rows.")

    write_issues_report()


def write_issues_report():
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "data_issues_report.md")
    with open(out_path, "w") as f:
        f.write("# Data Issues Report\n\n")
        f.write(f"Total issues found and handled: {len(ISSUES_LOG)}\n\n")
        f.write("| Source | Reference | Issue Type | Detail | Action Taken |\n")
        f.write("|---|---|---|---|---|\n")
        for i in ISSUES_LOG:
            f.write(f"| {i['source']} | {i['row_reference']} | {i['issue_type']} | "
                     f"{i['detail']} | {i['action_taken']} |\n")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()