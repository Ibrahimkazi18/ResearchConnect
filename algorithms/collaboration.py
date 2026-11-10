"""
collaboration.py
----------------
Builds the verified co-authorship network with NetworkX.

  node   = one VJTI faculty member (from faculty.csv)
  edge   = two faculty are listed as authors of the SAME paper (authorship.csv)
  weight = how many papers they share

An edge is NEVER created from shared keywords. Only shared papers count.
If every paper has just one VJTI author, the graph correctly has zero edges.
"""
import itertools

import networkx as nx


def build_graph(ds):
    graph = nx.Graph()
    for fac in ds.faculty:
        graph.add_node(fac["faculty_id"])

    # For each paper, pair up every two VJTI authors of that paper.
    for paper_id, author_ids in ds.paper_authors.items():
        for a, b in itertools.combinations(sorted(set(author_ids)), 2):
            if graph.has_edge(a, b):
                graph[a][b]["weight"] += 1
                graph[a][b]["papers"].append(paper_id)
            else:
                graph.add_edge(a, b, weight=1, papers=[paper_id])
    return graph


def network_stats(graph, ds):
    n, m = graph.number_of_nodes(), graph.number_of_edges()
    connected = sum(1 for node in graph if graph.degree(node) > 0)
    multi_author = sum(1 for ids in ds.paper_authors.values() if len(ids) > 1)
    pairs = []
    for a, b, data in graph.edges(data=True):
        pairs.append({
            "a": ds.faculty_by_id[a]["name"],
            "b": ds.faculty_by_id[b]["name"],
            "shared": data["weight"],
            "titles": [ds.papers_by_id[p]["title"] for p in data["papers"]],
        })
    pairs.sort(key=lambda p: (-p["shared"], p["a"]))
    return {
        "faculty": n,
        "links": m,
        "collaborating": connected,
        "isolated": n - connected,
        "multi_author_papers": multi_author,
        "density": round(nx.density(graph), 3) if n > 1 else 0,
        "top_pairs": pairs[:10],
    }


def collaborators_of(graph, ds, faculty_id):
    """[(faculty dict, shared paper count)] for one person."""
    if faculty_id not in graph:
        return []
    found = [(ds.faculty_by_id[other], graph[faculty_id][other]["weight"]) for other in graph[faculty_id]]
    found.sort(key=lambda item: (-item[1], item[0]["name"]))
    return found


def network_for_plot(graph, ds):
    """Plain dicts/lists describing the graph. The browser draws it with Plotly.js."""
    n = graph.number_of_nodes()
    if n == 0:
        return {"nodes": [], "edges": []}

    # Positions: spring layout when there are links, otherwise a tidy circle.
    if graph.number_of_edges() > 0:
        pos = nx.spring_layout(graph, seed=42, weight="weight")
    else:
        pos = nx.circular_layout(graph)

    centrality = nx.degree_centrality(graph) if n > 1 else {node: 0 for node in graph}

    nodes = []
    for fid in graph.nodes:
        fac = ds.faculty_by_id[fid]
        nodes.append({
            "id": fid,
            "name": fac["name"],
            "department": fac["department"],
            "paper_count": fac["paper_count"],
            "degree": graph.degree(fid),
            "size": round(16 + 34 * centrality[fid], 1),       # bigger = more collaborators
            "x": float(pos[fid][0]),
            "y": float(pos[fid][1]),
            "profile": "/faculty/" + fid,
            "collaborators": [{"name": f["name"], "shared": w} for f, w in collaborators_of(graph, ds, fid)],
        })

    edges = []
    for a, b, data in graph.edges(data=True):
        edges.append({
            "x0": float(pos[a][0]), "y0": float(pos[a][1]),
            "x1": float(pos[b][0]), "y1": float(pos[b][1]),
            "weight": data["weight"],
            "label": f'{ds.faculty_by_id[a]["name"]} and {ds.faculty_by_id[b]["name"]}: '
                     f'{data["weight"]} shared paper(s)',
        })
    return {"nodes": nodes, "edges": edges}
