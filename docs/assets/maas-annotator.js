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

    var icons = {
      pencil: '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/><path d="m15 5 4 4"/>',
      highlighter: '<path d="m9 11-6 6v3h9l3-3"/><path d="m22 12-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4"/>',
      arrow: '<path d="M13 5H19V11"/><path d="M19 5L5 19"/>',
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

    var host = document.createElement("div");
    host.id = "maas-annotator";
    host.setAttribute("data-maas-annotator-ui", "");
    setStyles(host, {
      all: "initial",
      position: "fixed",
      right: "16px",
      bottom: "16px",
      zIndex: "2147483647"
    });
    document.body.appendChild(host);

    var shadow = host.attachShadow({ mode: "open" });
    shadow.innerHTML = buildUi();

    var panel = shadow.getElementById("panel");
    var launcher = shadow.getElementById("launcher");
    var status = shadow.getElementById("status");
    var importInput = shadow.getElementById("import-input");

    bindUi();
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
        var labels = ["Thin stroke", "Medium stroke", "Thick stroke"];
        return '<button class="icon-button width-button" type="button" data-width="' + width + '" aria-label="' + labels[index] + '" title="' + labels[index] + '"><span style="--dot:' + (width + 3) + 'px"></span></button>';
      }).join("");

      return '<style>' +
        ':host{color:#18242c;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:14px;letter-spacing:0}' +
        '*{box-sizing:border-box;letter-spacing:0}' +
        '[hidden]{display:none!important}' +
        '.shell{display:flex;flex-direction:column;align-items:flex-end;gap:8px}' +
        '.panel{width:344px;border:1px solid #cbd6dc;border-radius:8px;background:#fff;padding:10px;box-shadow:0 10px 28px rgba(20,33,43,.18)}' +
        '.row{display:flex;align-items:center;gap:6px;min-width:0}' +
        '.row+.row{margin-top:8px;padding-top:8px;border-top:1px solid #e3e8eb}' +
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
        '.width-button span{display:block;width:var(--dot);height:var(--dot);border-radius:50%;background:#26343d}' +
        '.actions{flex-wrap:wrap}' +
        '.status{margin-left:auto;min-width:0;overflow:hidden;color:#65737c;font-size:12px;line-height:1.2;text-align:right;text-overflow:ellipsis;white-space:nowrap}' +
        '@media(max-width:480px){.panel{width:calc(100vw - 24px);max-width:344px}.icon-button{width:36px;height:36px;flex-basis:36px}.row{gap:5px}}' +
        '@media(print){.shell{display:none}}' +
        '</style>' +
        '<div class="shell">' +
          '<div class="panel" id="panel" role="toolbar" aria-label="Page drawing tools" hidden>' +
            '<div class="row tools">' +
              toolButton("pointer", "pointer", "Use page") +
              toolButton("pen", "pencil", "Pen") +
              toolButton("highlighter", "highlighter", "Highlighter") +
              toolButton("arrow", "arrow", "Arrow") +
              toolButton("eraser", "eraser", "Erase a mark") +
              '<button class="icon-button" type="button" data-action="visibility" aria-label="Hide drawings" title="Hide drawings">' + svgIcon("eye") + '</button>' +
            '</div>' +
            '<div class="row options"><div class="group colors" role="radiogroup" aria-label="Drawing color">' + colorButtons + '</div><div class="group widths" role="group" aria-label="Stroke width">' + widthButtons + '</div></div>' +
            '<div class="row actions">' +
              actionButton("undo", "undo", "Undo") +
              actionButton("redo", "redo", "Redo") +
              actionButton("export", "download", "Export drawings") +
              actionButton("import", "upload", "Import drawings") +
              actionButton("clear", "trash", "Clear this page") +
              '<span class="status" id="status" role="status" aria-live="polite"></span>' +
            '</div>' +
          '</div>' +
          '<button class="launcher" id="launcher" type="button" aria-label="Open drawing tools" title="Open drawing tools" aria-pressed="false">' + svgIcon("pencil") + '</button>' +
          '<input id="import-input" type="file" accept="application/json,.json" hidden>' +
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

    function bindKeyboard() {
      document.addEventListener("keydown", function (event) {
        var target = event.target;
        var typing = target && (target.matches("input,textarea,select") || target.isContentEditable);
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

    function setOpen(open) {
      state.open = Boolean(open);
      panel.hidden = !state.open;
      launcher.setAttribute("aria-pressed", String(state.open));
      launcher.setAttribute("aria-label", state.open ? "Close drawing tools" : "Open drawing tools");
      launcher.setAttribute("title", state.open ? "Close drawing tools" : "Open drawing tools");
      launcher.innerHTML = svgIcon(state.open ? "close" : "pencil");
      if (!state.open && state.draft) state.draft = null;
      updatePointerMode();
      render();
      refreshUi();
    }

    function setTool(tool) {
      if (["pointer", "pen", "highlighter", "arrow", "eraser"].indexOf(tool) === -1) return;
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
      overlay.style.cursor = state.tool === "eraser" ? "crosshair" : "crosshair";
    }

    function toggleVisibility() {
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
      if (!state.undo.length) return;
      state.redo.push(snapshotItems());
      state.items = state.undo.pop();
      persist();
      render();
      refreshUi();
    }

    function redo() {
      if (!state.redo.length) return;
      pushUndo(snapshotItems());
      state.items = state.redo.pop();
      persist();
      render();
      refreshUi();
    }

    function clearAll(skipConfirmation) {
      if (!state.items.length) return;
      if (!skipConfirmation && !window.confirm("Clear all drawings saved for this page?")) return;
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
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", String(active));
      });
      var visibility = shadow.querySelector('button[data-action="visibility"]');
      visibility.innerHTML = svgIcon(state.visible ? "eye" : "eyeOff");
      visibility.setAttribute("aria-label", state.visible ? "Hide drawings" : "Show drawings");
      visibility.setAttribute("title", state.visible ? "Hide drawings" : "Show drawings");
      shadow.querySelector('button[data-action="undo"]').disabled = !state.undo.length;
      shadow.querySelector('button[data-action="redo"]').disabled = !state.redo.length;
      shadow.querySelector('button[data-action="clear"]').disabled = !state.items.length;
      setStatus(state.items.length + (state.items.length === 1 ? " mark" : " marks") + (state.storageOkay ? " | saved" : " | unsaved"));
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
        if (["pointer", "pen", "highlighter", "arrow", "eraser"].indexOf(preferences.tool) !== -1) state.tool = preferences.tool;
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
      var type = ["path", "highlight", "arrow"].indexOf(raw.type) !== -1 ? raw.type : null;
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
      } else {
        if (!Array.isArray(raw.points)) return null;
        item.points = raw.points.slice(0, 10000).map(function (point) {
          return Array.isArray(point) && point.length >= 2 ? [coordinate(point[0]), coordinate(point[1])] : null;
        }).filter(Boolean);
        if (!item.points.length) return null;
      }
      return item;
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
