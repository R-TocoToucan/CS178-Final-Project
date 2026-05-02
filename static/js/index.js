const BASE = "";

const GLX_STATIONS = new Set([
  'place-lech', 'place-spmnl', 'place-gilmn',
  'place-esomr', 'place-mgngl', 'place-balsq', 'place-mdftf'
]);

// Tooltip helpers
const tooltip = document.getElementById("tooltip");

function showTooltip(html, event) {
  tooltip.innerHTML = html;
  tooltip.classList.add("visible");
  moveTooltip(event);
}

function moveTooltip(event) {
  tooltip.style.left = (event.clientX + 14) + "px";
  tooltip.style.top = (event.clientY - 28) + "px";
}

function hideTooltip() {
  tooltip.classList.remove("visible");
}

// Get control values
function getParams() {
  return {
    day_type: document.getElementById("day-type").value,
    exclude_terminal: document.getElementById("exclude-terminal").checked,
    branch: document.getElementById("branch").value,
    direction: document.getElementById("direction").value,
  };
}

function qs(params) {
  return Object.entries(params)
    .filter(([_, v]) => v !== "all" && v !== false)
    .map(([k, v]) => `${k}=${v}`)
    .join("&");
}

// Chart 1: Distribution box plot
function drawDistribution(data) {
  const el = document.getElementById("chart-distribution");
  const W = el.parentElement.clientWidth - 40;
  const H = 280;
  const margin = { top: 16, right: 110, bottom: 50, left: 65 };
  const w = W - margin.left - margin.right;
  const h = H - margin.top - margin.bottom;

  d3.select(el).selectAll("*").remove();
  const svg = d3.select(el)
    .attr("width", W).attr("height", H)
    .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const branches = data.map(d => d.branch_route_id);
  const x = d3.scaleBand().domain(branches).range([0, w]).padding(0.3);
  const y = d3.scaleLinear().domain([0, d3.max(data, d => d.q3) * 1.35]).range([h, 0]);

  svg.append("g").attr("transform", `translate(0,${h})`)
    .call(d3.axisBottom(x).tickSize(0))
    .call(g => g.select(".domain").remove())
    .selectAll("text").attr("font-family", "DM Sans").attr("font-size", "12px");

  svg.append("g")
    .call(d3.axisLeft(y).ticks(5).tickFormat(d => `${d} min`))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").attr("stroke", "#e5e7eb"))
    .selectAll("text").attr("font-family", "DM Mono").attr("font-size", "10px");

  svg.append("g").attr("class", "grid")
    .call(d3.axisLeft(y).ticks(5).tickSize(-w).tickFormat(""))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").attr("stroke", "#f0f0f0").attr("stroke-width", 1));

  svg.append("text")
    .attr("class", "axis-label")
    .attr("transform", "rotate(-90)")
    .attr("x", -h / 2).attr("y", -52)
    .attr("text-anchor", "middle")
    .text("Headway (minutes)");

  const bw = x.bandwidth();

  data.forEach(d => {
    const cx = x(d.branch_route_id) + bw / 2;
    const isGreen = d.branch_route_id.startsWith("Green");

    svg.append("rect")
      .attr("x", x(d.branch_route_id))
      .attr("y", y(d.q3))
      .attr("width", bw)
      .attr("height", Math.max(0, y(d.q1) - y(d.q3)))
      .attr("fill", isGreen ? "#a8d5b5" : "#b8cce4")
      .attr("stroke", isGreen ? "#1b7a3e" : "#2c5f8a")
      .attr("stroke-width", 1.5)
      .attr("rx", 2)
      .style("cursor", "pointer")
      .on("mousemove", (event) => showTooltip(
        `<b>${d.branch_route_id}</b><br>
         Median: ${d.median.toFixed(1)} min<br>
         Mean: ${d.mean.toFixed(1)} min<br>
         Q1: ${d.q1.toFixed(1)} / Q3: ${d.q3.toFixed(1)} min<br>
         Long gap: ${d.long_gap_pct.toFixed(1)}%`, event))
      .on("mouseleave", hideTooltip);

    svg.append("line")
      .attr("x1", x(d.branch_route_id)).attr("x2", x(d.branch_route_id) + bw)
      .attr("y1", y(d.median)).attr("y2", y(d.median))
      .attr("stroke", isGreen ? "#1b7a3e" : "#2c5f8a")
      .attr("stroke-width", 2.5);

    svg.append("circle")
      .attr("cx", cx).attr("cy", y(d.mean))
      .attr("r", 4).attr("fill", "#e74c3c")
      .style("cursor", "pointer")
      .on("mousemove", (event) => showTooltip(
        `<b>${d.branch_route_id}</b><br>Mean: ${d.mean.toFixed(2)} min`, event))
      .on("mouseleave", hideTooltip);

    svg.append("text")
      .attr("x", cx).attr("y", y(d.q3) - 6)
      .attr("text-anchor", "middle")
      .attr("font-size", "10px")
      .attr("font-family", "DM Mono")
      .attr("fill", "#6b7280")
      .text(`${d.long_gap_pct.toFixed(1)}%`);
  });

  // Legend
  const leg = svg.append("g").attr("transform", `translate(${w + 12}, 20)`);
  [
    ["IQR box", "#a8d5b5", "rect"],
    ["Median", "#1b7a3e", "line"],
    ["Mean", "#e74c3c", "dot"],
  ].forEach(([label, color, type], i) => {
    if (type === "rect") {
      leg.append("rect").attr("x", 0).attr("y", i * 20).attr("width", 12).attr("height", 12)
        .attr("fill", color).attr("rx", 2);
    } else if (type === "line") {
      leg.append("line").attr("x1", 0).attr("x2", 12)
        .attr("y1", i * 20 + 6).attr("y2", i * 20 + 6)
        .attr("stroke", color).attr("stroke-width", 2.5);
    } else {
      leg.append("circle").attr("cx", 6).attr("cy", i * 20 + 6).attr("r", 4).attr("fill", color);
    }
    leg.append("text").attr("x", 16).attr("y", i * 20 + 10)
      .attr("font-size", "10px").attr("font-family", "DM Sans").text(label);
  });
}


