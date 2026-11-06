'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const video = $('cache-video');
  if (video) {
    document.querySelectorAll('[data-video-seek]').forEach(button => {
      button.addEventListener('click', () => {
        video.currentTime = Number(button.dataset.videoSeek);
        video.play().catch(() => {});
      });
    });
  }

  let dirty = false;
  let step = 0;
  const descriptions = {
    clean: [
      ['1. Preparation leaves unrelated clean data', 'The read-only sweep replaces useful GEMM inputs with unrelated clean lines. It does not make L2 literally empty.'],
      ['2. GEMM replaces a clean line', 'A clean line can be discarded. Loading GEMM inputs does not require writing this old line back to HBM.'],
      ['3. GEMM receives its inputs', 'Input data reaches the SM through the cache and shared-memory path. The controlled median for this preparation is 42.080 µs.']
    ],
    dirty: [
      ['1. Preparation can leave unrelated dirty data', 'The write-based sweep changes the eviction buffer. Some modified lines can remain in L2 after that kernel finishes.'],
      ['2. GEMM replaces a dirty line', 'Replacing modified data can require a writeback to HBM. That traffic can compete with the GEMM input reads during the measured interval.'],
      ['3. GEMM receives its inputs after extra traffic', 'The arithmetic is unchanged. The memory state created by preparation adds work outside the supplied tile plan. The controlled median is 52.032 µs.']
    ]
  };
  function render() {
    $('choose-clean').setAttribute('aria-pressed', String(!dirty));
    $('choose-dirty').setAttribute('aria-pressed', String(dirty));
    $('cache-step').value = step;
    $('step-count').textContent = `${step + 1} / 3`;
    $('next-step').textContent = step === 2 ? 'Back to step 1' : 'Next step →';
    const [title, explanation] = descriptions[dirty ? 'dirty' : 'clean'][step];
    $('step-title').textContent = title;
    $('step-explanation').textContent = explanation;
    $('l2-line').setAttribute('class', step === 2 ? 'input-line' : dirty ? 'dirty-line' : 'clean-line');
    $('line-label').textContent = step === 2 ? 'GEMM inputs' : 'Unrelated data';
    $('line-state').textContent = step === 2 ? 'available to read' : dirty ? 'modified / dirty' : 'clean';
    $('read-path').style.opacity = step > 0 ? '1' : '.15';
    $('sm-path').style.opacity = step === 2 ? '1' : '.15';
    $('writeback-path').toggleAttribute('hidden', !(dirty && step === 1));
    $('discard-label').textContent = step === 2 ? 'Replacement is complete in this schematic.' : dirty ? (step === 1 ? 'The old modified data must be preserved.' : 'Some modified lines can remain cached.') : 'Clean lines can be discarded.';
    $('cache-svg-desc').textContent = `${title}. ${explanation}`;
  }
  $('choose-clean').addEventListener('click', () => { dirty = false; render(); });
  $('choose-dirty').addEventListener('click', () => { dirty = true; render(); });
  $('cache-step').addEventListener('input', e => { step = Number(e.target.value); render(); });
  $('next-step').addEventListener('click', () => { step = (step + 1) % 3; render(); });
  render();

  const keys = ['ro_then_no_write', 'ro_then_dirty4mib', 'ro_then_dirty16mib', 'ro_then_dirty32mib', 'ro_then_dirty64mib', 'ro_then_dirty128mib'];
  const labels = ['None', '4 MiB', '16 MiB', '32 MiB', '64 MiB', '128 MiB'];
  fetch('data/measurements.json').then(r => {
    if (!r.ok) throw new Error('Cannot load saved measurements');
    return r.json();
  }).then(data => {
    const measurements = data.runs.small_dirty_footprint_trace.modes;
    const base = measurements[keys[0]].median_us;
    function showSweep() {
      const i = Number($('dirty-size').value);
      const value = measurements[keys[i]].median_us;
      $('dirty-size-label').textContent = labels[i];
      $('sweep-time').textContent = `${value.toFixed(3)} µs`;
      $('sweep-delta').textContent = i ? `+${(value - base).toFixed(3)} µs after additional writes` : 'No additional writes';
    }
    $('dirty-size').addEventListener('input', showSweep);
    showSweep();
  }).catch(() => {
    $('dirty-size').disabled = true;
    $('sweep-delta').textContent = 'Interactive data unavailable; all saved values remain in the table.';
  });
})();
