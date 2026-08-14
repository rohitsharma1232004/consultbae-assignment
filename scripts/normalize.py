"""
Normalization helpers.
Every "messy real-world value" -> "one clean, comparable value" function lives here.
"""
import re
from datetime import datetime

import pandas as pd


def normalize_phone(raw):
    """
    '+919000000254' -> '9000000254'
    '09000000287'   -> '9000000287'
    '+91-9000000131'-> '9000000131'
    Returns None if we can't get a valid 10-digit Indian mobile number.
    """
    if pd.isna(raw):
        return None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) > 10:
        digits = digits[-10:]
    return digits if len(digits) == 10 else None


def normalize_email(raw):
    if pd.isna(raw):
        return None
    e = str(raw).strip().lower()
    return e if e else None


_CITY_MAP = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "gurgaon": "Gurugram",
    "gurugram": "Gurugram",
    "noida": "Noida",
    "new delhi": "New Delhi",
    "delhi": "Delhi",
    "delhi ncr": "Delhi NCR",
    "pune": "Pune",
}


def normalize_city(raw):
    if pd.isna(raw):
        return None
    key = str(raw).strip().lower()
    return _CITY_MAP.get(key, str(raw).strip().title())


def normalize_date(raw):
    """
    Applied Date mixes 4 formats. Ambiguous MM/DD-style values are
    assumed MM/DD/YYYY (documented assumption).
    """
    if pd.isna(raw):
        return None
    raw = str(raw).strip()
    formats = ["%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_ctc(raw):
    """CTC mixes lakhs ('2.4') and absolute rupees ('327287'). <100 = lakhs."""
    if pd.isna(raw):
        return None
    val = float(raw)
    return round(val * 100000, 2) if val < 100 else round(val, 2)


def normalize_rate(raw):
    """'1415/hr' -> (1415.0,'hourly'); '72k/month' -> (72000.0,'monthly')"""
    if pd.isna(raw):
        return None, None
    raw = str(raw).strip().lower()
    m = re.match(r"([\d.]+)(k)?/(\w+)", raw)
    if not m:
        return None, None
    amount = float(m.group(1))
    if m.group(2) == "k":
        amount *= 1000
    unit = "hourly" if "hr" in m.group(3) else "monthly" if "month" in m.group(3) else m.group(3)
    return amount, unit


def normalize_skills(raw):
    if pd.isna(raw):
        return []
    return [s.strip().title() for s in str(raw).split(",") if s.strip()]


def normalize_name(raw):
    if pd.isna(raw):
        return None
    return re.sub(r"\s+", " ", str(raw).strip())