// Chart 2: GLX vs Green-E comparison
function drawGLX(data) {
  const el = document.getElementById("chart-glx");
  const W = el.parentElement.clientWidth - 40;
  const H = 280;
  const margin = { top: 16, right: 150, bottom: 50, left: 55 };
  const w = W - margin.left - margin.right;
  const h = H - margin.top - margin.bottom;

  d3.select(el).selectAll("*").remove();
  const svg = d3.select(el)
    .attr("width", W).attr("height", H)
    .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const metrics = ["mean", "median", "stddev", "long_gap_pct"];
  const labels = ["Mean (min)", "Median (min)", "Std Dev", "Long Gap %"];
  const groups = data.map(d => d.group);
  const colors = { "GLX": "#1b7a3e", "Green-E (non-GLX)": "#a8d5b5" };

  const x0 = d3.scaleBand().domain(labels).range([0, w]).padding(0.25);
  const x1 = d3.scaleBand().domain(groups).range([0, x0.bandwidth()]).padding(0.05);
  const y = d3.scaleLinear()
    .domain([0, d3.max(data, d => Math.max(d.mean, d.stddev, d.long_gap_pct)) * 1.25])
    .range([h, 0]);

  svg.append("g").attr("transform", `translate(0,${h})`)
    .call(d3.axisBottom(x0).tickSize(0))
    .call(g => g.select(".domain").remove())
    .selectAll("text").attr("font-family", "DM Sans").attr("font-size", "11px");

  svg.append("g")
    .call(d3.axisLeft(y).ticks(5))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").attr("stroke", "#e5e7eb"))
    .selectAll("text").attr("font-family", "DM Mono").attr("font-size", "10px");

  svg.append("g").attr("class", "grid")
    .call(d3.axisLeft(y).ticks(5).tickSize(-w).tickFormat(""))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").attr("stroke", "#f0f0f0"));

  svg.append("text")
    .attr("class", "axis-label")
    .attr("transform", "rotate(-90)")
    .attr("x", -h / 2).attr("y", -44)
    .attr("text-anchor", "middle")
    .text("Value");

  metrics.forEach((metric, mi) => {
    data.forEach(d => {
      svg.append("rect")
        .attr("x", x0(labels[mi]) + x1(d.group))
        .attr("y", y(d[metric]))
        .attr("width", x1.bandwidth())
        .attr("height", h - y(d[metric]))
        .attr("fill", colors[d.group])
        .attr("rx", 2)
        .style("cursor", "pointer")
        .on("mousemove", (event) => showTooltip(
          `<b>${d.group}</b><br>${labels[mi]}: ${d[metric].toFixed(2)}`, event))
        .on("mouseleave", hideTooltip);
    });
  });

  // Legend
  const leg = svg.append("g").attr("transform", `translate(${w + 12}, 20)`);
  groups.forEach((g, i) => {
    leg.append("rect").attr("x", 0).attr("y", i * 20).attr("width", 12).attr("height", 12)
      .attr("fill", colors[g]).attr("rx", 2);
    leg.append("text").attr("x", 16).attr("y", i * 20 + 10)
      .attr("font-size", "10px").attr("font-family", "DM Sans").text(g);
  });
}
// Chart 3: Hour-of-day line chart
function drawHour(data) {
  const el = document.getElementById("chart-hour");
  const W = el.parentElement.clientWidth - 40;
  const H = 260;
  const margin = { top: 20, right: 110, bottom: 50, left: 70 };
  const w = W - margin.left - margin.right;
  const h = H - margin.top - margin.bottom;

  d3.select(el).selectAll("*").remove();
  const svg = d3.select(el)
    .attr("width", W).attr("height", H)
    .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const x = d3.scaleLinear().domain([0, 23]).range([0, w]);
  const y = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.mean_headway) * 1.2])
    .range([h, 0]);

  svg.append("g").attr("transform", `translate(0,${h})`)
    .call(d3.axisBottom(x).ticks(12).tickFormat(d => `${d}:00`))
    .call(g => g.select(".domain").remove())
    .selectAll("text").attr("font-family", "DM Mono").attr("font-size", "10px")
    .attr("transform", "rotate(-35)").style("text-anchor", "end");

  svg.append("g")
    .call(d3.axisLeft(y).ticks(5).tickFormat(d => `${d.toFixed(0)} min`))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").attr("stroke", "#e5e7eb"))
    .selectAll("text").attr("font-family", "DM Mono").attr("font-size", "10px");

  // Gridlines
  svg.append("g").attr("class", "grid")
    .call(d3.axisLeft(y).ticks(5).tickSize(-w).tickFormat(""))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").attr("stroke", "#f0f0f0"));

  // Axis labels
  svg.append("text").attr("class", "axis-label")
    .attr("x", w / 2).attr("y", h + 44)
    .attr("text-anchor", "middle").text("Hour of Day");

  svg.append("text").attr("class", "axis-label")
    .attr("transform", "rotate(-90)")
    .attr("x", -h / 2).attr("y", -58)
    .attr("text-anchor", "middle").text("Headway (minutes)");

  // Mean area fill
  const area = d3.area().x(d => x(d.hour_of_day)).y0(h).y1(d => y(d.mean_headway));
  svg.append("path").datum(data)
    .attr("fill", "#a8d5b5").attr("opacity", 0.3).attr("d", area);

  // Mean line
  const line = d3.line().x(d => x(d.hour_of_day)).y(d => y(d.mean_headway));
  svg.append("path").datum(data)
    .attr("fill", "none").attr("stroke", "#1b7a3e")
    .attr("stroke-width", 2).attr("d", line);

  // Median line
  const medLine = d3.line().x(d => x(d.hour_of_day)).y(d => y(d.median_headway));
  svg.append("path").datum(data)
    .attr("fill", "none").attr("stroke", "#1b7a3e")
    .attr("stroke-width", 1.5).attr("stroke-dasharray", "4,3").attr("d", medLine);

  // Hover dots
  const focus = svg.append("g").style("display", "none");
  focus.append("circle").attr("r", 5).attr("fill", "#1b7a3e");
  focus.append("line").attr("class", "focus-line")
    .attr("y1", 0).attr("y2", h)
    .attr("stroke", "#ccc").attr("stroke-width", 1).attr("stroke-dasharray", "3,3");

  svg.append("rect")
    .attr("width", w).attr("height", h)
    .attr("fill", "none").attr("pointer-events", "all")
    .on("mousemove", function(event) {
      const xVal = Math.round(x.invert(d3.pointer(event)[0]));
      const d = data.find(r => r.hour_of_day === xVal);
      if (!d) return;
      focus.style("display", null)
        .attr("transform", `translate(${x(d.hour_of_day)},${y(d.mean_headway)})`);
      focus.select(".focus-line").attr("transform", `translate(0,${-y(d.mean_headway)})`);
      showTooltip(
        `<b>${d.hour_of_day}:00</b><br>
         Mean: ${d.mean_headway.toFixed(1)} min<br>
         Median: ${d.median_headway.toFixed(1)} min<br>
         Long gap: ${d.long_gap_pct.toFixed(1)}%`, event);
    })
    .on("mouseleave", () => { focus.style("display", "none"); hideTooltip(); });

  // Legend
  const leg = svg.append("g").attr("transform", `translate(${w + 12}, 20)`);
  [["Mean", "#1b7a3e", ""], ["Median", "#1b7a3e", "4,3"]].forEach(([label, color, dash], i) => {
    leg.append("line").attr("x1", 0).attr("x2", 18).attr("y1", i * 18 + 6).attr("y2", i * 18 + 6)
      .attr("stroke", color).attr("stroke-width", 2).attr("stroke-dasharray", dash);
    leg.append("text").attr("x", 22).attr("y", i * 18 + 10)
      .attr("font-size", "10px").attr("font-family", "DM Sans").text(label);
  });
}

