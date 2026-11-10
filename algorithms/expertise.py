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
