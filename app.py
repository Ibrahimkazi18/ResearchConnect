"""
app.py - ResearchConnect: VJTI Faculty Research Collaboration and Expertise Mapper

This file only connects web pages (routes) to the logic in the algorithms/ folder:
    data_manager.py  -> reads and cleans the CSV files
    expertise.py     -> Jaccard keyword matching
    collaboration.py -> NetworkX co-authorship graph
    analytics.py     -> counts and chart data

Run it with:   python app.py      then open  http://127.0.0.1:5000
"""
from flask import Flask, abort, render_template, request, url_for

from algorithms import analytics, collaboration, expertise
from algorithms.data_manager import Dataset

app = Flask(__name__)


def publication_table_context(ds, q="", year="", dept=""):
    """Everything the shared publications table needs. q / year / dept only set the
    starting values of the controls (so a link like /publications?year=2023 works)."""
    years = ds.years()
    departments = ds.publication_departments()
    return {
        "pub_rows": ds.publication_rows(),
        "pub_years": years,
        "pub_departments": departments,
        "init_q": q,
        "init_year": year if year in [str(y) for y in years] else "",
        "init_dept": dept if dept in departments else "",
    }


# ---------- Dashboard ----------
@app.route("/")
def dashboard():
    ds = Dataset()
    graph = collaboration.build_graph(ds)
    return render_template(
        "index.html",
        stats=analytics.dashboard_stats(ds, graph),
        year_chart=analytics.publications_by_year(ds),
        dept_chart=analytics.publications_by_department(ds),
        keyword_chart=analytics.top_keywords(ds, 10),
        year_missing=analytics.data_coverage(ds)["papers_without_year"],
        recent=ds.recent_papers(5),
        warnings=ds.warnings,
        **publication_table_context(ds),
    )


# ---------- Faculty directory ----------
@app.route("/faculty")
def faculty_list():
    ds = Dataset()
    q = request.args.get("q", "").strip()
    dept = request.args.get("department", "").strip()

    people = ds.faculty
    if q:
        people = [f for f in people if q.lower() in f["name"].lower()]
    if dept:
        people = [f for f in people if f["department"] == dept]

    return render_template("faculty.html", people=people, q=q, dept=dept,
                           departments=ds.departments(), total=len(ds.faculty))


@app.route("/faculty/<faculty_id>")
def faculty_detail(faculty_id):
    ds = Dataset()
    person = ds.faculty_by_id.get(faculty_id)
    if person is None:
        abort(404)
    graph = collaboration.build_graph(ds)
    return render_template("faculty_detail.html", person=person,
                           collaborators=collaboration.collaborators_of(graph, ds, faculty_id))


# ---------- Publications ----------
@app.route("/publications")
def publications():
    ds = Dataset()
    q = request.args.get("q", "").strip()
    year = request.args.get("year", "").strip()
    dept = request.args.get("department", "").strip()
    if not q:                                   # older links used ?keyword=...
        q = request.args.get("keyword", "").strip()
    return render_template("publications.html", **publication_table_context(ds, q, year, dept))


# ---------- Expertise Finder ----------
@app.route("/expertise")
def expertise_finder():
    ds = Dataset()
    q = request.args.get("q", "").strip()
    query_set = expertise.parse_query(q)

    results, unknown = [], []
    if query_set:
        results = expertise.find_matches(query_set, expertise.build_profiles(ds), ds.keyword_labels)
        unknown = sorted(k for k in query_set if k not in ds.keyword_labels)

    return render_template("expertise.html", q=q, searched=bool(query_set), results=results,
                           unknown=unknown, keywords=ds.keyword_options())


# ---------- Collaboration network ----------
@app.route("/network")
def network():
    ds = Dataset()
    graph = collaboration.build_graph(ds)
    plot = collaboration.network_for_plot(graph, ds)
    for node in plot["nodes"]:                        # build profile links with url_for
        node["profile"] = url_for("faculty_detail", faculty_id=node["id"])
    return render_template("network.html", plot=plot, stats=collaboration.network_stats(graph, ds))


# ---------- Analytics ----------
@app.route("/analytics")
def analytics_page():
    ds = Dataset()
    graph = collaboration.build_graph(ds)
    return render_template(
        "analytics.html",
        year_chart=analytics.publications_by_year(ds),
        dept_chart=analytics.publications_by_department(ds),
        keyword_chart=analytics.top_keywords(ds, 15),
        faculty_chart=analytics.faculty_paper_counts(ds),
        collab=collaboration.network_stats(graph, ds),
        coverage=analytics.data_coverage(ds),
        total_papers=len(ds.papers),
        total_faculty=len(ds.faculty),
    )


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