// Chart 4: Missingness table
function drawMissingness(data) {
  const container = document.getElementById("table-missingness");
  container.innerHTML = "";

  const table = document.createElement("table");
  table.innerHTML = `
    <thead>
      <tr>
        <th>Stop</th>
        <th>Null %</th>
        <th></th>
        <th>Bar</th>
      </tr>
    </thead>
  `;

  const tbody = document.createElement("tbody");
  data.forEach(d => {
    const isGLX = GLX_STATIONS.has(d.parent_station);
    const tr = document.createElement("tr");
    if (d.is_terminal) tr.classList.add("terminal");
    else if (isGLX) tr.classList.add("glx-stop");

    tr.innerHTML = `
      <td>${d.stop_name}</td>
      <td style="font-family:DM Mono;font-size:11px">${d.null_pct.toFixed(1)}%</td>
      <td>${d.is_terminal ? '<span class="t-badge">T</span>' : (isGLX ? '<span style="font-size:10px;color:#1b7a3e;font-weight:700">GLX</span>' : '')}</td>
      <td>
        <div class="null-bar-wrap">
          <div class="null-bar" style="width:${Math.min(d.null_pct, 100)}%"></div>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  container.appendChild(table);
}

// Fetch and render all charts
async function updateAll() {
  const p = getParams();
  const q = qs(p);

  const [dist, glx, hour, miss] = await Promise.all([
    fetch(`${BASE}/api/distribution?${q}`).then(r => r.json()),
    fetch(`${BASE}/api/glx_comparison?${q}`).then(r => r.json()),
    fetch(`${BASE}/api/by_hour?${q}`).then(r => r.json()),
    fetch(`${BASE}/api/missingness?branch=${p.branch}`).then(r => r.json()),
  ]);

  drawDistribution(dist);
  drawGLX(glx);
  drawHour(hour);
  drawMissingness(miss);
}

// Init
document.getElementById("submit").addEventListener("click", updateAll);
updateAll();