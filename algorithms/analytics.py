"""
analytics.py
------------
Turns the Dataset into numbers and chart data. Every value is counted from the
CSV files; nothing is typed in by hand. Charts are returned as small dicts
({"labels": [...], "values": [...]}) and drawn in the browser by Plotly.js.
An empty chart simply has an empty "labels" list, and the page shows a message.
"""
from collections import Counter

import pandas as pd


def _chart(labels, values, orientation="v", x_title="", y_title="", name_label="", value_label=""):
    """The small dict that charts.js draws.
    name_label / value_label are the words shown in the hover tooltip."""
    return {"labels": list(labels), "values": [int(v) for v in values],
            "orientation": orientation, "x_title": x_title, "y_title": y_title,
            "name_label": name_label, "value_label": value_label}


def _from_counter(counter, limit=None, orientation="h", x_title="", y_title="", name_label="", value_label=""):
    ordered = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    if limit:
        ordered = ordered[:limit]
    return _chart([k for k, _ in ordered], [v for _, v in ordered], orientation,
                  x_title, y_title, name_label, value_label)


def publications_by_year(ds):
    years = pd.Series([p["year_num"] for p in ds.papers if p["year_num"]], dtype="int64")
    counts = years.value_counts().sort_index()          # pandas does the counting
    return _chart([str(y) for y in counts.index], counts.values, "v",
                  "Publication year", "Number of publications", "Year", "Publications")


def keyword_trends(ds):
    """Count papers per normalized keyword and valid year, in sorted order.

    Each keyword counts at most once per paper. Missing/invalid years are
    already None in Dataset; their exclusion count remains available through
    data_coverage(ds)["papers_without_year"], outside this nested contract.
    """
    observations = [
        (paper["year_num"], keyword)
        for paper in ds.papers if paper["year_num"] is not None
        for keyword in sorted({k.lower() for k in paper["keyword_list"]})
    ]
    if not observations:
        return {}
    frame = pd.DataFrame(observations, columns=["year", "keyword"])
    counts = frame.groupby(["keyword", "year"], sort=True).size()
    trends = {}
    for (keyword, year), count in counts.items():
        trends.setdefault(keyword, {})[int(year)] = int(count)
    return trends


def publications_by_department(ds):
    """A paper counts once for each department that has a linked author on it."""
    counter = Counter()
    for paper in ds.papers:
        for dept in {a["department"] for a in paper["authors"] if a["department"]}:
            counter[dept] += 1
    return _from_counter(counter, x_title="Number of publications",
                         name_label="Department", value_label="Publications")


def top_keywords(ds, limit=10):
    counter = Counter({ds.keyword_labels[k]: c for k, c in ds.keyword_paper_counts.items()})
    return _from_counter(counter, limit=limit, x_title="Number of papers using the keyword",
                         name_label="Keyword", value_label="Papers")


def faculty_paper_counts(ds):
    counter = Counter({f["name"]: f["paper_count"] for f in ds.faculty})
    return _from_counter(counter, x_title="Number of papers",
                         name_label="Faculty", value_label="Papers") if counter else _chart([], [])


def dashboard_stats(ds, graph):
    return {
        "faculty": len(ds.faculty),
        "papers": len(ds.papers),
        "links": graph.number_of_edges(),
        "keywords": len(ds.keyword_labels),
    }


def data_coverage(ds):
    """How complete the CSV data is. Shown on the Analytics page."""
    return {
        "papers_without_year": sum(1 for p in ds.papers if not p["year_num"]),
        "papers_without_keywords": sum(1 for p in ds.papers if not p["keyword_list"]),
        "papers_without_doi": sum(1 for p in ds.papers if not p["doi"]),
        "faculty_without_department": sum(1 for f in ds.faculty if not f["department"]),
        "faculty_without_expertise": sum(1 for f in ds.faculty if not f["expertise_list"]),
    }
