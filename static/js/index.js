const BASE = "";

const GLX_STATIONS = new Set([
  'place-lech', 'place-spmnl', 'place-gilmn',
  'place-esomr', 'place-mgngl', 'place-balsq', 'place-mdftf'
]);

const GROUP_COLORS = {
  'GLX':                    '#1b7a3e',
  'Green-E (non-GLX)':      '#52b788',
  'Green (other branches)': '#a8d5b5',
  'Red Line':               '#c0392b',
  'Orange Line':            '#e67e22',
  'Blue Line':              '#2980b9',
  'Mattapan':               '#8e44ad',
};

const GROUP_ORDER = [
  'GLX', 'Green-E (non-GLX)', 'Green (other branches)',
  'Red Line', 'Orange Line', 'Blue Line', 'Mattapan'
];

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

function getParams() {
  return {
    day_type: document.getElementById("day-type").value,
    exclude_terminal: document.getElementById("exclude-terminal").checked,
    direction: document.getElementById("direction").value,
  };
}

function qs(params) {
  return Object.entries(params)
    .filter(([_, v]) => v !== "all" && v !== false)
    .map(([k, v]) => `${k}=${v}`)
    .join("&");
}

// Chart 1: Network comparison box plot
function drawNetwork(data) {
  const el = document.getElementById("chart-network");
  const W = el.parentElement.clientWidth - 40;
  const H = 300;
  const margin = { top: 20, right: 20, bottom: 50, left: 70 };
  const w = W - margin.left - margin.right;
  const h = H - margin.top - margin.bottom;

  d3.select(el).selectAll("*").remove();
  const svg = d3.select(el)
    .attr("width", W).attr("height", H)
    .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const groups = data.map(d => d.group);
  const x = d3.scaleBand().domain(groups).range([0, w]).padding(0.3);
  const y = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.q3) * 1.3])
    .range([h, 0]);

  svg.append("g").attr("transform", `translate(0,${h})`)
    .call(d3.axisBottom(x).tickSize(0))
    .call(g => g.select(".domain").remove())
    .selectAll("text")
    .attr("font-family", "DM Sans").attr("font-size", "11px")
    .style("text-anchor", "middle");

  svg.append("g")
    .call(d3.axisLeft(y).ticks(6).tickFormat(d => `${d} min`))
    .call(g => g.select(".domain").remove())
    .selectAll("text").attr("font-family", "DM Mono").attr("font-size", "10px");

  svg.append("g")
    .call(d3.axisLeft(y).ticks(6).tickSize(-w).tickFormat(""))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").attr("stroke", "#f0f0f0"));

  svg.append("text").attr("class", "axis-label")
    .attr("transform", "rotate(-90)")
    .attr("x", -h / 2).attr("y", -58)
    .attr("text-anchor", "middle")
    .text("Headway (minutes)");

  const bw = x.bandwidth();

  data.forEach(d => {
    const cx = x(d.group) + bw / 2;
    const color = GROUP_COLORS[d.group] || "#999";
    const isGLX = d.group === "GLX";

    svg.append("rect")
      .attr("x", x(d.group))
      .attr("y", y(d.q3))
      .attr("width", bw)
      .attr("height", Math.max(0, y(d.q1) - y(d.q3)))
      .attr("fill", color)
      .attr("opacity", isGLX ? 1 : 0.6)
      .attr("stroke", color)
      .attr("stroke-width", isGLX ? 2.5 : 1)
      .attr("rx", 2)
      .style("cursor", "pointer")
      .on("mousemove", (event) => showTooltip(
        `<b>${d.group}</b><br>
         Median: ${d.median.toFixed(1)} min<br>
         Mean: ${d.mean.toFixed(1)} min<br>
         Q1: ${d.q1.toFixed(1)} / Q3: ${d.q3.toFixed(1)} min<br>
         Long gap: ${d.long_gap_pct.toFixed(1)}%<br>
         n: ${d.n.toLocaleString()}`, event))
      .on("mouseleave", hideTooltip);

    svg.append("line")
      .attr("x1", x(d.group)).attr("x2", x(d.group) + bw)
      .attr("y1", y(d.median)).attr("y2", y(d.median))
      .attr("stroke", "white")
      .attr("stroke-width", 2);

    svg.append("circle")
      .attr("cx", cx).attr("cy", y(d.mean))
      .attr("r", 3).attr("fill", "white")
      .attr("stroke", color).attr("stroke-width", 1.5);

    svg.append("text")
      .attr("x", cx).attr("y", y(d.q3) - 5)
      .attr("text-anchor", "middle")
      .attr("font-size", "9px")
      .attr("font-family", "DM Mono")
      .attr("fill", "#6b7280")
      .text(`${d.long_gap_pct.toFixed(1)}%`);
  });
}

