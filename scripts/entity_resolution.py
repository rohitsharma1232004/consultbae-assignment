"""
Entity resolution: decide which rows across the 3 files belong to the
SAME real person, using Union-Find (connected components).

File1 (naukri) has BOTH email and phone -> it's the "bridge" table.
File2 (gig_workers) only has email. File3 (cbnexus) only has phone.
There is no direct key between File2 and File3 - they only link
THROUGH a File1 row. So: union any two rows that share a normalized
email OR phone. Rows still alone after that get a fuzzy name+city
pass; genuinely ambiguous cases (multiple equally-good candidates)
are NOT auto-merged - a silently wrong merge is worse than two
records for one person.
"""
from rapidfuzz import fuzz


class UnionFind:
    def __init__(self, ids):
        self.parent = {i: i for i in ids}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb

    def groups(self):
        out = {}
        for x in self.parent:
            out.setdefault(self.find(x), []).append(x)
        return list(out.values())


def resolve_entities(rows, fuzzy_threshold=88):
    """
    rows: list of dicts with keys: uid, name, email_norm, phone_norm, city_norm
    Returns: (groups, match_notes)
    """
    uids = [r["uid"] for r in rows]
    uf = UnionFind(uids)
    by_uid = {r["uid"]: r for r in rows}
    match_notes = {}

    email_map = {}
    for r in rows:
        if r["email_norm"]:
            email_map.setdefault(r["email_norm"], []).append(r["uid"])
    for uid_list in email_map.values():
        for other in uid_list[1:]:
            uf.union(uid_list[0], other)
            match_notes[other] = ("email_exact", 100.0, f"shares email with {uid_list[0]}")

    phone_map = {}
    for r in rows:
        if r["phone_norm"]:
            phone_map.setdefault(r["phone_norm"], []).append(r["uid"])
    for uid_list in phone_map.values():
        for other in uid_list[1:]:
            uf.union(uid_list[0], other)
            match_notes[other] = ("phone_exact", 100.0, f"shares phone with {uid_list[0]}")

    groups_after_exact = uf.groups()
    singleton_uids = [g[0] for g in groups_after_exact if len(g) == 1]

    for i, uid_a in enumerate(singleton_uids):
        ra = by_uid[uid_a]
        if not ra["name"] or not ra["city_norm"]:
            continue
        candidates = []
        for uid_b in singleton_uids[i + 1:]:
            rb = by_uid[uid_b]
            if not rb["name"] or ra["city_norm"] != rb["city_norm"]:
                continue
            score = fuzz.token_sort_ratio(ra["name"].lower(), rb["name"].lower())
            if score >= fuzzy_threshold:
                candidates.append((uid_b, score))

        if len(candidates) == 1:
            uid_b, score = candidates[0]
            uf.union(uid_a, uid_b)
            match_notes[uid_b] = (
                "name_city_fuzzy", float(score),
                f"fuzzy name+city match with {uid_a} ('{ra['name']}' vs '{by_uid[uid_b]['name']}')"
            )
        elif len(candidates) > 1:
            for uid_b, score in candidates:
                match_notes[uid_a] = (
                    "ambiguous_unmerged", float(score),
                    "multiple name+city candidates found, not auto-merged - manual review needed"
                )
                match_notes[uid_b] = match_notes[uid_a]

    return uf.groups(), match_notes