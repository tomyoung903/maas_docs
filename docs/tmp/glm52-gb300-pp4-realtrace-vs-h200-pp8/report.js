const REPORT = {"latency":{"h200":{"client_ttft":{"max":70.367078918,"mean":18.045243484405614,"min":4.470109679,"n":4810,"p50":17.1938877855,"p75":20.32835881675,"p90":24.1003420126,"p99":52.937980489849465},"internal_ttft":{"definition":"prefill_finished_time - forward_entry_time; excludes the SGLang scheduler queue","max":11.511131763458252,"mean":2.0331856942226385,"min":1.6021959781646729,"n":4810,"p50":1.900094985961914,"p75":2.1055359840393066,"p90":2.3950931072235107,"p99":4.603970358371734},"last_ten_complete_minute_bins":{"internal_ttft_p50":{"max":1.9362666606903076,"mean":1.8638604044914246,"median":1.8759015798568726,"min":1.7623400688171387},"internal_ttft_p90":{"max":2.4595559597015386,"mean":2.3037514019012453,"median":2.2811707258224487,"min":2.184573841094971},"internal_ttft_p99":{"max":4.960872650146484,"mean":4.243182862758634,"median":4.265816974639886,"min":3.4477518630027806}},"mean_nonqueue_noninternal_remainder_seconds":0.6403100438212299,"queue":{"max":55.28701,"mean":15.371747746361747,"min":0.00113,"n":4810,"p50":14.688005,"p75":17.817852499999997,"p90":21.593768,"p99":45.338638999999986},"ratio_of_mean_queue_to_mean_client_ttft":0.8518448509517617,"threshold_counts":{"client_ttft_le_20_seconds":3485,"client_ttft_le_30_seconds":4639,"internal_ttft_le_2_seconds":3202,"internal_ttft_le_3_seconds":4632,"internal_ttft_le_5_seconds":4774}},"gb300":{"client_ttft":{"max":43.075197189,"mean":11.1035332553545,"min":4.087402796,"n":4810,"p50":10.7150079065,"p75":12.39015902875,"p90":14.848097539000008,"p99":32.055409793829966},"internal_ttft":{"max":8.582805395126343,"mean":2.3395202386404024,"min":1.1615643501281738,"n":4810,"p50":2.2460016012191772,"p75":2.498432457447052,"p90":2.807329797744751,"p99":3.835234606266013},"queue":{"max":33.3361,"mean":7.846096704781708,"min":0.00084,"n":4810,"p50":7.590815000000001,"p75":9.280777500000001,"p90":11.705547000000019,"p99":27.144387299999998}}}};

const q = (selector, root = document) => root.querySelector(selector);
const qa = (selector, root = document) => [...root.querySelectorAll(selector)];

const sections = qa("main section[id]");
const navLinks = qa(".overview a");
const navObserver = new IntersectionObserver((entries) => {
  const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
  if (!visible) return;
  navLinks.forEach((link) => link.classList.toggle("active", link.getAttribute("href") === `#${visible.target.id}`));
}, { rootMargin: "-15% 0px -70% 0px", threshold: [0.05, 0.3, 0.7] });
sections.forEach((section) => navObserver.observe(section));

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add("visible");
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.08 });
qa(".reveal").forEach((item) => revealObserver.observe(item));

const latencyLabels = { client_ttft: "Client TTFT", queue: "SGLang queue", internal_ttft: "Internal TTFT" };
function renderLatency(stat) {
  const h = REPORT.latency.h200;
  const g = REPORT.latency.gb300;
  const keys = ["client_ttft", "queue", "internal_ttft"];
  const maximum = Math.max(...keys.flatMap((key) => [h[key][stat], g[key][stat]]));
  const chart = q("#latency-bars");
  chart.innerHTML = keys.map((key) => {
    const hw = Math.max(1, h[key][stat] / maximum * 100);
    const gw = Math.max(1, g[key][stat] / maximum * 100);
    return `<div class="bar-pair"><div class="bar-label">${latencyLabels[key]}</div><div class="bar-stack"><div class="bar-track"><div class="bar-fill h200" style="width:${hw}%">H200 ${h[key][stat].toFixed(3)} s</div></div><div class="bar-track"><div class="bar-fill gb300" style="width:${gw}%">GB300 ${g[key][stat].toFixed(3)} s</div></div></div></div>`;
  }).join("");
  q("#latency-caption").textContent = `${stat.toUpperCase()} values; each pair shares one scale, and all rows share the chart maximum.`;
}
qa("[data-latency-stat]").forEach((button) => button.addEventListener("click", () => {
  qa("[data-latency-stat]").forEach((candidate) => candidate.classList.remove("active"));
  button.classList.add("active");
  renderLatency(button.dataset.latencyStat);
}));
renderLatency("p50");

const queueMachine = q("#queue-machine");
q("#queue-toggle").addEventListener("click", (event) => {
  const paused = queueMachine.classList.toggle("paused");
  event.currentTarget.textContent = paused ? "Animate slots" : "Pause animation";
});