// Chart 2: Hour-of-day GLX vs Green-E
function drawHour(data) {
  const el = document.getElementById("chart-hour");
  const W = el.parentElement.clientWidth - 40;
  const H = 280;
  const margin = { top: 20, right: 110, bottom: 55, left: 70 };
  const w = W - margin.left - margin.right;
  const h = H - margin.top - margin.bottom;

  d3.select(el).selectAll("*").remove();
  const svg = d3.select(el)
    .attr("width", W).attr("height", H)
    .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const groups = ["GLX", "Green-E (non-GLX)"];
  const x = d3.scaleLinear().domain([0, 23]).range([0, w]);
  const y = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.mean_headway) * 1.2])
    .range([h, 0]);

  svg.append("g").attr("transform", `translate(0,${h})`)
    .call(d3.axisBottom(x).ticks(12).tickFormat(d => `${d}:00`))
    .call(g => g.select(".domain").remove())
    .selectAll("text").attr("font-family", "DM Mono").attr("font-size", "10px");

  svg.append("g")
    .call(d3.axisLeft(y).ticks(5).tickFormat(d => `${d.toFixed(0)} min`))
    .call(g => g.select(".domain").remove())
    .selectAll("text").attr("font-family", "DM Mono").attr("font-size", "10px");

  svg.append("g")
    .call(d3.axisLeft(y).ticks(5).tickSize(-w).tickFormat(""))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").attr("stroke", "#f0f0f0"));

  svg.append("text").attr("class", "axis-label")
    .attr("x", w / 2).attr("y", h + 50)
    .attr("text-anchor", "middle").text("Hour of Day");

  svg.append("text").attr("class", "axis-label")
    .attr("transform", "rotate(-90)")
    .attr("x", -h / 2).attr("y", -58)
    .attr("text-anchor", "middle").text("Headway (minutes)");

  groups.forEach(grp => {
    const grpData = data.filter(d => d.group === grp)
      .sort((a, b) => a.hour_of_day - b.hour_of_day);
    const color = GROUP_COLORS[grp];
    const isDashed = grp !== "GLX";

    const line = d3.line()
      .x(d => x(d.hour_of_day))
      .y(d => y(d.mean_headway));

    svg.append("path").datum(grpData)
      .attr("fill", "none")
      .attr("stroke", color)
      .attr("stroke-width", 2)
      .attr("stroke-dasharray", isDashed ? "5,3" : "none")
      .attr("d", line);
  });

  // Legend
  const leg = svg.append("g").attr("transform", `translate(${w + 12}, 20)`);
  groups.forEach((grp, i) => {
    const color = GROUP_COLORS[grp];
    leg.append("line")
      .attr("x1", 0).attr("x2", 20)
      .attr("y1", i * 20 + 6).attr("y2", i * 20 + 6)
      .attr("stroke", color).attr("stroke-width", 2)
      .attr("stroke-dasharray", i === 0 ? "none" : "5,3");
    leg.append("text").attr("x", 24).attr("y", i * 20 + 10)
      .attr("font-size", "10px").attr("font-family", "DM Sans")
      .attr("fill", "#374151").text(grp);
  });
  
  svg.append("rect")
    .attr("width", w).attr("height", h)
    .attr("fill", "none").attr("pointer-events", "all")
    .on("mousemove", function(event) {
      const xVal = Math.round(x.invert(d3.pointer(event)[0]));
      const glxD = data.find(r => r.hour_of_day === xVal && r.group === "GLX");
      const nonD = data.find(r => r.hour_of_day === xVal && r.group === "Green-E (non-GLX)");
      if (!glxD || !nonD) return;
      showTooltip(
        `<b>${xVal}:00</b><br>
         GLX: ${glxD.mean_headway.toFixed(1)} min<br>
         Green-E: ${nonD.mean_headway.toFixed(1)} min`, event);
    })
    .on("mouseleave", hideTooltip);
}

