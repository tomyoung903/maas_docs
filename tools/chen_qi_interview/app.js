(function () {
  'use strict';
  function boot() {
    var presetQuestions = Array.isArray(window.INTERVIEW_QUESTIONS) ? window.INTERVIEW_QUESTIONS.slice() : [];
    var questions = presetQuestions.slice();
    var dialog = document.getElementById('question-dialog');
    var toggle = document.getElementById('toggle-pins');
    var closeButton = document.getElementById('close-dialog');
    var answerToggle = document.getElementById('answers-toggle');
    var answerPanel = document.getElementById('expected-answer');
    var previous = document.getElementById('prev-question');
    var next = document.getElementById('next-question');
    var addQuestionButton = document.getElementById('add-question');
    var editQuestionButton = document.getElementById('edit-question');
    var editor = document.getElementById('question-editor');
    var editorForm = document.getElementById('question-editor-form');
    var projectSelect = document.getElementById('editor-project');
    var paragraphSelect = document.getElementById('editor-paragraph');
    var questionInput = document.getElementById('editor-question');
    var answerInput = document.getElementById('editor-answer');
    var storageKey = 'chen-qi-interview:custom-questions:v1';
    var firstCustomNumber = Math.max.apply(null, presetQuestions.map(function (q) { return q.number || 0; }).concat([0])) + 1;
    var customState = { version: 2, nextNumber: firstCustomNumber, questions: [] };
    var unsavedIds = new Set();
    var editingId = null;
    var editorReturnId = null;
    var paragraphBlocks = [];
    var projectLabels = Array.from(document.querySelectorAll('.project .section-heading')).map(function (node) { return node.textContent.trim(); });
    var pins = Array.from(document.querySelectorAll('.question-pin'));
    var currentIndex = -1;
    var opener = null;
    var pinsVisible = !toggle || toggle.getAttribute('aria-pressed') !== 'false';
    if (!dialog) return;

    document.querySelectorAll('.project').forEach(function (projectNode, projectIndex) {
      projectNode.querySelectorAll('.experience > li').forEach(function (node, blockIndex) {
        var copy = node.cloneNode(true);
        copy.querySelectorAll('.question-pin').forEach(function (pin) { pin.remove(); });
        paragraphBlocks.push({ project: projectIndex + 1, blockIndex: blockIndex, anchorId: node.dataset.anchor, node: node, text: copy.textContent.trim() });
      });
    });

    function put(id, value) {
      var el = document.getElementById(id);
      if (el) el.textContent = value == null ? '' : String(value);
    }
    function visibleFocusables() {
      return Array.from(dialog.querySelectorAll('button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])')).filter(function (el) {
        return !el.hidden && !el.closest('[hidden]') && el.getClientRects().length;
      });
    }
    function findPin(id) {
      return pins.find(function (pin) { return pin.dataset.question === id; });
    }
    function findAnchor(id) {
      var custom = questions.find(function (question) { return question.id === id && question.custom; });
      if (custom) {
        var block = findBlockByAnchor(custom.anchorId);
        if (block) return block.node;
      }
      return Array.from(document.querySelectorAll('[data-anchor]')).find(function (node) { return node.dataset.anchor === id; }) || (findPin(id) && findPin(id).closest('[data-anchor]'));
    }
    function findBlock(project, blockIndex) {
      return paragraphBlocks.find(function (block) { return block.project === project && block.blockIndex === blockIndex; });
    }
    function findBlockByAnchor(anchorId) {
      return paragraphBlocks.find(function (block) { return typeof anchorId === 'string' && block.anchorId === anchorId; });
    }
    function syncDialogState() {
      document.body.classList.toggle('dialog-open', Boolean(dialog.open || (editor && editor.open)));
    }
    function clearHighlight() {
      document.querySelectorAll('.active-anchor').forEach(function (node) { node.classList.remove('active-anchor'); });
      pins.forEach(function (pin) { pin.setAttribute('aria-expanded', 'false'); });
    }
    function setAnswers(expanded) {
      if (answerToggle) {
        answerToggle.setAttribute('aria-expanded', String(expanded));
        answerToggle.setAttribute('aria-controls', 'expected-answer');
        var label = answerToggle.querySelector('[data-answer-label]');
        if (label) label.textContent = expanded ? '收起参考答案' : '展开参考答案';
        else answerToggle.textContent = expanded ? '收起参考答案' : '展开参考答案';
      }
      if (answerPanel) answerPanel.hidden = !expanded;
    }
    function renderAnswers(value) {
      if (!answerPanel) return;
      var entries = Array.isArray(value) ? value : (value ? [value] : []);
      var list = document.getElementById('answer-checkpoints');
      if (!list) {
        list = /^(UL|OL)$/.test(answerPanel.tagName) ? answerPanel : document.createElement('ul');
        if (list !== answerPanel) { list.id = 'answer-checkpoints'; answerPanel.prepend(list); }
      }
      list.replaceChildren();
      entries.forEach(function (entry) {
        var item = document.createElement('li');
        item.textContent = typeof entry === 'string' ? entry : (entry.text || entry.label || String(entry));
        list.appendChild(item);
      });
    }
    function renderSources(sources, targetId) {
      var target = document.getElementById(targetId || 'question-sources');
      if (!target) return;
      target.replaceChildren();
      (Array.isArray(sources) ? sources : []).forEach(function (source) {
        var url = typeof source === 'string' ? source : source.url;
        if (!url) return;
        try { if (!/^https?:$/.test(new URL(url, document.baseURI).protocol)) return; } catch (_) { return; }
        var link = document.createElement('a');
        link.href = url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = typeof source === 'string' ? new URL(url, document.baseURI).hostname : (source.label || source.title || new URL(url, document.baseURI).hostname);
        if (/^(UL|OL)$/.test(target.tagName)) {
          var item = document.createElement('li');
          item.appendChild(link);
          target.appendChild(item);
        } else target.appendChild(link);
      });
    }
    function render(index) {
      var question = questions[index];
      if (!question) return;
      currentIndex = index;
      put('question-index', '问题 ' + question.number + ' · 第 ' + (index + 1) + ' / ' + questions.length + ' 题');
      put('question-project', question.projectLabel || ('项目 ' + question.project));
      if (question.custom) put('question-project', '自定义 · ' + (projectLabels[question.project - 1] || ('项目 ' + question.project)));
      put('question-title', question.title);
      put('question-text', question.question);
      var anchor = findAnchor(question.id);
      var quote = question.claim || question.anchorText || question.anchor;
      if (!quote || quote === question.id) {
        if (anchor) {
          var copy = anchor.cloneNode(true);
          copy.querySelectorAll('.question-pin').forEach(function (pin) { pin.remove(); });
          quote = copy.textContent.trim();
        }
      }
      put('source-claim', quote || '');
      renderAnswers(question.expectedAnswer);
      if (answerToggle) answerToggle.hidden = !question.expectedAnswer || question.expectedAnswer.length === 0;
      put('judgement', question.judgement);
      put('evidence', question.evidence);
      put('followup', question.followUp);
      [['judgement-block', question.judgement], ['evidence-block', question.evidence], ['followup-block', question.followUp]].forEach(function (entry) {
        var section = document.getElementById(entry[0]);
        if (section) section.hidden = !entry[1];
      });
      if (editQuestionButton) editQuestionButton.hidden = !question.custom;
      renderSources(question.sources);
      renderSources(question.studySources, 'question-study-sources');
      put('interviewer-hint', question.interviewerHint || '');
      document.getElementById('interviewer-hint-block').hidden = !question.interviewerHint;
      document.getElementById('study-sources-block').hidden = !question.studySources || !question.studySources.length;
      document.getElementById('technical-sources-block').hidden = !question.sources || !question.sources.length;
      setAnswers(false);
      clearHighlight();
      if (anchor) anchor.classList.add('active-anchor');
      var pin = findPin(question.id);
      if (pin) pin.setAttribute('aria-expanded', 'true');
      if (previous) previous.disabled = index === 0;
      if (next) next.disabled = index === questions.length - 1;
      dialog.scrollTop = 0;
    }
    function openQuestion(id, origin) {
      if (!pinsVisible) return;
      var index = questions.findIndex(function (question) { return question.id === id; });
      if (index < 0) return;
      opener = origin || findPin(id) || document.activeElement;
      render(index);
      if (!dialog.open) {
        if (typeof dialog.showModal === 'function') dialog.showModal();
        else dialog.setAttribute('open', '');
      }
      document.body.classList.add('dialog-open');
      if (closeButton) closeButton.focus();
    }
    function finishClose() {
      clearHighlight();
      syncDialogState();
      var returnTarget = pinsVisible && opener && document.contains(opener) ? opener : toggle;
      if (returnTarget && !(editor && editor.open)) returnTarget.focus({ preventScroll: true });
    }
    function closeDialog() {
      if (!dialog.open) return;
      if (typeof dialog.close === 'function') dialog.close();
      else { dialog.removeAttribute('open'); finishClose(); }
    }
    document.addEventListener('click', function (event) {
      var pin = event.target.closest && event.target.closest('.question-pin');
      if (!pin) return;
      event.preventDefault();
      openQuestion(pin.dataset.question, pin);
    });
    if (closeButton) closeButton.addEventListener('click', function (event) { event.preventDefault(); closeDialog(); });
    if (answerToggle) answerToggle.addEventListener('click', function (event) {
      event.preventDefault();
      setAnswers(answerToggle.getAttribute('aria-expanded') !== 'true');
    });
    if (previous) previous.addEventListener('click', function (event) { event.preventDefault(); if (currentIndex > 0) { render(currentIndex - 1); if (previous.disabled && next) next.focus(); } });
    if (next) next.addEventListener('click', function (event) { event.preventDefault(); if (currentIndex < questions.length - 1) { render(currentIndex + 1); if (next.disabled && previous) previous.focus(); } });
    dialog.addEventListener('close', finishClose);
    dialog.addEventListener('cancel', function (event) { event.preventDefault(); closeDialog(); });
    dialog.addEventListener('click', function (event) {
      if (event.target !== dialog) return;
      var bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) closeDialog();
    });
    dialog.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') { event.preventDefault(); closeDialog(); return; }
      if (event.key !== 'Tab') return;
      var focusable = visibleFocusables();
      if (!focusable.length) { event.preventDefault(); return; }
      var first = focusable[0], last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    function updatePinVisibility() {
      document.body.classList.toggle('pins-hidden', !pinsVisible);
      pins.forEach(function (pin) { pin.hidden = !pinsVisible; });
      if (toggle) {
        toggle.setAttribute('aria-pressed', String(pinsVisible));
        toggle.textContent = pinsVisible ? '隐藏问题标记' : '显示问题标记';
      }
      put('pin-count', questions.length + ' 个问题 · ' + paragraphBlocks.length + ' 处简历节选');
    }
    if (toggle) toggle.addEventListener('click', function (event) {
      event.preventDefault();
      pinsVisible = !pinsVisible;
      if (!pinsVisible) closeDialog();
      updatePinVisibility();
    });
    function warnStorage(message) {
      var warning = document.getElementById('custom-storage-warning');
      if (warning) { warning.textContent = message; warning.hidden = false; }
    }
    function normalizeCustomNumbers(state) {
      var used = new Set(presetQuestions.map(function (question) { return question.number; }));
      var ordered = state.questions.slice().sort(function (a, b) {
        return a.number - b.number || a.id.localeCompare(b.id);
      });
      var cursor = Math.max.apply(null, ordered.map(function (question) { return question.number + 1; }).concat([firstCustomNumber, state.nextNumber]));
      var collisions = [];
      ordered.forEach(function (question) {
        if (question.number < firstCustomNumber || used.has(question.number)) collisions.push(question);
        else used.add(question.number);
      });
      collisions.forEach(function (question) {
        while (used.has(cursor)) cursor++;
        question.number = cursor++;
        used.add(question.number);
      });
      var previousNext = state.nextNumber;
      state.nextNumber = Math.max.apply(null, ordered.map(function (question) { return question.number + 1; }).concat([cursor, firstCustomNumber]));
      return collisions.length > 0 || state.nextNumber !== previousNext;
    }
    function readCustomState() {
      var result = { version: 2, nextNumber: firstCustomNumber, questions: [] };
      try {
        var raw = window.localStorage.getItem(storageKey);
        if (!raw) return result;
        var stored = JSON.parse(raw);
        if ((stored.version !== 1 && stored.version !== 2) || !Array.isArray(stored.questions)) return result;
        // Version 1 referred to the original three paragraphs by position.
        // Version 2 uses the stable excerpt ID while retaining this storage key.
        var legacyAnchors = {
          1: ['moe-topology', 'moe-precision', 'moe-kernel'],
          2: ['kv-format', 'kv-capacity', 'kv-chain']
        };
        var ids = new Set();
        stored.questions.forEach(function (item) {
          if (!item || typeof item.id !== 'string' || !/^custom-[a-z0-9-]+$/i.test(item.id) || ids.has(item.id)) return;
          // Preserve existing custom questions if a later preset takes their number.
          if (!Number.isSafeInteger(item.number) || item.number < 1) return;
          var anchorId = stored.version === 1
            ? (legacyAnchors[item.project] || [])[item.blockIndex]
            : item.anchorId;
          var block = findBlockByAnchor(anchorId);
          if (!block || typeof item.question !== 'string' || !item.question.trim()) return;
          ids.add(item.id);
          var text = item.question.trim().slice(0, 5000);
          result.questions.push({
            id: item.id, number: item.number, project: block.project, blockIndex: block.blockIndex, anchorId: block.anchorId,
            question: text, title: text.split(/\r?\n/)[0].slice(0, 48), anchor: block.text,
            expectedAnswer: Array.isArray(item.expectedAnswer) ? item.expectedAnswer.filter(function (value) { return typeof value === 'string'; }) : [],
            custom: true
          });
        });
        result.nextNumber = Math.max.apply(null, result.questions.map(function (item) { return item.number + 1; }).concat([firstCustomNumber, Number.isInteger(stored.nextNumber) ? stored.nextNumber : firstCustomNumber]));
        if (normalizeCustomNumbers(result) || stored.version === 1) {
          try { window.localStorage.setItem(storageKey, JSON.stringify(result)); }
          catch (_) { warnStorage('自定义问题已恢复，但浏览器阻止了保存段落关联或编号。刷新后会重新恢复。'); }
        }
      } catch (_) {
        warnStorage('浏览器暂时无法读取本地问题。新问题可在当前页面使用，但保存状态需要确认。');
      }
      return result;
    }
    function mergeUnsavedState(latest) {
      customState.questions.forEach(function (item) {
        var index = latest.questions.findIndex(function (stored) { return stored.id === item.id; });
        if (index < 0) latest.questions.push(item);
        else if (unsavedIds.has(item.id)) latest.questions[index] = item;
      });
      latest.nextNumber = Math.max(latest.nextNumber, customState.nextNumber);
      normalizeCustomNumbers(latest);
      return latest;
    }
    function restoreCustomPins() {
      document.querySelectorAll('.custom-question-anchor').forEach(function (node) { node.remove(); });
      customState.questions.sort(function (a, b) { return a.number - b.number; });
      questions = presetQuestions.concat(customState.questions);
      customState.questions.forEach(function (question) {
        var block = findBlockByAnchor(question.anchorId);
        if (!block) return;
        var wrapper = document.createElement('span');
        wrapper.className = 'claim-anchor custom-question-anchor';
        wrapper.dataset.anchor = question.id;
        var pin = document.createElement('button');
        pin.className = 'question-pin custom-question-pin';
        pin.type = 'button'; pin.dataset.question = question.id;
        pin.textContent = String(question.number);
        pin.setAttribute('aria-label', '问题 ' + question.number + '：' + question.title);
        pin.setAttribute('aria-haspopup', 'dialog'); pin.setAttribute('aria-controls', 'question-dialog');
        wrapper.appendChild(pin); block.node.appendChild(wrapper);
      });
      pins = Array.from(document.querySelectorAll('.question-pin'));
      pins.forEach(function (pin) { pin.setAttribute('aria-expanded', 'false'); });
      updatePinVisibility();
    }
    function updateParagraphOptions(selectedIndex) {
      if (!projectSelect || !paragraphSelect) return;
      var project = Number(projectSelect.value);
      paragraphSelect.replaceChildren();
      paragraphBlocks.filter(function (block) { return block.project === project; }).forEach(function (block) {
        var option = document.createElement('option');
        option.value = String(block.blockIndex);
        option.textContent = '第 ' + (block.blockIndex + 1) + ' 段 · ' + block.text.slice(0, 54) + (block.text.length > 54 ? '…' : '');
        paragraphSelect.appendChild(option);
      });
      if (selectedIndex != null) paragraphSelect.value = String(selectedIndex);
      updateEditorQuote();
    }
    function updateEditorQuote() {
      var block = findBlock(Number(projectSelect.value), Number(paragraphSelect.value));
      put('editor-quote', block ? block.text : '');
    }
    function openEditor(question) {
      if (!editor || !editorForm) return;
      editingId = question ? question.id : null;
      editorReturnId = editingId;
      closeDialog();
      editorForm.reset();
      questionInput.setCustomValidity('');
      put('question-editor-title', question ? '编辑问题 ' + question.number : '添加问题');
      projectSelect.value = String(question ? question.project : 1);
      updateParagraphOptions(question ? question.blockIndex : 0);
      questionInput.value = question ? question.question : '';
      answerInput.value = question ? question.expectedAnswer.join('\n\n') : '';
      if (typeof editor.showModal === 'function') editor.showModal(); else editor.setAttribute('open', '');
      syncDialogState();
      questionInput.focus();
    }
    function dismissEditor(restoreQuestion) {
      var returnId = editorReturnId;
      editorReturnId = null;
      if (typeof editor.close === 'function') editor.close(); else editor.removeAttribute('open');
      syncDialogState();
      if (restoreQuestion && returnId) openQuestion(returnId, findPin(returnId));
      else if (addQuestionButton && !dialog.open) addQuestionButton.focus();
    }
    if (addQuestionButton) addQuestionButton.addEventListener('click', function () { openEditor(null); });
    if (editQuestionButton) editQuestionButton.addEventListener('click', function () { openEditor(questions[currentIndex]); });
    if (editor && editorForm && projectSelect && paragraphSelect && questionInput && answerInput) {
      projectSelect.addEventListener('change', function () { updateParagraphOptions(0); });
      paragraphSelect.addEventListener('change', updateEditorQuote);
      questionInput.addEventListener('input', function () { questionInput.setCustomValidity(''); });
      ['editor-close', 'editor-cancel'].forEach(function (id) {
        var button = document.getElementById(id);
        if (button) button.addEventListener('click', function () { dismissEditor(true); });
      });
      editor.addEventListener('cancel', function (event) { event.preventDefault(); dismissEditor(true); });
      editor.addEventListener('close', syncDialogState);
      editor.addEventListener('click', function (event) {
        if (event.target !== editor) return;
        var bounds = editor.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dismissEditor(true);
      });
      editorForm.addEventListener('submit', function (event) {
        event.preventDefault();
        var text = questionInput.value.trim();
        if (!text) { questionInput.setCustomValidity('请输入问题。'); questionInput.reportValidity(); return; }
        var block = findBlock(Number(projectSelect.value), Number(paragraphSelect.value));
        if (!block) return;
        customState = mergeUnsavedState(readCustomState());
        var old = customState.questions.find(function (item) { return item.id === editingId; });
        var id = old ? old.id : 'custom-' + (window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : Date.now().toString(36) + '-' + Math.random().toString(36).slice(2));
        var question = { id: id, number: old ? old.number : customState.nextNumber++, project: block.project, blockIndex: block.blockIndex, anchorId: block.anchorId, title: text.split(/\r?\n/)[0].slice(0, 48), question: text, anchor: block.text, expectedAnswer: answerInput.value.trim() ? answerInput.value.trim().split(/\n{2,}/) : [], custom: true };
        customState.questions = customState.questions.filter(function (item) { return item.id !== id; }).concat([question]);
        unsavedIds.add(id);
        try {
          window.localStorage.setItem(storageKey, JSON.stringify(customState));
          unsavedIds.clear();
          var warning = document.getElementById('custom-storage-warning');
          if (warning) warning.hidden = true;
        } catch (_) {
          warnStorage('问题已添加，但浏览器阻止了本地保存。刷新页面后，新改动可能丢失。');
        }
        pinsVisible = true;
        restoreCustomPins();
        dismissEditor(false);
        openQuestion(id, findPin(id));
      });
    }
    window.addEventListener('storage', function (event) {
      if (event.key !== storageKey || (editor && editor.open)) return;
      var openId = dialog.open && questions[currentIndex] ? questions[currentIndex].id : null;
      customState = mergeUnsavedState(readCustomState()); restoreCustomPins();
      if (openId) {
        var index = questions.findIndex(function (question) { return question.id === openId; });
        if (index >= 0) render(index); else closeDialog();
      }
    });
    customState = readCustomState();
    restoreCustomPins();
    setAnswers(false);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
