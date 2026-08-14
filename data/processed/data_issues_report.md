# Data Issues Report

Total issues found and handled: 14

| Source | Reference | Issue Type | Detail | Action Taken |
|---|---|---|---|---|
| source1_naukri | R. Verma | intra_file_duplicate | same email+phone as another row (kept the fuller name instead) | dropped this row, kept the more complete-name duplicate |
| source1_naukri | Nikhil Chopra | intra_file_duplicate | same phone number, different email - looks like a repeat application | dropped this row, kept the first submission |
| source1_naukri | Phone column | type_coercion_risk | pandas silently reads Phone as int64 if not forced to string, stripping '+' and leading '0' formatting | loaded with dtype=str explicitly |
| source1_naukri | Current CTC column | unit_inconsistency | CTC mixes lakhs (e.g. 2.4) and absolute rupees (e.g. 327287) in the same column | any value < 100 treated as lakhs and multiplied by 100000 |
| source1_naukri | Applied Date column | format_inconsistency | 4 different date formats mixed in one column; some values like 07/03/2026 are genuinely ambiguous | parsed with a 4-format cascade; ambiguous MM/DD-style values assumed MM/DD/YYYY |
| source1_naukri | Phone column | format_inconsistency | 3 phone formats mixed: '+91XXXXXXXXXX', '0XXXXXXXXXX', plain 10-digit | normalized to a plain 10-digit string by stripping all non-digits and country code |
| source1_naukri | City column | format_inconsistency | case and whitespace inconsistent; 'Bangalore'/'Bengaluru' and 'Gurgaon'/'Gurugram' used as synonyms | canonicalized via a lookup map to one spelling per city |
| source2_gig_workers | row(s) [10] | blank_row | entire row is empty | dropped |
| source2_gig_workers | row with worker_name field='ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG' | column_shift_corruption | row's values are shifted one column left; appears to be a corrupted duplicate of an already-present correct row | dropped this malformed row (correct duplicate row was kept) |
| source2_gig_workers | email_id column | case_inconsistency | some emails are fully uppercase | lowercased for matching |
| source2_gig_workers | rate column | unit_inconsistency | rate mixes hourly ('1415/hr') and monthly ('72k/month') pay in one column | parsed into separate rate_amount + rate_unit fields |
| source3_cbnexus | row(s) [14] | embedded_header_row | the column header row appears again as a data row | dropped |
| source3_cbnexus | Phone Number column | format_inconsistency | 3 phone formats mixed | normalized to a plain 10-digit string |
| source3_cbnexus | 'Arjun Mehta' (2 rows) | name_collision_different_people | two rows named 'Arjun Mehta', same city, DIFFERENT phone numbers | kept as two separate person records - name+city alone is not reliable enough evidence to merge people |