// Chart 3: Monthly trend — all line groups
function drawMonth(data) {
  const el = document.getElementById("chart-month");
  const W = el.parentElement.clientWidth - 40;
  const H = 280;
  const margin = { top: 20, right: 150, bottom: 40, left: 70 };
  const w = W - margin.left - margin.right;
  const h = H - margin.top - margin.bottom;

  d3.select(el).selectAll("*").remove();
  const svg = d3.select(el)
    .attr("width", W).attr("height", H)
    .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const monthNames = ["Jan","Feb","Mar","Apr","May","Jun",
                      "Jul","Aug","Sep","Oct","Nov","Dec"];
  const groups = GROUP_ORDER.filter(g => data.some(d => d.group === g));

  const x = d3.scaleLinear().domain([1, 12]).range([0, w]);
  const y = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.mean) * 1.2])
    .range([h, 0]);

  svg.append("g").attr("transform", `translate(0,${h})`)
    .call(d3.axisBottom(x).ticks(12).tickFormat(d => monthNames[d - 1]))
    .call(g => g.select(".domain").remove())
    .selectAll("text").attr("font-family", "DM Mono").attr("font-size", "10px");

  svg.append("g")
    .call(d3.axisLeft(y).ticks(5).tickFormat(d => `${d.toFixed(0)} min`))
    .call(g => g.select(".domain").remove())
    .selectAll("text").attr("font-family", "DM Mono").attr("font-size", "10px");

  svg.append("g")
    .call(d3.axisLeft(y).ticks(5).tickSize(-w).tickFormat(""))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").attr("stroke", "#f0f0f0"));

  svg.append("text").attr("class", "axis-label")
    .attr("transform", "rotate(-90)")
    .attr("x", -h / 2).attr("y", -58)
    .attr("text-anchor", "middle").text("Median Headway (minutes)");

  groups.forEach(grp => {
    const grpData = data.filter(d => d.group === grp)
      .sort((a, b) => a.month - b.month);
    if (grpData.length === 0) return;

    const color = GROUP_COLORS[grp] || "#999";
    const isGLX = grp === "GLX";

    const line = d3.line()
      .x(d => x(d.month))
      .y(d => y(d.median));

    svg.append("path").datum(grpData)
      .attr("fill", "none")
      .attr("stroke", color)
      .attr("stroke-width", isGLX ? 2.5 : 1.5)
      .attr("opacity", isGLX ? 1 : 0.6)
      .attr("d", line);

    grpData.forEach(d => {
      svg.append("circle")
        .attr("cx", x(d.month))
        .attr("cy", y(d.median))
        .attr("r", isGLX ? 4 : 3)
        .attr("fill", color)
        .attr("opacity", isGLX ? 1 : 0.6)
        .style("cursor", "pointer")
        .on("mousemove", (event) => showTooltip(
          `<b>${grp}</b><br>
           ${monthNames[d.month - 1]}: ${d.median.toFixed(1)} min`, event))
        .on("mouseleave", hideTooltip);
    });
  });

  // Legend
  const leg = svg.append("g").attr("transform", `translate(${w + 12}, 0)`);
  groups.forEach((grp, i) => {
    const color = GROUP_COLORS[grp] || "#999";
    const isGLX = grp === "GLX";
    leg.append("line")
      .attr("x1", 0).attr("x2", 20)
      .attr("y1", i * 18 + 6).attr("y2", i * 18 + 6)
      .attr("stroke", color)
      .attr("stroke-width", isGLX ? 2.5 : 1.5)
      .attr("opacity", isGLX ? 1 : 0.6);
    leg.append("text").attr("x", 24).attr("y", i * 18 + 10)
      .attr("font-size", "10px").attr("font-family", "DM Sans")
      .attr("fill", "#374151").text(grp);
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
      <td>${d.is_terminal
        ? '<span class="t-badge small">T</span>'
        : isGLX ? '<span class="glx-label">GLX</span>' : ''}</td>
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

  const [network, hour, month, miss] = await Promise.all([
    fetch(`${BASE}/api/network_comparison?${q}`).then(r => r.json()),
    fetch(`${BASE}/api/by_hour?${q}`).then(r => r.json()),
    fetch(`${BASE}/api/by_month?${q}`).then(r => r.json()),
    fetch(`${BASE}/api/missingness?${q}`).then(r => r.json()),
  ]);

  drawNetwork(network);
  drawHour(hour);
  drawMonth(month);
  drawMissingness(miss);
}

// Init
document.getElementById("submit").addEventListener("click", updateAll);
updateAll();