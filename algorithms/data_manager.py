"""
data_manager.py
---------------
Stage 1 of ResearchConnect: load and clean the three CSV files.

faculty.csv    : faculty_id, name, department, expertise, profile_url, data_status
papers.csv     : paper_id, title, year, venue, doi, keywords, source_url, data_status
authorship.csv : paper_id, faculty_id, author_order, source_url, data_status

Everything else in the project (search, charts, network) reads its data from the
`Dataset` object defined here, so the CSV rules live in exactly one place.
Nothing in this file ever writes to a CSV.
"""
import os
import re
from collections import Counter

import pandas as pd

# The CSV files sit next to app.py (the project root).
# RC_DATA_DIR is only an optional override, handy for testing with other files.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("RC_DATA_DIR", BASE_DIR)

FACULTY_COLUMNS = ["faculty_id", "name", "department", "expertise", "profile_url", "data_status"]
PAPER_COLUMNS = ["paper_id", "title", "year", "venue", "doi", "keywords", "source_url", "data_status"]
AUTHORSHIP_COLUMNS = ["paper_id", "faculty_id", "author_order", "source_url", "data_status"]


# ---------- small helper functions ----------

def read_csv_safe(filename, columns):
    """Read a CSV as text. A missing, empty or broken file gives an empty table
    with the right columns, so the website shows empty states instead of crashing."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return pd.DataFrame(columns=columns)
    try:
        # dtype=str + keep_default_na=False: blank cells stay "" and never become NaN
        df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame(columns=columns)
    df.columns = [str(c).strip() for c in df.columns]
    for col in columns:                      # a missing column becomes a blank column
        if col not in df.columns:
            df[col] = ""
    df = df[columns].copy()
    for col in columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def clean_year(value):
    """'2023' or '2023.0' -> 2023. Blank or invalid -> None."""
    try:
        year = int(float(value))
    except (TypeError, ValueError):
        return None
    return year if 1900 <= year <= 2100 else None


def clean_int(value, default=9999):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def split_keywords(text, semicolon_first=True):
    """'AI; IoT; Robotics' -> ['AI', 'IoT', 'Robotics'] (no blanks, no repeats).

    papers.csv separates keywords with semicolons. If a cell contains a semicolon,
    ONLY semicolons (and |) split it, so a phrase such as 'Learning, Deep' stays whole.
    A cell with no semicolon is split on commas too. The search box on the Expertise
    Finder passes semicolon_first=False because people type commas there."""
    text = text or ""
    pattern = r"[;|]" if (semicolon_first and ";" in text) else r"[;,|]"
    seen, result = set(), []
    for part in re.split(pattern, text):
        label = " ".join(part.split())
        if label and label.lower() not in seen:
            seen.add(label.lower())
            result.append(label)
    return result


def safe_url(url):
    """Only allow web links, so a bad cell can never become a javascript: link."""
    url = (url or "").strip()
    return url if url.lower().startswith(("http://", "https://")) else ""


def doi_to_url(doi):
    doi = (doi or "").strip()
    if not doi:
        return ""
    return safe_url(doi) or "https://doi.org/" + doi


# ---------- the Dataset ----------

class Dataset:
    """Holds clean, linked data. Created fresh on every request, so edits to the
    CSV files show up after a page refresh (the files are tiny, so this is fast)."""

    def __init__(self):
        self.warnings = []                    # data-quality notes shown on the dashboard
        self._load_faculty()
        self._load_papers()
        self._link_authorship()
        self._build_keyword_index()

    # -- loading --
    def _load_faculty(self):
        self.faculty = []
        self.faculty_by_id = {}
        for row in read_csv_safe("faculty.csv", FACULTY_COLUMNS).to_dict("records"):
            fid = row["faculty_id"]
            if not fid or fid in self.faculty_by_id:
                continue
            row["name"] = row["name"] or "Name not listed"
            row["profile_url"] = safe_url(row["profile_url"])
            row["expertise_list"] = split_keywords(row["expertise"])
            self.faculty.append(row)
            self.faculty_by_id[fid] = row

    def _load_papers(self):
        self.papers = []
        self.papers_by_id = {}
        for row in read_csv_safe("papers.csv", PAPER_COLUMNS).to_dict("records"):
            pid = row["paper_id"]
            if not pid or pid in self.papers_by_id:
                continue
            row["title"] = row["title"] or "Title not listed"
            row["year_num"] = clean_year(row["year"])
            row["keyword_list"] = split_keywords(row["keywords"])
            row["doi_link"] = doi_to_url(row["doi"])
            row["source_url"] = safe_url(row["source_url"])
            row["link"] = row["doi_link"] or row["source_url"]   # best link for the title
            self.papers.append(row)
            self.papers_by_id[pid] = row

    def _link_authorship(self):
        """authorship.csv connects papers to faculty. Only rows whose paper_id AND
        faculty_id exist in the other two files are used."""
        self.paper_authors = {}                              # paper_id -> [faculty_id, ...]
        faculty_papers = {fid: [] for fid in self.faculty_by_id}
        rows = read_csv_safe("authorship.csv", AUTHORSHIP_COLUMNS).to_dict("records")
        rows.sort(key=lambda r: clean_int(r["author_order"]))
        unlinked = 0
        for row in rows:
            pid, fid = row["paper_id"], row["faculty_id"]
            if pid not in self.papers_by_id or fid not in self.faculty_by_id:
                unlinked += 1
                continue
            authors = self.paper_authors.setdefault(pid, [])
            if fid not in authors:                           # ignore duplicate rows
                authors.append(fid)
                faculty_papers[fid].append(pid)
        if unlinked:
            self.warnings.append(
                f"{unlinked} authorship row(s) point to a paper or faculty ID that does not "
                "exist in papers.csv or faculty.csv, so they were skipped.")

        # attach convenient lists used by the templates
        for paper in self.papers:
            paper["authors"] = [self.faculty_by_id[f] for f in self.paper_authors.get(paper["paper_id"], [])]
        for fac in self.faculty:
            papers = [self.papers_by_id[p] for p in faculty_papers[fac["faculty_id"]]]
            papers.sort(key=lambda p: p["year_num"] or 0, reverse=True)
            fac["papers"] = papers
            fac["paper_count"] = len(papers)
            kws, seen = [], set()                            # keywords taken from their papers
            for p in papers:
                for k in p["keyword_list"]:
                    if k.lower() not in seen:
                        seen.add(k.lower())
                        kws.append(k)
            fac["paper_keywords"] = kws

    def _build_keyword_index(self):
        self.keyword_labels = {}               # 'machine learning' -> 'Machine Learning'
        self.keyword_paper_counts = Counter()  # how many papers use each keyword
        for p in self.papers:
            for k in p["keyword_list"]:
                self.keyword_labels.setdefault(k.lower(), k)
                self.keyword_paper_counts[k.lower()] += 1
        for f in self.faculty:
            for k in f["expertise_list"]:
                self.keyword_labels.setdefault(k.lower(), k)

    # -- helpers used by routes --
    def departments(self):
        return sorted({f["department"] for f in self.faculty if f["department"]})

    def years(self):
        return sorted({p["year_num"] for p in self.papers if p["year_num"]}, reverse=True)

    def keyword_options(self):
        """[(normalised, label)] sorted A-Z, for dropdowns and suggestion chips."""
        return sorted(self.keyword_labels.items(), key=lambda kv: kv[1].lower())

    def recent_papers(self, n=5):
        return sorted(self.papers, key=lambda p: p["year_num"] or 0, reverse=True)[:n]

    # -- publications table --
    def publication_rows(self):
        """One row per paper for the publications table, newest year first.
        Each row carries the linked faculty, their departments (from faculty.csv, via
        authorship.csv) and one lowercase text blob that the live search looks inside."""
        by_title = sorted(self.papers, key=lambda p: p["title"].lower())
        newest_first = sorted(by_title, key=lambda p: p["year_num"] or 0, reverse=True)
        rows = []
        for paper in newest_first:
            departments = []
            for author in paper["authors"]:
                if author["department"] and author["department"] not in departments:
                    departments.append(author["department"])
            text = " ".join([paper["title"], " ".join(paper["keyword_list"]), paper["venue"],
                             " ".join(a["name"] for a in paper["authors"])])
            rows.append({
                "paper": paper,
                "authors": paper["authors"],
                "departments": departments,
                "search_text": " ".join(text.lower().split()),
            })
        return rows

    def publication_departments(self):
        """Departments that actually have at least one paper (used by the dropdown)."""
        return sorted({d for row in self.publication_rows() for d in row["departments"]})
