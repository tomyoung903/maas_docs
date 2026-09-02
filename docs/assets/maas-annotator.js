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
    var MAX_EDITS = 500;
    var MAX_EDIT_HTML = 200000;
    var DEFAULT_COLOR = "#d94b3d";
    var COLORS = ["#d94b3d", "#f2b84b", "#0f8278", "#2f6feb", "#20262d"];
    var WIDTHS = [2, 4, 7];
    var TOOLS = ["pointer", "edit", "pen", "highlighter", "arrow", "text", "eraser"];
    var DRAW_TOOLS = ["pen", "highlighter", "arrow", "text", "eraser"];
    var TEXT_SIZES = { 2: 16, 4: 22, 7: 30 };
    var EDITABLE_BLOCKS = "h1,h2,h3,h4,h5,h6,p,li,dt,dd,figcaption,caption,th,td,blockquote,pre";
    var EDIT_EXCLUDED_ANCESTORS = "a,button,input,textarea,select,option,[role=button],[role=link],[role=tab],[role=menuitem],[contenteditable],[data-maas-annotator-ui],[data-maas-text-editor]";
    var EDIT_UNSAFE_DESCENDANTS = "script,style,noscript,iframe,object,embed,form,input,textarea,select,button,svg,math,canvas,video,audio";
    var EDIT_BLOCK_DESCENDANTS = "address,article,aside,blockquote,div,dl,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hr,main,nav,ol,p,pre,section,table,ul";

    var icons = {
      pencil: '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/><path d="m15 5 4 4"/>',
      highlighter: '<path d="m9 11-6 6v3h9l3-3"/><path d="m22 12-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4"/>',
      arrow: '<path d="M13 5H19V11"/><path d="M19 5L5 19"/>',
      text: '<path d="M4 7V4h16v3"/><path d="M9 20h6"/><path d="M12 4v16"/>',
      edit: '<path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.4 2.6a2.1 2.1 0 0 1 3 3L12 15l-4 1 1-4Z"/>',
      eraser: '<path d="M21 21H8a2 2 0 0 1-1.42-.587l-3.994-3.999a2 2 0 0 1 0-2.828l10-10a2 2 0 0 1 2.829 0l5.999 6a2 2 0 0 1 0 2.828L12.834 21"/><path d="m5.082 11.09 8.828 8.828"/>',
      pointer: '<path d="M12.586 12.586 19 19"/><path d="M3.5 2.5 10 18l2.5-5.5L18 10Z"/>',
      undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5 5.5 5.5 0 0 1-5.5 5.5H11"/>',
      redo: '<path d="m15 14 5-5-5-5"/><path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5 5.5 5.5 0 0 0 9.5 20H13"/>',
      eye: '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
      eyeOff: '<path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49"/><path d="M14.084 14.158a3 3 0 0 1-4.242-4.242"/><path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"/><path d="m2 2 20 20"/>',
      trash: '<path d="M10 11v6"/><path d="M14 11v6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
      download: '<path d="M12 15V3"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/>',
      upload: '<path d="M12 3v12"/><path d="m17 8-5-5-5 5"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>',
      fileCode: '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5Z"/><polyline points="14 2 14 8 20 8"/><path d="m10 13-2 2 2 2"/><path d="m14 17 2-2-2-2"/>',
      reset: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
      close: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'
    };

    var state = {
      open: false,
      visible: true,
      tool: "pen",
      color: DEFAULT_COLOR,
      width: 4,
      items: [],
      edits: [],
      undo: [],
      redo: [],
      draft: null,
      textDraft: null,
      editDraft: null,
      editHover: null,
      editIssueCount: 0,
      applyingEdits: false,
      applyEditsFrame: 0,
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

    var editStyle = document.createElement("style");
    editStyle.setAttribute("data-maas-edit-style", "");
    editStyle.textContent =
      "html[data-maas-page-edit-mode] [data-maas-edit-hover]{outline:2px dashed #0f8278!important;outline-offset:3px!important;cursor:text!important}" +
      "[data-maas-edit-active]{outline:3px solid #0f8278!important;outline-offset:3px!important;cursor:text!important;caret-color:#0f8278!important}" +
      "@media print{[data-maas-edit-hover],[data-maas-edit-active]{outline:none!important}}";
    document.head.appendChild(editStyle);

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
    bindPageEditing();
    bindDrawing();
    bindKeyboard();
    applySavedEdits();
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
    window.addEventListener("load", function () {
      scheduleOverlaySize();
      scheduleApplyEdits();
    }, { once: true });

    var editObserver = typeof MutationObserver === "function"
      ? new MutationObserver(function () {
          if (state.edits.length && !state.applyingEdits && !state.editDraft) scheduleApplyEdits();
        })
      : null;
    if (editObserver) editObserver.observe(document.body, { childList: true, subtree: true, characterData: true });

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
          items: state.items,
          edits: state.edits,
          editIssueCount: state.editIssueCount
        });
      },
      setOpen: setOpen,
      setTool: setTool,
      clear: clearAll,
      resetEdits: resetEdits,
      downloadEditedHtml: downloadEditedHtml,
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
        '.panel{width:390px;border:1px solid #cbd6dc;border-radius:8px;background:#fff;padding:10px;box-shadow:0 10px 28px rgba(20,33,43,.18)}' +
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
        '.label-button{min-height:32px;padding:5px 10px;font-size:12px;font-weight:650}' +
        '.label-button.primary{border-color:#0c6f67;color:#fff;background:#0f8278}' +
        '.label-button.primary:hover{background:#0c7169}' +
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
        '.edit-copy{min-width:0;margin-right:auto;color:#40515c;font-size:12px;font-weight:650;line-height:1.25}' +
        '.actions{flex-wrap:wrap}' +
        '.status{margin-left:auto;min-width:0;overflow:hidden;color:#65737c;font-size:12px;line-height:1.2;text-align:right;text-overflow:ellipsis;white-space:nowrap}' +
        '@media(max-width:480px){.panel{width:calc(100vw - 24px);max-width:390px}.icon-button{width:36px;height:36px;flex-basis:36px}.row{gap:5px}}' +
        '@media(print){.shell{display:none}}' +
        '</style>' +
        '<div class="shell">' +
          '<div class="panel" id="panel" role="toolbar" aria-label="Page annotation and editing tools" hidden>' +
            '<div class="row tools">' +
              toolButton("pointer", "pointer", "Use page") +
              toolButton("edit", "edit", "Edit Page") +
              toolButton("pen", "pencil", "Pen") +
              toolButton("highlighter", "highlighter", "Highlighter") +
              toolButton("arrow", "arrow", "Arrow") +
              toolButton("text", "text", "Add text") +
              toolButton("eraser", "eraser", "Erase a mark") +
              '<button class="icon-button" type="button" data-action="visibility" aria-label="Hide annotations" title="Hide annotations">' + svgIcon("eye") + '</button>' +
            '</div>' +
            '<div class="row edit-actions" id="edit-actions" hidden><span class="edit-copy">Editing existing page text</span><button class="label-button" type="button" data-edit-command="cancel">Cancel</button><button class="label-button primary" type="button" data-edit-command="save">Save edit</button></div>' +
            '<div class="row options" id="options-row"><div class="group colors" role="radiogroup" aria-label="Annotation color">' + colorButtons + '</div><div class="group widths" role="group" aria-label="Stroke width">' + widthButtons + '</div></div>' +
            '<div class="row actions">' +
              actionButton("undo", "undo", "Undo") +
              actionButton("redo", "redo", "Redo") +
              actionButton("export", "download", "Export page changes") +
              actionButton("import", "upload", "Import page changes") +
              actionButton("download-html", "fileCode", "Download edited HTML") +
              actionButton("reset-edits", "reset", "Reset page text edits") +
              actionButton("clear", "trash", "Clear annotations and text edits") +
              '<span class="status" id="status" role="status" aria-live="polite"></span>' +
            '</div>' +
          '</div>' +
          '<button class="launcher" id="launcher" type="button" aria-label="Open page tools" title="Open page tools" aria-pressed="false">' + svgIcon("pencil") + '</button>' +
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
        var editCommand = event.target.closest("button[data-edit-command]");
        if (editCommand) {
          if (editCommand.dataset.editCommand === "save") commitPageEdit();
          if (editCommand.dataset.editCommand === "cancel") cancelPageEdit();
          return;
        }

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
        if (state.editDraft) commitPageEdit();
        if (action.dataset.action === "undo") undo();
        if (action.dataset.action === "redo") redo();
        if (action.dataset.action === "visibility") toggleVisibility();
        if (action.dataset.action === "export") downloadExport();
        if (action.dataset.action === "import") importInput.click();
        if (action.dataset.action === "download-html") downloadEditedHtml();
        if (action.dataset.action === "reset-edits") resetEdits();
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

    function bindPageEditing() {
      document.addEventListener("pointerover", function (event) {
        if (!pageEditMode() || state.editDraft || isAnnotatorTarget(event.target)) return;
        setEditHover(findEditableTarget(event.target));
      }, true);

      document.addEventListener("pointerout", function (event) {
        if (!state.editHover) return;
        var related = event.relatedTarget;
        if (!related || !state.editHover.contains(related)) setEditHover(null);
      }, true);

      document.addEventListener("click", function (event) {
        if (!pageEditMode() || isAnnotatorTarget(event.target)) return;

        if (state.editDraft && state.editDraft.element.contains(event.target)) {
          if (event.target.closest && event.target.closest("a")) event.preventDefault();
          return;
        }

        if (state.editDraft) commitPageEdit();
        var editable = findEditableTarget(event.target);
        if (!editable) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        beginPageEdit(editable, event.clientX, event.clientY);
      }, true);

      document.addEventListener("paste", function (event) {
        if (!state.editDraft || !state.editDraft.element.contains(event.target)) return;
        event.preventDefault();
        insertPlainText(event.clipboardData && event.clipboardData.getData("text/plain"));
      }, true);

      document.addEventListener("dragover", function (event) {
        if (state.editDraft && state.editDraft.element.contains(event.target)) event.preventDefault();
      }, true);

      document.addEventListener("drop", function (event) {
        if (!state.editDraft || !state.editDraft.element.contains(event.target)) return;
        event.preventDefault();
        insertPlainText(event.dataTransfer && event.dataTransfer.getData("text/plain"));
      }, true);
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
        if (state.editDraft) {
          if (event.key === "Escape") {
            event.preventDefault();
            event.stopImmediatePropagation();
            cancelPageEdit();
          } else if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
            event.preventDefault();
            event.stopImmediatePropagation();
            commitPageEdit();
          }
          return;
        }
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
        var before = snapshotState();
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
        before: snapshotState()
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

    function pageEditMode() {
      return state.open && state.tool === "edit";
    }

    function isAnnotatorTarget(target) {
      var element = target instanceof Element ? target : target && target.parentElement;
      return Boolean(element && element.closest("[data-maas-annotator-ui],[data-maas-text-editor]"));
    }

    function findEditableTarget(target) {
      var element = target instanceof Element ? target : target && target.parentElement;
      if (!element || isAnnotatorTarget(element) || element.closest(EDIT_EXCLUDED_ANCESTORS)) return null;

      var block = element.closest(EDITABLE_BLOCKS);
      if (isEditableCandidate(block)) return block;

      var span = element.closest("span");
      if (isEditableCandidate(span)) return span;

      var container = element.closest("div");
      return isEditableCandidate(container) ? container : null;
    }

    function isEditableCandidate(element) {
      if (!(element instanceof HTMLElement) || element === document.body || !document.body.contains(element)) return false;
      if (isAnnotatorTarget(element) || element.closest(EDIT_EXCLUDED_ANCESTORS)) return false;
      if (element.querySelector(EDIT_UNSAFE_DESCENDANTS) || element.querySelector(EDIT_BLOCK_DESCENDANTS)) return false;
      if (!String(element.textContent || "").trim() || element.innerHTML.length > MAX_EDIT_HTML) return false;
      return element.getClientRects().length > 0;
    }

    function setEditHover(element) {
      if (state.editHover === element) return;
      if (state.editHover && state.editHover.isConnected) state.editHover.removeAttribute("data-maas-edit-hover");
      state.editHover = element || null;
      if (state.editHover) state.editHover.setAttribute("data-maas-edit-hover", "");
    }

    function beginPageEdit(element, clientX, clientY) {
      if (!pageEditMode() || !isEditableCandidate(element)) return;
      if (state.textDraft) commitTextEditing();
      if (state.editDraft) commitPageEdit();

      var selector = selectorForElement(element);
      if (!selector) {
        setStatus("This text cannot be tracked safely");
        return;
      }
      var existing = state.edits.find(function (edit) { return edit.selector === selector; });
      var startHtml = canonicalHtml(element.innerHTML);
      var existingMatchesPage = existing && (
        startHtml === canonicalHtml(existing.originalHtml) ||
        startHtml === canonicalHtml(existing.html)
      );
      state.editDraft = {
        element: element,
        selector: selector,
        tagName: element.tagName.toLowerCase(),
        originalHtml: existingMatchesPage ? existing.originalHtml : sanitizeEditableHtml(startHtml),
        existingId: existing ? existing.id : null,
        startHtml: startHtml,
        before: snapshotState(),
        contentEditableAttr: element.getAttribute("contenteditable"),
        spellcheckAttr: element.getAttribute("spellcheck")
      };
      setEditHover(null);
      element.setAttribute("data-maas-edit-active", "");
      element.setAttribute("contenteditable", "plaintext-only");
      if (!element.isContentEditable) element.setAttribute("contenteditable", "true");
      element.setAttribute("spellcheck", "false");
      refreshUi();
      requestAnimationFrame(function () {
        if (!state.editDraft || state.editDraft.element !== element) return;
        try {
          element.focus({ preventScroll: true });
        } catch (error) {
          element.focus();
        }
        placeCaretAtPoint(element, clientX, clientY);
      });
    }

    function placeCaretAtPoint(element, clientX, clientY) {
      var range = null;
      if (document.caretPositionFromPoint) {
        var position = document.caretPositionFromPoint(clientX, clientY);
        if (position && element.contains(position.offsetNode)) {
          range = document.createRange();
          range.setStart(position.offsetNode, position.offset);
          range.collapse(true);
        }
      } else if (document.caretRangeFromPoint) {
        var pointRange = document.caretRangeFromPoint(clientX, clientY);
        if (pointRange && element.contains(pointRange.startContainer)) range = pointRange;
      }
      if (!range) {
        range = document.createRange();
        range.selectNodeContents(element);
        range.collapse(false);
      }
      var selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
    }

    function commitPageEdit() {
      if (!state.editDraft) return;
      var draft = state.editDraft;
      if (!draft.element.isConnected) {
        finishPageEdit();
        setStatus("Text changed while editing; edit cancelled");
        return;
      }

      var rawHtml = draft.element.innerHTML;
      if (rawHtml.length > MAX_EDIT_HTML) {
        draft.element.innerHTML = draft.startHtml;
        finishPageEdit();
        setStatus("That edit is too large; it was cancelled");
        return;
      }
      var currentHtml = canonicalHtml(rawHtml);
      if (currentHtml === draft.startHtml) {
        finishPageEdit();
        refreshUi();
        return;
      }
      var editedHtml = sanitizeEditableHtml(currentHtml);
      var originalHtml = sanitizeEditableHtml(draft.originalHtml);
      if (editedHtml === draft.startHtml) {
        draft.element.innerHTML = draft.startHtml;
        finishPageEdit();
        refreshUi();
        return;
      }

      var index = state.edits.findIndex(function (edit) { return edit.selector === draft.selector; });
      if (index === -1 && editedHtml !== originalHtml && state.edits.length >= MAX_EDITS) {
        draft.element.innerHTML = draft.startHtml;
        finishPageEdit();
        setStatus("Page edit limit reached");
        return;
      }

      draft.element.innerHTML = editedHtml;
      if (editedHtml === originalHtml) {
        if (index !== -1) state.edits.splice(index, 1);
      } else {
        var edit = {
          id: draft.existingId || newId(),
          selector: draft.selector,
          tagName: draft.tagName,
          originalHtml: originalHtml,
          html: editedHtml,
          updatedAt: new Date().toISOString()
        };
        if (index === -1) state.edits.push(edit);
        else state.edits[index] = edit;
      }
      finishPageEdit();
      pushUndo(draft.before);
      state.redo = [];
      persist();
      applySavedEdits();
      refreshUi();
    }

    function cancelPageEdit() {
      if (!state.editDraft) return;
      var draft = state.editDraft;
      if (draft.element.isConnected) draft.element.innerHTML = draft.startHtml;
      finishPageEdit();
      scheduleApplyEdits();
      refreshUi();
    }

    function finishPageEdit() {
      if (!state.editDraft) return;
      var draft = state.editDraft;
      if (draft.element.isConnected) {
        draft.element.removeAttribute("data-maas-edit-active");
        if (draft.contentEditableAttr === null) draft.element.removeAttribute("contenteditable");
        else draft.element.setAttribute("contenteditable", draft.contentEditableAttr);
        if (draft.spellcheckAttr === null) draft.element.removeAttribute("spellcheck");
        else draft.element.setAttribute("spellcheck", draft.spellcheckAttr);
      }
      state.editDraft = null;
      var selection = window.getSelection();
      if (selection) selection.removeAllRanges();
    }

    function insertPlainText(value) {
      if (!state.editDraft) return;
      var text = String(value || "").replace(/\r\n?/g, "\n").slice(0, MAX_EDIT_HTML);
      state.editDraft.element.focus();
      if (document.execCommand && document.execCommand("insertText", false, text)) return;
      var selection = window.getSelection();
      if (!selection || !selection.rangeCount || !state.editDraft.element.contains(selection.anchorNode)) {
        state.editDraft.element.appendChild(document.createTextNode(text));
        return;
      }
      var range = selection.getRangeAt(0);
      range.deleteContents();
      var node = document.createTextNode(text);
      range.insertNode(node);
      range.setStartAfter(node);
      range.collapse(true);
      selection.removeAllRanges();
      selection.addRange(range);
    }

    function selectorForElement(element) {
      var parts = [];
      var current = element;
      while (current && current !== document.body) {
        if (current.id) {
          var idSelector = "#" + escapeCssIdentifier(current.id);
          try {
            if (document.querySelectorAll(idSelector).length === 1) {
              parts.unshift(idSelector);
              return parts.join(" > ").slice(0, 2000);
            }
          } catch (error) {
            // Fall through to an nth-of-type selector.
          }
        }
        var tagName = current.tagName.toLowerCase();
        var siblings = current.parentElement ? Array.prototype.filter.call(current.parentElement.children, function (child) {
          return child.tagName === current.tagName;
        }) : [];
        var index = siblings.indexOf(current) + 1;
        parts.unshift(tagName + ":nth-of-type(" + index + ")");
        current = current.parentElement;
      }
      return current === document.body ? ("body > " + parts.join(" > ")).slice(0, 2000) : "";
    }

    function escapeCssIdentifier(value) {
      if (window.CSS && typeof window.CSS.escape === "function") return window.CSS.escape(value);
      return String(value).replace(/[^a-zA-Z0-9_-]/g, function (character) {
        return "\\" + character.codePointAt(0).toString(16) + " ";
      });
    }

    function setOpen(open) {
      state.open = Boolean(open);
      panel.hidden = !state.open;
      launcher.setAttribute("aria-pressed", String(state.open));
      launcher.setAttribute("aria-label", state.open ? "Close page tools" : "Open page tools");
      launcher.setAttribute("title", state.open ? "Close page tools" : "Open page tools");
      launcher.innerHTML = svgIcon(state.open ? "close" : "pencil");
      if (!state.open) {
        if (state.textDraft) commitTextEditing();
        if (state.editDraft) commitPageEdit();
        if (state.draft) state.draft = null;
      }
      updatePointerMode();
      render();
      refreshUi();
    }

    function setTool(tool) {
      if (TOOLS.indexOf(tool) === -1) return;
      if (tool !== "text" && state.textDraft) commitTextEditing();
      if (tool !== "edit" && state.editDraft) commitPageEdit();
      state.tool = tool;
      if (DRAW_TOOLS.indexOf(tool) !== -1 && !state.visible) {
        state.visible = true;
        persist();
      }
      savePreferences();
      render();
      refreshUi();
    }

    function updatePointerMode() {
      var drawing = state.open && state.visible && DRAW_TOOLS.indexOf(state.tool) !== -1;
      overlay.style.pointerEvents = drawing ? "auto" : "none";
      overlay.style.cursor = state.tool === "text" ? "text" : "crosshair";
      document.documentElement.toggleAttribute("data-maas-page-edit-mode", pageEditMode());
      if (!pageEditMode()) setEditHover(null);
    }

    function toggleVisibility() {
      if (state.textDraft) commitTextEditing();
      if (state.editDraft) commitPageEdit();
      state.visible = !state.visible;
      persist();
      render();
      refreshUi();
    }

    function removeItem(id) {
      var before = snapshotState();
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
      if (state.editDraft) commitPageEdit();
      if (!state.undo.length) return;
      state.redo.push(snapshotState());
      applyStateSnapshot(state.undo.pop());
      persist();
      render();
      refreshUi();
    }

    function redo() {
      if (state.textDraft) commitTextEditing();
      if (state.editDraft) commitPageEdit();
      if (!state.redo.length) return;
      pushUndo(snapshotState());
      applyStateSnapshot(state.redo.pop());
      persist();
      render();
      refreshUi();
    }

    function clearAll(skipConfirmation) {
      if (state.textDraft) commitTextEditing();
      if (state.editDraft) commitPageEdit();
      if (!state.items.length && !state.edits.length) return;
      if (!skipConfirmation && !window.confirm("Clear all annotations and page text edits saved for this page?")) return;
      var before = snapshotState();
      restoreAppliedEdits(state.edits);
      state.items = [];
      state.edits = [];
      state.editIssueCount = 0;
      pushUndo(before);
      state.redo = [];
      persist();
      render();
      refreshUi();
    }

    function resetEdits(skipConfirmation) {
      if (state.editDraft) commitPageEdit();
      if (!state.edits.length) return;
      if (!skipConfirmation && !window.confirm("Reset all saved page text edits on this page?")) return;
      var before = snapshotState();
      restoreAppliedEdits(state.edits);
      state.edits = [];
      state.editIssueCount = 0;
      pushUndo(before);
      state.redo = [];
      persist();
      refreshUi();
    }

    function pushUndo(snapshot) {
      state.undo.push(snapshot);
      if (state.undo.length > MAX_HISTORY) state.undo.shift();
    }

    function snapshotState() {
      return clone({ items: state.items, edits: state.edits });
    }

    function applyStateSnapshot(snapshot) {
      restoreAppliedEdits(state.edits);
      state.items = clone(snapshot && Array.isArray(snapshot.items) ? snapshot.items : []);
      state.edits = clone(snapshot && Array.isArray(snapshot.edits) ? snapshot.edits : []);
      applySavedEdits();
    }

    function exportData() {
      return {
        version: 1,
        pageKey: PAGE_KEY,
        source: location.href.split("#")[0].split("?")[0],
        updatedAt: new Date().toISOString(),
        visible: state.visible,
        items: clone(state.items),
        edits: clone(state.edits)
      };
    }

    function downloadExport() {
      var blob = new Blob([JSON.stringify(exportData(), null, 2) + "\n"], { type: "application/json" });
      var url = URL.createObjectURL(blob);
      var link = document.createElement("a");
      var slug = PAGE_KEY.replace(/^\/+|\/+$/g, "").replace(/[^a-zA-Z0-9._-]+/g, "-") || "home";
      link.href = url;
      link.download = slug + ".maas-page-changes.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 0);
      setStatus("Page changes exported");
    }

    function downloadEditedHtml() {
      if (state.textDraft) commitTextEditing();
      if (state.editDraft) commitPageEdit();
      var page = document.documentElement.cloneNode(true);
      Array.prototype.forEach.call(page.querySelectorAll("[data-maas-annotation-layer],[data-maas-annotator-ui],[data-maas-text-editor],[data-maas-edit-style]"), function (element) {
        element.remove();
      });
      page.removeAttribute("data-maas-page-edit-mode");
      Array.prototype.forEach.call(page.querySelectorAll("[data-maas-edit-hover],[data-maas-edit-active]"), function (element) {
        element.removeAttribute("data-maas-edit-hover");
        element.removeAttribute("data-maas-edit-active");
      });
      var html = serializeDoctype() + "\n" + page.outerHTML + "\n";
      var blob = new Blob([html], { type: "text/html;charset=utf-8" });
      var url = URL.createObjectURL(blob);
      var link = document.createElement("a");
      var slug = PAGE_KEY.replace(/^\/+|\/+$/g, "").replace(/[^a-zA-Z0-9._-]+/g, "-") || "index";
      link.href = url;
      link.download = slug.replace(/\.html$/i, "") + ".edited.html";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 0);
      setStatus("Edited HTML downloaded");
    }

    function serializeDoctype() {
      if (!document.doctype) return "<!doctype html>";
      var doctype = "<!DOCTYPE " + document.doctype.name;
      if (document.doctype.publicId) doctype += ' PUBLIC "' + document.doctype.publicId + '"';
      if (document.doctype.systemId) doctype += ' "' + document.doctype.systemId + '"';
      return doctype + ">";
    }

    function importJson(text) {
      var payload;
      try {
        payload = JSON.parse(text);
      } catch (error) {
        setStatus("Invalid JSON");
        return;
      }
      if (!payload || payload.version !== 1 || (!Array.isArray(payload.items) && !Array.isArray(payload.edits))) {
        setStatus("Unsupported file");
        return;
      }
      if (payload.pageKey && payload.pageKey !== PAGE_KEY && !window.confirm("These page changes belong to " + payload.pageKey + ". Import them on this page?")) return;
      var normalizedItems = (Array.isArray(payload.items) ? payload.items : []).map(normalizeItem).filter(Boolean);
      var normalizedEdits = normalizeEdits(payload.edits);
      if (!window.confirm("Replace this page's " + state.items.length + " saved mark(s) and " + state.edits.length + " text edit(s) with " + normalizedItems.length + " mark(s) and " + normalizedEdits.length + " text edit(s)?")) return;
      var before = snapshotState();
      restoreAppliedEdits(state.edits);
      state.items = normalizedItems;
      state.edits = normalizedEdits;
      state.visible = payload.visible !== false;
      pushUndo(before);
      state.redo = [];
      applySavedEdits();
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
      shadow.getElementById("options-row").hidden = state.tool === "edit";
      shadow.getElementById("edit-actions").hidden = !state.editDraft;
      shadow.querySelector(".widths").setAttribute("aria-label", state.tool === "text" ? "Text size" : "Stroke width");
      var visibility = shadow.querySelector('button[data-action="visibility"]');
      visibility.innerHTML = svgIcon(state.visible ? "eye" : "eyeOff");
      visibility.setAttribute("aria-label", state.visible ? "Hide annotations" : "Show annotations");
      visibility.setAttribute("title", state.visible ? "Hide annotations" : "Show annotations");
      shadow.querySelector('button[data-action="undo"]').disabled = !state.undo.length;
      shadow.querySelector('button[data-action="redo"]').disabled = !state.redo.length;
      shadow.querySelector('button[data-action="reset-edits"]').disabled = !state.edits.length;
      shadow.querySelector('button[data-action="clear"]').disabled = !state.items.length && !state.edits.length;
      if (state.textDraft) {
        setStatus("Type text, then add");
      } else if (state.editDraft) {
        setStatus("Ctrl/⌘+Enter saves | Esc cancels");
      } else if (state.open && state.tool === "edit") {
        setStatus(state.editIssueCount ? state.editIssueCount + " edit(s) need review" : "Click existing text | " + state.edits.length + " saved");
      } else if (state.open && state.tool === "text") {
        setStatus("Click page for text");
      } else {
        setStatus(state.items.length + (state.items.length === 1 ? " mark" : " marks") + " | " + state.edits.length + (state.edits.length === 1 ? " edit" : " edits") + (state.storageOkay ? " | saved" : " | unsaved"));
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
          items: state.items,
          edits: state.edits
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
        if (!payload || payload.version !== 1) return;
        state.items = (Array.isArray(payload.items) ? payload.items : []).map(normalizeItem).filter(Boolean);
        state.edits = normalizeEdits(payload.edits);
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

    function normalizeEdits(rawEdits) {
      var seen = Object.create(null);
      return (Array.isArray(rawEdits) ? rawEdits : []).slice(0, MAX_EDITS).map(normalizeEdit).filter(function (edit) {
        if (!edit || seen[edit.selector]) return false;
        seen[edit.selector] = true;
        return true;
      });
    }

    function normalizeEdit(raw) {
      if (!raw || typeof raw !== "object") return null;
      if (typeof raw.selector !== "string" || !raw.selector || raw.selector.length > 2000) return null;
      if (raw.selector.indexOf("\u0000") !== -1 || /[\r\n]/.test(raw.selector) || hasUnescapedComma(raw.selector)) return null;
      if (raw.selector.charAt(0) !== "#" && raw.selector.indexOf("body > ") !== 0) return null;
      if (typeof raw.tagName !== "string" || !/^(?:h[1-6]|p|li|dt|dd|figcaption|caption|th|td|blockquote|pre|span|div)$/.test(raw.tagName)) return null;
      if (typeof raw.originalHtml !== "string" || typeof raw.html !== "string") return null;
      if (raw.originalHtml.length > MAX_EDIT_HTML || raw.html.length > MAX_EDIT_HTML) return null;

      var originalHtml = sanitizeEditableHtml(raw.originalHtml);
      var html = sanitizeEditableHtml(raw.html);
      if (originalHtml === html) return null;
      return {
        id: typeof raw.id === "string" && raw.id.length <= 100 ? raw.id : newId(),
        selector: raw.selector,
        tagName: raw.tagName,
        originalHtml: originalHtml,
        html: html,
        updatedAt: typeof raw.updatedAt === "string" && raw.updatedAt.length <= 100 ? raw.updatedAt : new Date().toISOString()
      };
    }

    function hasUnescapedComma(value) {
      for (var index = 0; index < value.length; index += 1) {
        if (value.charAt(index) !== ",") continue;
        var slashCount = 0;
        for (var cursor = index - 1; cursor >= 0 && value.charAt(cursor) === "\\"; cursor -= 1) slashCount += 1;
        if (slashCount % 2 === 0) return true;
      }
      return false;
    }

    function canonicalHtml(value) {
      var source = typeof value === "string" ? value : String(value || "");
      var template = document.createElement("template");
      template.innerHTML = source.slice(0, MAX_EDIT_HTML);
      return template.innerHTML;
    }

    function sanitizeEditableHtml(value) {
      var template = document.createElement("template");
      template.innerHTML = String(value || "").slice(0, MAX_EDIT_HTML);

      Array.prototype.forEach.call(template.content.querySelectorAll("script,style,noscript,template,iframe,object,embed,form,input,textarea,select,option,button,meta,link,base,svg,math,canvas,video,audio,source,track"), function (element) {
        if (element.matches("script,style,noscript,template,meta,link,base")) {
          element.remove();
          return;
        }
        element.replaceWith(document.createTextNode(element.textContent || ""));
      });

      Array.prototype.forEach.call(template.content.querySelectorAll("*"), function (element) {
        Array.prototype.slice.call(element.attributes).forEach(function (attribute) {
          var name = attribute.name.toLowerCase();
          var compactValue = attribute.value.replace(/[\u0000-\u0020]+/g, "").toLowerCase();
          var urlAttribute = ["href", "src", "xlink:href", "action", "cite", "poster", "background", "ping"].indexOf(name) !== -1;
          if (
            name.indexOf("on") === 0 ||
            name === "srcdoc" ||
            name === "autofocus" ||
            name === "contenteditable" ||
            name === "tabindex" ||
            name === "form" ||
            name === "formaction" ||
            name === "data-maas-edit-hover" ||
            name === "data-maas-edit-active" ||
            (urlAttribute && /^(?:javascript|vbscript|data):/.test(compactValue)) ||
            (name === "srcset" && /(?:javascript|vbscript|data):/.test(compactValue)) ||
            (name === "style" && /(?:url\s*\(|expression\s*\(|@import|behavior\s*:|-moz-binding)/i.test(attribute.value))
          ) {
            element.removeAttribute(attribute.name);
          }
        });
      });
      return canonicalHtml(template.innerHTML);
    }

    function findEditElement(edit) {
      if (!edit || typeof edit.selector !== "string") return null;
      var matches;
      try {
        matches = document.querySelectorAll(edit.selector);
      } catch (error) {
        return null;
      }
      if (matches.length !== 1) return null;
      var element = matches[0];
      if (!(element instanceof HTMLElement) || !document.body.contains(element) || isAnnotatorTarget(element)) return null;
      if (element.tagName.toLowerCase() !== edit.tagName || !element.matches(EDITABLE_BLOCKS + ",span,div")) return null;
      if (element.closest(EDIT_EXCLUDED_ANCESTORS) || element.querySelector(EDIT_UNSAFE_DESCENDANTS)) return null;
      return element;
    }

    function applySavedEdits() {
      var issueCount = 0;
      var wasApplying = state.applyingEdits;
      state.applyingEdits = true;
      try {
        state.edits.forEach(function (edit) {
          var element = findEditElement(edit);
          if (!element) {
            issueCount += 1;
            return;
          }
          if (state.editDraft && state.editDraft.element === element) return;
          var currentHtml = canonicalHtml(element.innerHTML);
          if (currentHtml === edit.html) return;
          if (currentHtml === edit.originalHtml) {
            element.innerHTML = edit.html;
            return;
          }
          issueCount += 1;
        });
      } finally {
        state.applyingEdits = wasApplying;
      }
      state.editIssueCount = issueCount;
    }

    function restoreAppliedEdits(edits) {
      var wasApplying = state.applyingEdits;
      state.applyingEdits = true;
      try {
        (Array.isArray(edits) ? edits : []).slice().reverse().forEach(function (edit) {
          var element = findEditElement(edit);
          if (!element) return;
          if (canonicalHtml(element.innerHTML) === edit.html) element.innerHTML = edit.originalHtml;
        });
      } finally {
        state.applyingEdits = wasApplying;
      }
    }

    function scheduleApplyEdits() {
      if (state.applyEditsFrame || !state.edits.length) return;
      state.applyEditsFrame = requestAnimationFrame(function () {
        state.applyEditsFrame = 0;
        var previousIssueCount = state.editIssueCount;
        applySavedEdits();
        if (previousIssueCount !== state.editIssueCount) refreshUi();
      });
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
