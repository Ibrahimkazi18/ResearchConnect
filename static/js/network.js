/* network.js - draws the faculty collaboration graph with Plotly.js.
   Python (NetworkX) already worked out positions, sizes and edges; this file only draws them. */
(function () {
  var data = window.RC_NETWORK, el = document.getElementById("network-plot");
  var panel = document.getElementById("node-panel");
  if (!data || !el || !panel) return;

  var traces = [];
  // one line per verified co-authorship; thicker line = more shared papers
  data.edges.forEach(function (e) {
    var mx = (e.x0 + e.x1) / 2, my = (e.y0 + e.y1) / 2;
    traces.push({
      type: "scatter", mode: "lines", x: [e.x0, mx, e.x1], y: [e.y0, my, e.y1],
      line: { width: 2 + e.weight * 2, color: "rgba(196,181,253,0.7)" },
      text: [e.label, e.label, e.label], hoverinfo: "text", showlegend: false
    });
  });

  var maxDeg = Math.max.apply(null, data.nodes.map(function (n) { return n.degree; }).concat([1]));
  var baseLine = data.nodes.map(function () { return "#090E1D"; });
  var nodeTrace = {
    type: "scatter", mode: "markers+text",
    x: data.nodes.map(function (n) { return n.x; }),
    y: data.nodes.map(function (n) { return n.y; }),
    text: data.nodes.map(function (n) { return n.name.length > 20 ? n.name.slice(0, 19) + "\u2026" : n.name; }),
    textposition: "top center", textfont: { color: "#A2AAC0", size: 11 },
    customdata: data.nodes.map(function (n) { return n.id; }),
    hovertext: data.nodes.map(function (n) {
      return n.name + (n.department ? "<br>" + n.department : "") + "<br>" + n.paper_count + " paper(s), " + n.degree + " collaborator(s)";
    }),
    hoverinfo: "text", showlegend: false,
    marker: {
      size: data.nodes.map(function (n) { return n.size; }),
      color: data.nodes.map(function (n) { return n.degree; }),
      cmin: 0, cmax: maxDeg,
      colorscale: [[0, "#7C6BD6"], [1, "#DDD3FF"]],
      line: { color: baseLine, width: 3 }
    }
  };
  traces.push(nodeTrace);

  var axis = { visible: false, fixedrange: true };
  Plotly.newPlot(el, traces, {
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 20, r: 20, t: 20, b: 20 }, hovermode: "closest",
    xaxis: Object.assign({ range: [-1.35, 1.35] }, axis),
    yaxis: Object.assign({ range: [-1.35, 1.35] }, axis)
  }, { displayModeBar: false, responsive: true });

  function add(parent, tag, text, cls) {
    var node = document.createElement(tag);
    node.textContent = text;
    if (cls) node.className = cls;
    parent.appendChild(node);
    return node;
  }

  function showFaculty(id) {
    var n = data.nodes.find(function (item) { return item.id === id; });
    if (!n) return;
    panel.innerHTML = "";
    add(panel, "h2", n.name, "card-heading mb-1");
    add(panel, "p", n.department || "Department not listed", "muted");
    add(panel, "p", n.paper_count + (n.paper_count === 1 ? " paper" : " papers") + " in the data");
    add(panel, "h3", "Verified collaborators", "fs-6 mt-3");
    if (n.collaborators.length === 0) {
      add(panel, "p", "No VJTI co-authors are recorded for this faculty member.", "muted");
    } else {
      var list = add(panel, "ul", "", "mini-list");
      n.collaborators.forEach(function (c) {
        add(list, "li", c.name + " (" + c.shared + " shared " + (c.shared === 1 ? "paper" : "papers") + ")");
      });
    }
    var link = add(panel, "a", "Open full profile", "btn rc-btn-ghost btn-sm node-link");
    link.href = n.profile;

    // outline the selected node
    var lines = data.nodes.map(function (item) { return item.id === id ? "#F4F1FF" : "#090E1D"; });
    Plotly.restyle(el, { "marker.line.color": [lines] }, [traces.length - 1]);
  }

  el.on("plotly_click", function (ev) {
    if (ev.points && ev.points[0] && ev.points[0].customdata) showFaculty(ev.points[0].customdata);
  });
})();
