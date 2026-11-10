# ResearchConnect: project context

VJTI Faculty Research Collaboration and Expertise Mapper. A college mini-project (Flask web app).
Read this file first. It tells you what exists, how it fits together and what the rules are.

## 1. What the app does
- Faculty directory, publications table, expertise finder, collaboration network, analytics dashboard.
- No AI, ML, LLMs or recommendation APIs. All logic is plain Python (sets, Jaccard similarity, NetworkX).
- Data comes only from three CSV files in the project root. There is no database.

## 2. Tech stack
Python, Flask, Pandas, NetworkX, HTML/CSS, Bootstrap 5, JavaScript, Plotly.js (loaded from a CDN, not the Python `plotly` package).

## 3. Run it
    pip install -r requirements.txt
    python app.py        # open http://127.0.0.1:5000

## 4. Folder structure
    app.py                      routes only (thin: read request, call a function, render template)
    faculty.csv, papers.csv, authorship.csv    the real data (project root)
    data/                       OLD copy of the data. Not used. Do not edit.
    algorithms/
        data_manager.py         loads and cleans the CSVs, builds the Dataset object
        expertise.py            keyword sets and Jaccard similarity
        collaboration.py        NetworkX co-authorship graph
        analytics.py            counts and chart data
    templates/                  Jinja pages (base.html has the top nav; _macros.html and _publications_table.html are shared)
    static/css/style.css        navy and violet theme
    static/js/                  charts.js (bar charts), network.js (graph), publications.js (table search/filters)
    static/images/              logo.png and background.png (do not overwrite)
    PROJECT_GUIDE.md            module explanations and viva questions

## 5. Data files (exact columns)
- faculty.csv: faculty_id, name, department, expertise, profile_url, data_status
- papers.csv: paper_id, title, year, venue, doi, keywords, source_url, data_status
- authorship.csv: paper_id, faculty_id, author_order, source_url, data_status
- `keywords` in papers.csv are separated by semicolons.
- Current data: 12 faculty, 19 papers, 19 authorship rows. `expertise` is blank for all faculty, and each paper has only one VJTI faculty author, so the collaboration graph has 0 edges. This is correct. Do not "fix" it.

## 6. Routes
| Route | Page |
|---|---|
| `/` | Dashboard: hero, stat cards, charts, publications table |
| `/faculty` and `/faculty/<faculty_id>` | Directory and profile |
| `/publications` | Searchable publications table (also accepts `?q=`, `?year=`, `?department=`) |
| `/expertise?q=...` | Keyword matching with Jaccard % |
| `/network` | Collaboration graph |
| `/analytics` | Charts and collaboration stats |

## 7. Key functions
- `data_manager.py`: `Dataset` (faculty, papers, paper_authors, keyword_labels, warnings; methods `departments()`, `years()`, `keyword_options()`, `recent_papers()`, `publication_rows()`, `publication_departments()`), `read_csv_safe`, `clean_year`, `split_keywords`, `safe_url`, `doi_to_url`.
- `expertise.py`: `jaccard_percent`, `build_profiles`, `parse_query`, `find_matches`.
- `collaboration.py`: `build_graph`, `network_stats`, `collaborators_of`, `network_for_plot`.
- `analytics.py`: `publications_by_year`, `publications_by_department`, `top_keywords`, `faculty_paper_counts`, `dashboard_stats`, `data_coverage`.

## 8. How the main pieces work
- Jaccard: `J(A,B) = |A ∩ B| / |A ∪ B| x 100`. A = typed keywords, B = one faculty member's keywords (listed expertise plus keywords of their own papers). A high score is NOT proof of collaboration.
- Network: one node per faculty member. An edge exists only when two faculty are listed on the SAME paper in authorship.csv. Edge weight = number of shared papers. Keywords never create edges.
- Department of a paper = department of its linked faculty (via authorship.csv and faculty.csv).
- Charts: Python returns `{labels, values, orientation, ...}`, `charts.js` draws them. Counts are always calculated from the CSVs, never typed in.

## 9. Rules for contributors
1. Read data only through `Dataset`. Never call `pd.read_csv` in routes or templates.
2. Put logic in `algorithms/`. Keep `app.py` thin.
3. Return plain dicts or lists. Templates only display them.
4. Handle blank values with an empty state and a "Not listed" label.
5. Never invent faculty, papers, DOIs, expertise or collaborations.
6. Do not write to the CSV files or overwrite `static/images/logo.png` and `background.png`.
7. Add a `pytest` test for each new function, using small throwaway CSVs in `tests/`.
8. One branch per task, then open a pull request.

## 10. Status
Done: all six pages, upgraded stat cards, three dashboard charts, interactive publications table with live search and year/department filters, hero section.
Tested with throwaway CSVs (same columns). Not yet tested against the real CSV rows in a browser.

## 11. Next tasks (backend)
Tests; data quality report; paper detail page; related papers; faculty compare; department pages; keyword trends; keyword co-occurrence; network filters; centrality table; CSV export; data caching. See ResearchConnect_Collaborator_Guide.pdf for details.
