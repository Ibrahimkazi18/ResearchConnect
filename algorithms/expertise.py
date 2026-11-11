"""
expertise.py
------------
Keyword matching with Python sets and Jaccard similarity.

    J(A, B) = |A intersection B| / |A union B| x 100

A = the keywords the user typed.
B = the keywords linked to one faculty member.

IMPORTANT: a high score only means two keyword lists look alike. It is NOT
evidence that two people have worked together. Real collaboration is shown
only on the Collaboration Network page, from shared papers.
"""
from algorithms.data_manager import split_keywords


def jaccard_percent(set_a, set_b):
    """Jaccard similarity as a percentage (0 to 100)."""
    union = set_a | set_b
    if not union:                       # two empty sets: avoid dividing by zero
        return 0.0
    return len(set_a & set_b) / len(union) * 100


def build_profiles(ds):
    """One keyword set per faculty member.
    B = listed expertise (faculty.csv)  UNION  keywords of their own papers (papers.csv).
    Nothing is invented: both parts come straight from the CSV files."""
    profiles = []
    for fac in ds.faculty:
        keywords = {k.lower() for k in fac["expertise_list"]}
        keywords |= {k.lower() for k in fac["paper_keywords"]}
        profiles.append({"faculty": fac, "keywords": keywords})
    return profiles


def parse_query(text):
    """'AI, IoT; robotics' -> {'ai', 'iot', 'robotics'}"""
    return {k.lower() for k in split_keywords(text, semicolon_first=False)}


def compare_faculty(ds, id_a, id_b):
    """Compare normalized profiles; raise ValueError for unknown faculty IDs.

    Display labels follow normalized keyword order. Self-comparison is allowed;
    the existing Jaccard helper defines two empty profiles as 0%.
    """
    if id_a not in ds.faculty_by_id or id_b not in ds.faculty_by_id:
        raise ValueError("Select two known faculty members.")
    profiles = {p["faculty"]["faculty_id"]: p["keywords"] for p in build_profiles(ds)}
    a, b = profiles[id_a], profiles[id_b]

    def labels(keywords):
        return [ds.keyword_labels.get(k, k) for k in sorted(keywords)]

    def person(fid):
        faculty = ds.faculty_by_id[fid]
        return {"faculty_id": fid,
                "name": "Not listed" if faculty["name"] == "Name not listed" else faculty["name"] or "Not listed",
                "department": faculty["department"] or "Not listed"}

    return {"faculty_a": person(id_a), "faculty_b": person(id_b),
            "keywords_a": labels(a), "keywords_b": labels(b),
            "shared": labels(a & b), "unique_a": labels(a - b),
            "unique_b": labels(b - a), "score": jaccard_percent(a, b),
            "self_comparison": id_a == id_b}


def find_matches(query_set, profiles, labels):
    """Return faculty sharing at least one keyword, best match first.
    `labels` maps a lowercase keyword to its nicely written form."""
    results = []
    for profile in profiles:
        common = query_set & profile["keywords"]
        if not common:
            continue
        results.append({
            "faculty": profile["faculty"],
            "score": round(jaccard_percent(query_set, profile["keywords"]), 1),
            "matching": sorted(labels.get(k, k) for k in common),
            "shared": len(common),
            "union": len(query_set | profile["keywords"]),
        })
    results.sort(key=lambda r: (-r["score"], r["faculty"]["name"].lower()))
    return results
