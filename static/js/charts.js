/* charts.js - draws every bar chart with Plotly.js.
   Python sends {labels, values, orientation, x_title, y_title, name_label, value_label}
   in a data-chart attribute. All numbers come from the CSV files; nothing is typed in here. */
(function () {
  var TEXT = "#F4F1FF", MUTED = "#A2AAC0", GRID = "rgba(162,170,192,0.14)";
  var BAR_FALLBACK = "#A78BFA";                 // used if the gradient cannot be applied
  var GRAD_LIGHT = "#C4B5FD", GRAD_DEEP = "#6D4FD6";
  var FONT = "DM Sans, system-ui, sans-serif";
  var counter = 0;

  function short(label) { return label.length > 30 ? label.slice(0, 29) + "\u2026" : label; }

  // Plotly bars are flat colours, so after drawing we give each bar an SVG gradient fill:
  // light violet at the tip fading to deeper violet at the base.
  function applyGradient(el, id, horizontal) {
    var svg = el.querySelector("svg.main-svg");
    if (!svg) return;
    if (!svg.querySelector("#" + id)) {
      var ns = "http://www.w3.org/2000/svg";
      var defs = svg.querySelector("defs");
      if (!defs) { defs = document.createElementNS(ns, "defs"); svg.insertBefore(defs, svg.firstChild); }
      var g = document.createElementNS(ns, "linearGradient");
      g.setAttribute("id", id);
      g.setAttribute("x1", "0"); g.setAttribute("y1", "0");
      g.setAttribute("x2", horizontal ? "1" : "0"); g.setAttribute("y2", horizontal ? "0" : "1");
      // vertical bars: light at the top; horizontal bars: light at the right-hand tip
      var stops = horizontal ? [[0, GRAD_DEEP], [1, GRAD_LIGHT]] : [[0, GRAD_LIGHT], [1, GRAD_DEEP]];
      stops.forEach(function (s) {
        var stop = document.createElementNS(ns, "stop");
        stop.setAttribute("offset", String(s[0])); stop.setAttribute("stop-color", s[1]);
        g.appendChild(stop);
      });
      defs.appendChild(g);
    }
    el.querySelectorAll(".barlayer .point path").forEach(function (path) {
      path.style.fill = "url(#" + id + ")";
    });
  }

  function drawBar(el, cfg) {
    var horizontal = cfg.orientation === "h";
    var id = "rc-grad-" + (counter++);
    var shown = cfg.labels.map(short);
    var maxValue = Math.max.apply(null, cfg.values.concat([1]));
    var headroom = [0, Math.ceil(maxValue * 1.18 + 0.5)];     // space so the count label is never cut off

    var trace = {
      type: "bar",
      orientation: cfg.orientation,
      marker: { color: BAR_FALLBACK, line: { width: 0 } },
      text: cfg.values.map(String),                              // the count shown at the end of each bar
      textposition: "outside",
      cliponaxis: false,
      textfont: { color: TEXT, size: 13, family: FONT },
      hovertext: cfg.labels,
      customdata: cfg.values,
      hovertemplate: "<b>" + (cfg.name_label || "Item") + ":</b> %{hovertext}<br>" +
                     "<b>" + (cfg.value_label || "Count") + ":</b> %{customdata}<extra></extra>"
    };

    var countAxis = { gridcolor: GRID, zeroline: false, tickformat: "d", range: headroom,
                      fixedrange: true, title: { text: horizontal ? cfg.x_title : cfg.y_title, font: { size: 12 } } };
    var labelAxis = { type: "category", gridcolor: "rgba(0,0,0,0)", automargin: true, fixedrange: true,
                      title: { text: horizontal ? cfg.y_title : cfg.x_title, font: { size: 12 } } };
    if (horizontal) {
      trace.x = cfg.values; trace.y = shown;
      labelAxis.autorange = "reversed";                          // biggest bar on top
    } else {
      trace.x = shown; trace.y = cfg.values;
    }

    var layout = {
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: FONT, color: MUTED, size: 12 },
      margin: { l: 10, r: 24, t: 16, b: 10 },
      xaxis: horizontal ? countAxis : labelAxis,
      yaxis: horizontal ? labelAxis : countAxis,
      bargap: 0.3,
      hoverlabel: { bgcolor: "#202944", bordercolor: "#A78BFA", font: { color: TEXT, family: FONT, size: 13 } }
    };

    var done = Plotly.newPlot(el, [trace], layout, { displayModeBar: false, responsive: true });
    var paint = function () { applyGradient(el, id, horizontal); };
    if (done && done.then) done.then(paint);
    if (el.on) el.on("plotly_afterplot", paint);                 // re-apply after a resize redraw
  }

  document.querySelectorAll("[data-chart]").forEach(function (el) {
    try { drawBar(el, JSON.parse(el.getAttribute("data-chart"))); }
    catch (err) { el.textContent = "This chart could not be drawn."; }
  });
})();
