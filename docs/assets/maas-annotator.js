/*
 * MaaS Docs browser-local page annotator.
 * Icons use Lucide v1.38.0 paths under the ISC license.
 */
(function () {
  "use strict";

  if (window.__maasAnnotatorLoaded) return;
  window.__maasAnnotatorLoaded = true;

  var loader = document.currentScript;
  var configuredPageKey = loader && loader.dataset.pageKey;

  function start() {
    var SVG_NS = "http://www.w3.org/2000/svg";
    var PAGE_KEY = configuredPageKey || normalizePath(location.pathname);
    var STORAGE_KEY = "maas-docs:annotations:v1:" + PAGE_KEY;
    var PREFS_KEY = "maas-docs:annotator-prefs:v1";
    var MAX_HISTORY = 50;
    var DEFAULT_COLOR = "#d94b3d";
    var COLORS = ["#d94b3d", "#f2b84b", "#0f8278", "#2f6feb", "#20262d"];
    var WIDTHS = [2, 4, 7];
    var TOOLS = ["pointer", "pen", "highlighter", "arrow", "text", "eraser"];
    var TEXT_SIZES = { 2: 16, 4: 22, 7: 30 };

    var icons = {
      pencil: '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/><path d="m15 5 4 4"/>',
      highlighter: '<path d="m9 11-6 6v3h9l3-3"/><path d="m22 12-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4"/>',
      arrow: '<path d="M13 5H19V11"/><path d="M19 5L5 19"/>',
      text: '<path d="M4 7V4h16v3"/><path d="M9 20h6"/><path d="M12 4v16"/>',
      eraser: '<path d="M21 21H8a2 2 0 0 1-1.42-.587l-3.994-3.999a2 2 0 0 1 0-2.828l10-10a2 2 0 0 1 2.829 0l5.999 6a2 2 0 0 1 0 2.828L12.834 21"/><path d="m5.082 11.09 8.828 8.828"/>',
      pointer: '<path d="M12.586 12.586 19 19"/><path d="M3.5 2.5 10 18l2.5-5.5L18 10Z"/>',
      undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5 5.5 5.5 0 0 1-5.5 5.5H11"/>',
      redo: '<path d="m15 14 5-5-5-5"/><path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5 5.5 5.5 0 0 0 9.5 20H13"/>',
      eye: '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
      eyeOff: '<path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49"/><path d="M14.084 14.158a3 3 0 0 1-4.242-4.242"/><path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"/><path d="m2 2 20 20"/>',
      trash: '<path d="M10 11v6"/><path d="M14 11v6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
      download: '<path d="M12 15V3"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/>',
      upload: '<path d="M12 3v12"/><path d="m17 8-5-5-5 5"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>',
      close: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'
    };

    var state = {
      open: false,
      visible: true,
      tool: "pen",
      color: DEFAULT_COLOR,
      width: 4,
      items: [],
      undo: [],
      redo: [],
      draft: null,
      textDraft: null,
      storageOkay: true
    };

    loadPreferences();
    loadPageState();

    var overlay = createSvg("svg");
    overlay.setAttribute("data-maas-annotation-layer", "");
    overlay.setAttribute("aria-hidden", "true");
    setStyles(overlay, {
      position: "absolute",
      top: "0",
      left: "0",
      zIndex: "2147483000",
      overflow: "visible",
      pointerEvents: "none",
      touchAction: "none",
      display: state.visible ? "block" : "none"
    });

    var drawingGroup = createSvg("g");
    overlay.appendChild(drawingGroup);
    document.body.appendChild(overlay);

    var textEditorHost = document.createElement("div");
    textEditorHost.setAttribute("data-maas-text-editor", "");
    textEditorHost.setAttribute("aria-hidden", "true");
    setStyles(textEditorHost, {
      all: "initial",
      position: "fixed",
      zIndex: "2147483647",
      width: "min(280px, calc(100vw - 24px))",
      display: "none"
    });
    document.body.appendChild(textEditorHost);

    var textEditorShadow = textEditorHost.attachShadow({ mode: "open" });
    textEditorShadow.innerHTML = buildTextEditor();
    var textInput = textEditorShadow.getElementById("text-input");

    var host = document.createElement("div");
    host.id = "maas-annotator";
    host.setAttribute("data-maas-annotator-ui", "");
    setStyles(host, {
      all: "initial",
      position: "fixed",
      right: "16px",
      bottom: "16px",
      zIndex: "2147483500"
    });
    document.body.appendChild(host);

    var shadow = host.attachShadow({ mode: "open" });
    shadow.innerHTML = buildUi();

    var panel = shadow.getElementById("panel");
    var launcher = shadow.getElementById("launcher");
    var status = shadow.getElementById("status");
    var importInput = shadow.getElementById("import-input");

    bindUi();
    bindTextEditor();
    bindDrawing();
    bindKeyboard();
    updateOverlaySize();
    render();
    refreshUi();

    var resizeFrame = 0;
    var resizeObserver = typeof ResizeObserver === "function"
      ? new ResizeObserver(scheduleOverlaySize)
      : null;
    if (resizeObserver) {
      resizeObserver.observe(document.documentElement);
      resizeObserver.observe(document.body);
    }
    window.addEventListener("resize", scheduleOverlaySize, { passive: true });
    window.addEventListener("load", scheduleOverlaySize, { once: true });

    window.__maasAnnotator = {
      pageKey: PAGE_KEY,
      storageKey: STORAGE_KEY,
      getState: function () {
        return clone({
          pageKey: PAGE_KEY,
          open: state.open,
          visible: state.visible,
          tool: state.tool,
          color: state.color,
          width: state.width,
          items: state.items
        });
      },
      setOpen: setOpen,
      setTool: setTool,
      clear: clearAll,
      exportData: exportData
    };

    function normalizePath(pathname) {
      var path = pathname || "/";
      path = path.replace(/^\/maas_docs(?=\/|$)/, "") || "/";
      if (path.endsWith("/index.html")) path = path.slice(0, -10) || "/";
      return path;
    }

    function svgIcon(name) {
      return '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' + icons[name] + "</svg>";
    }

    function buildUi() {
      var colorButtons = COLORS.map(function (color) {
        return '<button class="swatch" type="button" role="radio" data-color="' + color + '" aria-label="Color ' + color + '" title="Color ' + color + '" style="--swatch:' + color + '"></button>';
      }).join("");
      var widthButtons = WIDTHS.map(function (width, index) {
        var strokeLabels = ["Thin stroke", "Medium stroke", "Thick stroke"];
        var textLabels = ["Small text", "Medium text", "Large text"];
        var sampleSizes = [12, 16, 20];
        return '<button class="icon-button width-button" type="button" data-width="' + width + '" data-stroke-label="' + strokeLabels[index] + '" data-text-label="' + textLabels[index] + '" aria-label="' + strokeLabels[index] + '" title="' + strokeLabels[index] + '"><span class="stroke-size" style="--dot:' + (width + 3) + 'px"></span><span class="text-size" style="--text-size:' + sampleSizes[index] + 'px">T</span></button>';
      }).join("");

      return '<style>' +
        ':host{color:#18242c;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:14px;letter-spacing:0}' +
        '*{box-sizing:border-box;letter-spacing:0}' +
        '[hidden]{display:none!important}' +
        '.shell{display:flex;flex-direction:column;align-items:flex-end;gap:8px}' +
        '.panel{width:344px;border:1px solid #cbd6dc;border-radius:8px;background:#fff;padding:10px;box-shadow:0 10px 28px rgba(20,33,43,.18)}' +
        '.row{display:flex;align-items:center;gap:6px;min-width:0}' +
        '.row+.row{margin-top:8px;padding-top:8px;border-top:1px solid #e3e8eb}' +
        '.row.tools{flex-wrap:wrap}' +
        '.row.options{justify-content:space-between}' +
        '.group{display:flex;align-items:center;gap:5px}' +
        'button{margin:0;border:1px solid #c8d2d8;border-radius:7px;background:#fff;color:#24323b;font:inherit;cursor:pointer}' +
        'button:hover{border-color:#82949f;background:#f6f9fa}' +
        'button:focus-visible{outline:3px solid rgba(15,130,120,.28);outline-offset:1px}' +
        'button[disabled]{cursor:not-allowed;opacity:.38}' +
        '.icon-button,.launcher{display:grid;width:38px;height:38px;place-items:center;padding:0;flex:0 0 38px}' +
        '.icon-button svg,.launcher svg{width:19px;height:19px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}' +
        '.icon-button.is-active{border-color:#0f8278;background:#e7f3f1;color:#0b665f}' +
        '.launcher{width:44px;height:44px;flex-basis:44px;border-color:#0c6f67;background:#0f8278;color:#fff;box-shadow:0 6px 18px rgba(15,70,66,.23)}' +
        '.launcher:hover{border-color:#095c56;background:#0c7169}' +
        '.swatch{position:relative;width:26px;height:26px;padding:0;border-color:#b9c5cc;background:var(--swatch)}' +
        '.swatch::after{content:"";position:absolute;inset:4px;border:2px solid rgba(255,255,255,.85);border-radius:4px;opacity:0}' +
        '.swatch.is-active{outline:2px solid #26343d;outline-offset:2px}' +
        '.swatch.is-active::after{opacity:1}' +
        '.width-button .stroke-size{display:block;width:var(--dot);height:var(--dot);border-radius:50%;background:#26343d}' +
        '.width-button .text-size{display:none;color:#26343d;font-weight:750;font-size:var(--text-size);line-height:1}' +
        '.width-button.is-text-mode .stroke-size{display:none}' +
        '.width-button.is-text-mode .text-size{display:block}' +
        '.actions{flex-wrap:wrap}' +
        '.status{margin-left:auto;min-width:0;overflow:hidden;color:#65737c;font-size:12px;line-height:1.2;text-align:right;text-overflow:ellipsis;white-space:nowrap}' +
        '@media(max-width:480px){.panel{width:calc(100vw - 24px);max-width:344px}.icon-button{width:36px;height:36px;flex-basis:36px}.row{gap:5px}}' +
        '@media(print){.shell{display:none}}' +
        '</style>' +
        '<div class="shell">' +
          '<div class="panel" id="panel" role="toolbar" aria-label="Page annotation tools" hidden>' +
            '<div class="row tools">' +
              toolButton("pointer", "pointer", "Use page") +
              toolButton("pen", "pencil", "Pen") +
              toolButton("highlighter", "highlighter", "Highlighter") +
              toolButton("arrow", "arrow", "Arrow") +
              toolButton("text", "text", "Add text") +
              toolButton("eraser", "eraser", "Erase a mark") +
              '<button class="icon-button" type="button" data-action="visibility" aria-label="Hide annotations" title="Hide annotations">' + svgIcon("eye") + '</button>' +
            '</div>' +
            '<div class="row options"><div class="group colors" role="radiogroup" aria-label="Annotation color">' + colorButtons + '</div><div class="group widths" role="group" aria-label="Stroke width">' + widthButtons + '</div></div>' +
            '<div class="row actions">' +
              actionButton("undo", "undo", "Undo") +
              actionButton("redo", "redo", "Redo") +
              actionButton("export", "download", "Export annotations") +
              actionButton("import", "upload", "Import annotations") +
              actionButton("clear", "trash", "Clear this page") +
              '<span class="status" id="status" role="status" aria-live="polite"></span>' +
            '</div>' +
          '</div>' +
          '<button class="launcher" id="launcher" type="button" aria-label="Open annotation tools" title="Open annotation tools" aria-pressed="false">' + svgIcon("pencil") + '</button>' +
          '<input id="import-input" type="file" accept="application/json,.json" hidden>' +
        '</div>';
    }

    function buildTextEditor() {
      return '<style>' +
        ':host{color:#18242c;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:13px}' +
        '*{box-sizing:border-box}' +
        '.editor{width:100%;padding:9px;border:1px solid #82949f;border-radius:8px;background:#fff;box-shadow:0 10px 28px rgba(20,33,43,.24)}' +
        'textarea{display:block;width:100%;min-height:76px;max-height:220px;resize:none;margin:0;padding:8px 9px;border:1px solid #b8c5cc;border-radius:6px;color:#20262d;background:#fff;font:600 18px/1.3 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;overflow:auto}' +
        'textarea:focus{outline:3px solid rgba(15,130,120,.24);border-color:#0f8278}' +
        '.footer{display:flex;align-items:center;gap:6px;margin-top:8px}' +
        '.hint{min-width:0;margin-right:auto;color:#65737c;font-size:11px;line-height:1.25}' +
        'button{min-height:30px;margin:0;padding:4px 9px;border:1px solid #b8c5cc;border-radius:6px;color:#24323b;background:#fff;font:650 12px/1 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;cursor:pointer}' +
        'button:hover{border-color:#82949f;background:#f6f9fa}' +
        'button:focus-visible{outline:3px solid rgba(15,130,120,.24);outline-offset:1px}' +
        'button.primary{border-color:#0c6f67;color:#fff;background:#0f8278}' +
        'button.primary:hover{background:#0c7169}' +
        '</style>' +
        '<div class="editor" role="dialog" aria-label="Add text annotation">' +
          '<textarea id="text-input" maxlength="5000" placeholder="Type text…" aria-label="Annotation text"></textarea>' +
          '<div class="footer"><span class="hint">Ctrl/⌘+Enter to add · Esc to cancel</span><button type="button" data-editor-action="cancel">Cancel</button><button class="primary" type="button" data-editor-action="save">Add text</button></div>' +
        '</div>';
    }

    function toolButton(tool, iconName, label) {
      return '<button class="icon-button" type="button" data-tool="' + tool + '" aria-label="' + label + '" title="' + label + '" aria-pressed="false">' + svgIcon(iconName) + '</button>';
    }

    function actionButton(action, iconName, label) {
      return '<button class="icon-button" type="button" data-action="' + action + '" aria-label="' + label + '" title="' + label + '">' + svgIcon(iconName) + '</button>';
    }

    function bindUi() {
      launcher.addEventListener("click", function () {
        setOpen(!state.open);
      });

      shadow.addEventListener("click", function (event) {
        var tool = event.target.closest("button[data-tool]");
        if (tool) {
          setTool(tool.dataset.tool);
          return;
        }

        var color = event.target.closest("button[data-color]");
        if (color) {
          state.color = color.dataset.color;
          savePreferences();
          refreshUi();
          return;
        }

        var width = event.target.closest("button[data-width]");
        if (width) {
          state.width = Number(width.dataset.width);
          savePreferences();
          refreshUi();
          return;
        }

        var action = event.target.closest("button[data-action]");
        if (!action) return;
        if (state.textDraft) commitTextEditing();
        if (action.dataset.action === "undo") undo();
        if (action.dataset.action === "redo") redo();
        if (action.dataset.action === "visibility") toggleVisibility();
        if (action.dataset.action === "export") downloadExport();
        if (action.dataset.action === "import") importInput.click();
        if (action.dataset.action === "clear") clearAll();
      });

      importInput.addEventListener("change", function () {
        var file = importInput.files && importInput.files[0];
        importInput.value = "";
        if (!file) return;
        file.text().then(importJson).catch(function () {
          setStatus("Import failed");
        });
      });
    }

    function bindTextEditor() {
      textEditorShadow.addEventListener("click", function (event) {
        var action = event.target.closest("button[data-editor-action]");
        if (!action) return;
        if (action.dataset.editorAction === "save") commitTextEditing();
        if (action.dataset.editorAction === "cancel") cancelTextEditing();
      });

      textInput.addEventListener("input", resizeTextInput);
      textInput.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
          event.preventDefault();
          cancelTextEditing();
          return;
        }
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
          event.preventDefault();
          commitTextEditing();
        }
      });
      textInput.addEventListener("blur", function () {
        setTimeout(function () {
          if (state.textDraft && !textEditorShadow.activeElement) commitTextEditing();
        }, 0);
      });
    }

    function bindKeyboard() {
      document.addEventListener("keydown", function (event) {
        var target = event.target;
        var typing = Boolean(state.textDraft) || (target && ((target.matches && target.matches("input,textarea,select")) || target.isContentEditable));
        if (event.altKey && !event.ctrlKey && !event.metaKey && event.key.toLowerCase() === "a" && !typing) {
          event.preventDefault();
          setOpen(!state.open);
          return;
        }
        if (!state.open || typing) return;
        if (event.key === "Escape") {
          event.preventDefault();
          setOpen(false);
          return;
        }
        if ((event.ctrlKey || event.metaKey) && !event.shiftKey && event.key.toLowerCase() === "z") {
          event.preventDefault();
          undo();
          return;
        }
        if ((event.ctrlKey || event.metaKey) && (event.key.toLowerCase() === "y" || (event.shiftKey && event.key.toLowerCase() === "z"))) {
          event.preventDefault();
          redo();
        }
      }, true);
    }

    function bindDrawing() {
      overlay.addEventListener("pointerdown", function (event) {
        if (!state.open || state.tool === "pointer") return;
        if (event.pointerType === "mouse" && event.button !== 0) return;

        if (state.tool === "eraser") {
          var target = event.target.closest && event.target.closest("[data-annotation-id]");
          if (target) removeItem(target.getAttribute("data-annotation-id"));
          return;
        }

        if (state.tool === "text") {
          event.preventDefault();
          beginTextEditing(eventPoint(event));
          return;
        }

        event.preventDefault();
        overlay.setPointerCapture(event.pointerId);
        var point = eventPoint(event);
        var before = snapshotItems();
        var item;
        if (state.tool === "arrow") {
          item = {
            id: newId(),
            type: "arrow",
            x1: point[0],
            y1: point[1],
            x2: point[0],
            y2: point[1],
            color: state.color,
            width: state.width,
            opacity: 1
          };
        } else {
          item = {
            id: newId(),
            type: state.tool === "highlighter" ? "highlight" : "path",
            points: [point],
            color: state.color,
            width: state.tool === "highlighter" ? Math.max(14, state.width * 4) : state.width,
            opacity: state.tool === "highlighter" ? 0.3 : 1
          };
        }
        state.draft = { pointerId: event.pointerId, item: item, before: before };
        render();
      });

      overlay.addEventListener("pointermove", function (event) {
        if (!state.draft || state.draft.pointerId !== event.pointerId) return;
        event.preventDefault();
        var point = eventPoint(event);
        var item = state.draft.item;
        if (item.type === "arrow") {
          item.x2 = point[0];
          item.y2 = point[1];
        } else {
          var last = item.points[item.points.length - 1];
          if (Math.hypot(point[0] - last[0], point[1] - last[1]) >= 1.5) {
            item.points.push(point);
          }
        }
        render();
      });

      overlay.addEventListener("pointerup", finishDrawing);
      overlay.addEventListener("pointercancel", cancelDrawing);
    }

    function finishDrawing(event) {
      if (!state.draft || state.draft.pointerId !== event.pointerId) return;
      var draft = state.draft;
      state.draft = null;
      if (draft.item.type !== "arrow" && draft.item.points.length === 1) {
        draft.item.points.push([draft.item.points[0][0] + 0.1, draft.item.points[0][1] + 0.1]);
      }
      state.items.push(draft.item);
      pushUndo(draft.before);
      state.redo = [];
      persist();
      render();
      refreshUi();
      scheduleOverlaySize();
    }

    function cancelDrawing(event) {
      if (!state.draft || state.draft.pointerId !== event.pointerId) return;
      state.draft = null;
      render();
    }

    function eventPoint(event) {
      return [round(event.pageX), round(event.pageY)];
    }

    function render() {
      while (drawingGroup.firstChild) drawingGroup.removeChild(drawingGroup.firstChild);
      var items = state.draft ? state.items.concat([state.draft.item]) : state.items;
      items.forEach(renderItem);
      overlay.style.display = state.visible ? "block" : "none";
      updatePointerMode();
    }

    function renderItem(item) {
      var group = createSvg("g");
      group.setAttribute("data-annotation-id", item.id);
      group.style.pointerEvents = "none";

      if (item.type === "arrow") {
        var line = createSvg("line");
        line.setAttribute("x1", item.x1);
        line.setAttribute("y1", item.y1);
        line.setAttribute("x2", item.x2);
        line.setAttribute("y2", item.y2);
        setStroke(line, item);
        group.appendChild(line);

        var angle = Math.atan2(item.y2 - item.y1, item.x2 - item.x1);
        var length = Math.max(12, item.width * 4);
        var spread = Math.PI / 7;
        var ax = item.x2 - length * Math.cos(angle - spread);
        var ay = item.y2 - length * Math.sin(angle - spread);
        var bx = item.x2 - length * Math.cos(angle + spread);
        var by = item.y2 - length * Math.sin(angle + spread);
        var head = createSvg("polygon");
        head.setAttribute("points", item.x2 + "," + item.y2 + " " + round(ax) + "," + round(ay) + " " + round(bx) + "," + round(by));
        head.setAttribute("fill", item.color);
        head.setAttribute("opacity", item.opacity);
        group.appendChild(head);
      } else if (item.type === "text") {
        var text = createSvg("text");
        text.setAttribute("x", item.x);
        text.setAttribute("y", item.y);
        text.setAttribute("fill", item.color);
        text.setAttribute("opacity", item.opacity);
        text.setAttribute("font-size", item.fontSize);
        text.setAttribute("font-family", 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif');
        text.setAttribute("font-weight", "600");
        text.setAttribute("dominant-baseline", "hanging");
        item.text.split("\n").forEach(function (line, index) {
          var span = createSvg("tspan");
          span.setAttribute("x", item.x);
          if (index > 0) span.setAttribute("dy", round(item.fontSize * 1.3));
          span.textContent = line || " ";
          text.appendChild(span);
        });
        group.appendChild(text);
      } else {
        var path = createSvg("path");
        path.setAttribute("d", pathData(item.points));
        path.setAttribute("fill", "none");
        setStroke(path, item);
        if (item.type === "highlight") path.style.mixBlendMode = "multiply";
        group.appendChild(path);
      }

      Array.prototype.forEach.call(group.children, function (child) {
        child.setAttribute("data-annotation-id", item.id);
        child.style.pointerEvents = state.tool === "eraser" && state.open ? "visiblePainted" : "none";
      });
      drawingGroup.appendChild(group);
    }

    function setStroke(element, item) {
      element.setAttribute("stroke", item.color);
      element.setAttribute("stroke-width", item.width);
      element.setAttribute("stroke-linecap", "round");
      element.setAttribute("stroke-linejoin", "round");
      element.setAttribute("opacity", item.opacity);
    }

    function pathData(points) {
      if (!points.length) return "";
      if (points.length === 1) return "M " + points[0][0] + " " + points[0][1];
      if (points.length === 2) return "M " + points[0][0] + " " + points[0][1] + " L " + points[1][0] + " " + points[1][1];
      var data = "M " + points[0][0] + " " + points[0][1];
      for (var index = 1; index < points.length - 1; index += 1) {
        var midpointX = round((points[index][0] + points[index + 1][0]) / 2);
        var midpointY = round((points[index][1] + points[index + 1][1]) / 2);
        data += " Q " + points[index][0] + " " + points[index][1] + " " + midpointX + " " + midpointY;
      }
      var last = points[points.length - 1];
      return data + " L " + last[0] + " " + last[1];
    }

    function beginTextEditing(point) {
      if (state.textDraft) commitTextEditing();
      state.textDraft = {
        x: point[0],
        y: point[1],
        color: state.color,
        width: state.width,
        fontSize: textSize(state.width),
        before: snapshotItems()
      };
      textInput.value = "";
      textInput.style.color = state.textDraft.color;
      textInput.style.fontSize = Math.min(state.textDraft.fontSize, 30) + "px";
      textInput.style.height = "76px";
      positionTextEditor(point);
      textEditorHost.style.display = "block";
      textEditorHost.setAttribute("aria-hidden", "false");
      refreshUi();
      requestAnimationFrame(function () {
        keepTextEditorInViewport();
        try {
          textInput.focus({ preventScroll: true });
        } catch (error) {
          textInput.focus();
        }
      });
    }

    function positionTextEditor(point) {
      var width = Math.min(280, Math.max(180, window.innerWidth - 24));
      var left = Math.max(12, Math.min(point[0] - window.scrollX + 8, window.innerWidth - width - 12));
      var below = point[1] - window.scrollY + 8;
      var top = below + 154 <= window.innerHeight ? below : Math.max(12, below - 170);
      textEditorHost.style.left = Math.round(left) + "px";
      textEditorHost.style.top = Math.round(top) + "px";
    }

    function resizeTextInput() {
      textInput.style.height = "auto";
      textInput.style.height = Math.min(220, Math.max(76, textInput.scrollHeight)) + "px";
      keepTextEditorInViewport();
    }

    function keepTextEditorInViewport() {
      if (!state.textDraft || textEditorHost.style.display === "none") return;
      var rect = textEditorHost.getBoundingClientRect();
      var left = parseFloat(textEditorHost.style.left) || 12;
      var top = parseFloat(textEditorHost.style.top) || 12;
      if (rect.right > window.innerWidth - 12) left -= rect.right - (window.innerWidth - 12);
      if (rect.bottom > window.innerHeight - 12) top -= rect.bottom - (window.innerHeight - 12);
      textEditorHost.style.left = Math.max(12, Math.round(left)) + "px";
      textEditorHost.style.top = Math.max(12, Math.round(top)) + "px";
    }

    function commitTextEditing() {
      if (!state.textDraft) return;
      var draft = state.textDraft;
      var value = normalizeText(textInput.value);
      closeTextEditor();
      if (!value) {
        refreshUi();
        return;
      }
      state.items.push({
        id: newId(),
        type: "text",
        x: draft.x,
        y: draft.y,
        text: value,
        color: draft.color,
        width: draft.width,
        fontSize: draft.fontSize,
        opacity: 1
      });
      pushUndo(draft.before);
      state.redo = [];
      persist();
      render();
      refreshUi();
      scheduleOverlaySize();
    }

    function cancelTextEditing() {
      if (!state.textDraft) return;
      closeTextEditor();
      refreshUi();
    }

    function closeTextEditor() {
      state.textDraft = null;
      textEditorHost.style.display = "none";
      textEditorHost.setAttribute("aria-hidden", "true");
      textInput.value = "";
    }

    function textSize(width) {
      return TEXT_SIZES[width] || TEXT_SIZES[4];
    }

    function setOpen(open) {
      state.open = Boolean(open);
      panel.hidden = !state.open;
      launcher.setAttribute("aria-pressed", String(state.open));
      launcher.setAttribute("aria-label", state.open ? "Close annotation tools" : "Open annotation tools");
      launcher.setAttribute("title", state.open ? "Close annotation tools" : "Open annotation tools");
      launcher.innerHTML = svgIcon(state.open ? "close" : "pencil");
      if (!state.open) {
        if (state.textDraft) commitTextEditing();
        if (state.draft) state.draft = null;
      }
      updatePointerMode();
      render();
      refreshUi();
    }

    function setTool(tool) {
      if (TOOLS.indexOf(tool) === -1) return;
      if (tool !== "text" && state.textDraft) commitTextEditing();
      state.tool = tool;
      if (tool !== "pointer" && !state.visible) {
        state.visible = true;
        persist();
      }
      savePreferences();
      render();
      refreshUi();
    }

    function updatePointerMode() {
      var drawing = state.open && state.visible && state.tool !== "pointer";
      overlay.style.pointerEvents = drawing ? "auto" : "none";
      overlay.style.cursor = state.tool === "text" ? "text" : "crosshair";
    }

    function toggleVisibility() {
      if (state.textDraft) commitTextEditing();
      state.visible = !state.visible;
      persist();
      render();
      refreshUi();
    }

    function removeItem(id) {
      var before = snapshotItems();
      var next = state.items.filter(function (item) { return item.id !== id; });
      if (next.length === state.items.length) return;
      state.items = next;
      pushUndo(before);
      state.redo = [];
      persist();
      render();
      refreshUi();
    }

    function undo() {
      if (state.textDraft) commitTextEditing();
      if (!state.undo.length) return;
      state.redo.push(snapshotItems());
      state.items = state.undo.pop();
      persist();
      render();
      refreshUi();
    }

    function redo() {
      if (state.textDraft) commitTextEditing();
      if (!state.redo.length) return;
      pushUndo(snapshotItems());
      state.items = state.redo.pop();
      persist();
      render();
      refreshUi();
    }

    function clearAll(skipConfirmation) {
      if (state.textDraft) commitTextEditing();
      if (!state.items.length) return;
      if (!skipConfirmation && !window.confirm("Clear all annotations saved for this page?")) return;
      var before = snapshotItems();
      state.items = [];
      pushUndo(before);
      state.redo = [];
      persist();
      render();
      refreshUi();
    }

    function pushUndo(items) {
      state.undo.push(items);
      if (state.undo.length > MAX_HISTORY) state.undo.shift();
    }

    function snapshotItems() {
      return clone(state.items);
    }

    function exportData() {
      return {
        version: 1,
        pageKey: PAGE_KEY,
        source: location.href.split("#")[0].split("?")[0],
        updatedAt: new Date().toISOString(),
        visible: state.visible,
        items: snapshotItems()
      };
    }

    function downloadExport() {
      var blob = new Blob([JSON.stringify(exportData(), null, 2) + "\n"], { type: "application/json" });
      var url = URL.createObjectURL(blob);
      var link = document.createElement("a");
      var slug = PAGE_KEY.replace(/^\/+|\/+$/g, "").replace(/[^a-zA-Z0-9._-]+/g, "-") || "home";
      link.href = url;
      link.download = slug + ".maas-annotations.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 0);
      setStatus("Exported");
    }

    function importJson(text) {
      var payload;
      try {
        payload = JSON.parse(text);
      } catch (error) {
        setStatus("Invalid JSON");
        return;
      }
      if (!payload || payload.version !== 1 || !Array.isArray(payload.items)) {
        setStatus("Unsupported file");
        return;
      }
      if (payload.pageKey && payload.pageKey !== PAGE_KEY && !window.confirm("These drawings belong to " + payload.pageKey + ". Import them on this page?")) return;
      var normalized = payload.items.map(normalizeItem).filter(Boolean);
      if (!window.confirm("Replace this page's " + state.items.length + " saved mark(s) with " + normalized.length + " imported mark(s)?")) return;
      var before = snapshotItems();
      state.items = normalized;
      state.visible = payload.visible !== false;
      pushUndo(before);
      state.redo = [];
      persist();
      render();
      refreshUi();
      setStatus("Imported");
    }

    function refreshUi() {
      Array.prototype.forEach.call(shadow.querySelectorAll("button[data-tool]"), function (button) {
        var active = button.dataset.tool === state.tool;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", String(active));
      });
      Array.prototype.forEach.call(shadow.querySelectorAll("button[data-color]"), function (button) {
        var active = button.dataset.color === state.color;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-checked", String(active));
      });
      Array.prototype.forEach.call(shadow.querySelectorAll("button[data-width]"), function (button) {
        var active = Number(button.dataset.width) === state.width;
        var textMode = state.tool === "text";
        button.classList.toggle("is-active", active);
        button.classList.toggle("is-text-mode", textMode);
        button.setAttribute("aria-pressed", String(active));
        button.setAttribute("aria-label", textMode ? button.dataset.textLabel : button.dataset.strokeLabel);
        button.setAttribute("title", textMode ? button.dataset.textLabel : button.dataset.strokeLabel);
      });
      shadow.querySelector(".widths").setAttribute("aria-label", state.tool === "text" ? "Text size" : "Stroke width");
      var visibility = shadow.querySelector('button[data-action="visibility"]');
      visibility.innerHTML = svgIcon(state.visible ? "eye" : "eyeOff");
      visibility.setAttribute("aria-label", state.visible ? "Hide annotations" : "Show annotations");
      visibility.setAttribute("title", state.visible ? "Hide annotations" : "Show annotations");
      shadow.querySelector('button[data-action="undo"]').disabled = !state.undo.length;
      shadow.querySelector('button[data-action="redo"]').disabled = !state.redo.length;
      shadow.querySelector('button[data-action="clear"]').disabled = !state.items.length;
      if (state.textDraft) {
        setStatus("Type text, then add");
      } else if (state.open && state.tool === "text") {
        setStatus("Click page for text");
      } else {
        setStatus(state.items.length + (state.items.length === 1 ? " mark" : " marks") + (state.storageOkay ? " | saved" : " | unsaved"));
      }
    }

    function setStatus(message) {
      status.textContent = message;
    }

    function persist() {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
          version: 1,
          pageKey: PAGE_KEY,
          visible: state.visible,
          updatedAt: new Date().toISOString(),
          items: state.items
        }));
        state.storageOkay = true;
      } catch (error) {
        state.storageOkay = false;
      }
    }

    function loadPageState() {
      try {
        var raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        var payload = JSON.parse(raw);
        if (!payload || payload.version !== 1 || !Array.isArray(payload.items)) return;
        state.items = payload.items.map(normalizeItem).filter(Boolean);
        state.visible = payload.visible !== false;
      } catch (error) {
        state.storageOkay = false;
      }
    }

    function loadPreferences() {
      try {
        var preferences = JSON.parse(localStorage.getItem(PREFS_KEY) || "{}");
        if (TOOLS.indexOf(preferences.tool) !== -1) state.tool = preferences.tool;
        if (COLORS.indexOf(preferences.color) !== -1) state.color = preferences.color;
        if (WIDTHS.indexOf(Number(preferences.width)) !== -1) state.width = Number(preferences.width);
      } catch (error) {
        // Invalid preferences fall back to defaults.
      }
    }

    function savePreferences() {
      try {
        localStorage.setItem(PREFS_KEY, JSON.stringify({ tool: state.tool, color: state.color, width: state.width }));
      } catch (error) {
        // Per-page persistence reports storage failures in the UI.
      }
    }

    function normalizeItem(raw) {
      if (!raw || typeof raw !== "object") return null;
      var type = ["path", "highlight", "arrow", "text"].indexOf(raw.type) !== -1 ? raw.type : null;
      if (!type) return null;
      var item = {
        id: typeof raw.id === "string" && raw.id.length <= 100 ? raw.id : newId(),
        type: type,
        color: /^#[0-9a-f]{6}$/i.test(raw.color || "") ? raw.color : DEFAULT_COLOR,
        width: clampNumber(raw.width, 1, 48, 4),
        opacity: clampNumber(raw.opacity, 0.05, 1, type === "highlight" ? 0.3 : 1)
      };
      if (type === "arrow") {
        item.x1 = coordinate(raw.x1);
        item.y1 = coordinate(raw.y1);
        item.x2 = coordinate(raw.x2);
        item.y2 = coordinate(raw.y2);
      } else if (type === "text") {
        item.x = coordinate(raw.x);
        item.y = coordinate(raw.y);
        item.fontSize = clampNumber(raw.fontSize, 10, 96, textSize(item.width));
        item.text = normalizeText(raw.text);
        if (!item.text) return null;
      } else {
        if (!Array.isArray(raw.points)) return null;
        item.points = raw.points.slice(0, 10000).map(function (point) {
          return Array.isArray(point) && point.length >= 2 ? [coordinate(point[0]), coordinate(point[1])] : null;
        }).filter(Boolean);
        if (!item.points.length) return null;
      }
      return item;
    }

    function normalizeText(value) {
      if (typeof value !== "string") return "";
      return value
        .replace(/\r\n?/g, "\n")
        .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, "")
        .slice(0, 5000)
        .trim();
    }

    function coordinate(value) {
      return round(clampNumber(value, -1000000, 10000000, 0));
    }

    function clampNumber(value, min, max, fallback) {
      var number = Number(value);
      return Number.isFinite(number) ? Math.min(max, Math.max(min, number)) : fallback;
    }

    function updateOverlaySize() {
      var root = document.documentElement;
      var body = document.body;
      var width = Math.max(root.scrollWidth, body.scrollWidth, window.innerWidth);
      var height = Math.max(root.scrollHeight, body.scrollHeight, window.innerHeight);
      overlay.setAttribute("width", String(width));
      overlay.setAttribute("height", String(height));
      overlay.style.width = width + "px";
      overlay.style.height = height + "px";
    }

    function scheduleOverlaySize() {
      if (resizeFrame) return;
      resizeFrame = requestAnimationFrame(function () {
        resizeFrame = 0;
        updateOverlaySize();
        keepTextEditorInViewport();
      });
    }

    function createSvg(name) {
      return document.createElementNS(SVG_NS, name);
    }

    function setStyles(element, styles) {
      Object.keys(styles).forEach(function (key) {
        element.style[key] = styles[key];
      });
    }

    function clone(value) {
      return JSON.parse(JSON.stringify(value));
    }

    function round(value) {
      return Math.round(Number(value) * 10) / 10;
    }

    function newId() {
      if (window.crypto && typeof window.crypto.randomUUID === "function") return window.crypto.randomUUID();
      return "mark-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
