/* AUTO-GENERATED from ts/utils/element-inspector.ts via esbuild — do not edit by hand. Rebuild: npm run build:ui -- --only js/utils/element-inspector.js */
"use strict";
(() => {
  // ts/utils/_element-inspector/_overlay-manager.ts
  var OverlayManager = class {
    overlayContainer = null;
    styleElement = null;
    isActive() {
      return this.overlayContainer !== null;
    }
    getContainer() {
      return this.overlayContainer;
    }
    createOverlay() {
      this.overlayContainer = document.createElement("div");
      this.overlayContainer.id = "element-inspector-overlay";
      const docHeight = Math.max(
        document.body.scrollHeight,
        document.documentElement.scrollHeight,
        document.body.offsetHeight,
        document.documentElement.offsetHeight,
        document.body.clientHeight,
        document.documentElement.clientHeight
      );
      this.overlayContainer.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: ${docHeight}px;
            pointer-events: none;
            z-index: 999999;
        `;
      this.addStyles();
      document.body.appendChild(this.overlayContainer);
      return this.overlayContainer;
    }
    removeOverlay() {
      if (this.overlayContainer) {
        this.overlayContainer.remove();
        this.overlayContainer = null;
      }
      if (this.styleElement) {
        this.styleElement.remove();
        this.styleElement = null;
      }
    }
    addStyles() {
      const linkElement = document.createElement("link");
      linkElement.rel = "stylesheet";
      linkElement.href = "/static/scitex_sdk/ui/css/utils/element-inspector.css";
      linkElement.id = "element-inspector-styles";
      document.head.appendChild(linkElement);
      this.styleElement = linkElement;
    }
  };

  // ts/utils/_element-inspector/_LayerPickerPanel.ts
  var LayerPickerPanel = class {
    panel = null;
    elementsAtCursor = [];
    currentDepthIndex = 0;
    debugCollector;
    notificationManager;
    highlightCallback = null;
    getDepthFn;
    getColorFn;
    constructor(debugCollector, notificationManager, getDepthFn, getColorFn) {
      this.debugCollector = debugCollector;
      this.notificationManager = notificationManager;
      this.getDepthFn = getDepthFn;
      this.getColorFn = getColorFn;
    }
    /**
     * Set callback for highlighting selected element
     */
    setHighlightCallback(callback) {
      this.highlightCallback = callback;
    }
    /**
     * Get current depth index
     */
    getCurrentDepthIndex() {
      return this.currentDepthIndex;
    }
    /**
     * Get elements at cursor
     */
    getElementsAtCursor() {
      return this.elementsAtCursor;
    }
    /**
     * Get the currently selected element
     */
    getSelectedElement() {
      if (this.elementsAtCursor.length > 0 && this.currentDepthIndex < this.elementsAtCursor.length) {
        return this.elementsAtCursor[this.currentDepthIndex];
      }
      return null;
    }
    /**
     * Show layer picker panel at position with given elements
     */
    show(x, y, elements) {
      this.remove();
      this.elementsAtCursor = elements;
      this.currentDepthIndex = 0;
      if (elements.length <= 1) return;
      const panel = document.createElement("div");
      panel.className = "element-inspector-layer-picker";
      panel.tabIndex = 0;
      panel.style.cssText = `
      position: fixed;
      top: ${Math.min(y + 10, window.innerHeight - 300)}px;
      left: ${Math.min(x + 15, window.innerWidth - 220)}px;
      background: rgba(30, 30, 30, 0.95);
      border: 1px solid rgba(100, 100, 100, 0.5);
      border-radius: 6px;
      padding: 6px 0;
      min-width: 200px;
      max-height: 280px;
      overflow-y: auto;
      z-index: 10000001;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace;
      font-size: 11px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
      outline: none;
    `;
      const header = document.createElement("div");
      header.style.cssText = `
      padding: 4px 10px 6px;
      color: #888;
      border-bottom: 1px solid rgba(100, 100, 100, 0.3);
      margin-bottom: 4px;
      font-size: 10px;
    `;
      header.textContent = `${elements.length} layers (\u2191\u2193/Tab + Enter)`;
      panel.appendChild(header);
      this.setupKeyboardHandler(panel);
      this.renderElementList(panel, elements);
      document.body.appendChild(panel);
      this.panel = panel;
      this.updateSelection();
      setTimeout(() => panel.focus(), 10);
    }
    /**
     * Render the element list in the panel
     */
    renderElementList(panel, elements) {
      elements.forEach((el, index) => {
        const item = document.createElement("div");
        item.dataset.index = String(index);
        item.style.cssText = `
        padding: 5px 10px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: background 0.1s;
      `;
        const depthBar = document.createElement("span");
        const depth = this.getDepthFn(el);
        depthBar.style.cssText = `
        width: ${Math.min(depth * 3, 30)}px;
        height: 3px;
        background: ${this.getColorFn(depth)};
        border-radius: 2px;
        flex-shrink: 0;
      `;
        const indexNum = document.createElement("span");
        indexNum.style.cssText = `color: #666; width: 18px; text-align: right;`;
        indexNum.textContent = `${index + 1}`;
        const info = document.createElement("span");
        const tag = el.tagName.toLowerCase();
        const id = el.id ? `#${el.id}` : "";
        const cls = el.className && typeof el.className === "string" ? `.${el.className.split(" ")[0].substring(0, 15)}` : "";
        info.innerHTML = `<span style="color:#61afef">${tag}</span><span style="color:#e5c07b">${id}</span><span style="color:#98c379">${cls}</span>`;
        info.style.cssText = `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;`;
        item.appendChild(depthBar);
        item.appendChild(indexNum);
        item.appendChild(info);
        item.addEventListener("mouseenter", () => {
          item.style.background = "rgba(100, 100, 100, 0.3)";
        });
        item.addEventListener("mouseleave", () => {
          if (this.currentDepthIndex !== index) {
            item.style.background = "";
          }
        });
        item.addEventListener("click", () => {
          this.currentDepthIndex = index;
          this.highlightCallback?.(el);
          this.updateSelection();
        });
        panel.appendChild(item);
      });
    }
    /**
     * Setup keyboard navigation
     */
    setupKeyboardHandler(panel) {
      panel.addEventListener("keydown", async (e) => {
        const maxIndex = this.elementsAtCursor.length - 1;
        switch (e.key) {
          case "ArrowDown":
          case "Tab":
            if (!e.shiftKey) {
              e.preventDefault();
              e.stopPropagation();
              this.currentDepthIndex = Math.min(
                this.currentDepthIndex + 1,
                maxIndex
              );
              this.highlightCallback?.(
                this.elementsAtCursor[this.currentDepthIndex]
              );
              this.updateSelection();
            } else if (e.key === "Tab") {
              e.preventDefault();
              e.stopPropagation();
              this.currentDepthIndex = Math.max(this.currentDepthIndex - 1, 0);
              this.highlightCallback?.(
                this.elementsAtCursor[this.currentDepthIndex]
              );
              this.updateSelection();
            }
            break;
          case "ArrowUp":
            e.preventDefault();
            e.stopPropagation();
            this.currentDepthIndex = Math.max(this.currentDepthIndex - 1, 0);
            this.highlightCallback?.(
              this.elementsAtCursor[this.currentDepthIndex]
            );
            this.updateSelection();
            break;
          case "Enter":
            e.preventDefault();
            e.stopPropagation();
            await this.confirmSelection();
            break;
          case "Escape":
            e.preventDefault();
            e.stopPropagation();
            this.remove();
            break;
        }
      });
    }
    /**
     * Confirm current selection (copy debug info)
     */
    async confirmSelection() {
      if (this.elementsAtCursor.length === 0) return;
      const selectedElement = this.elementsAtCursor[this.currentDepthIndex];
      if (!selectedElement) return;
      const debugInfo = this.debugCollector.gatherElementDebugInfo(selectedElement);
      try {
        await navigator.clipboard.writeText(debugInfo);
        this.notificationManager.showNotification("\u2713 Copied!", "success");
        console.log("[ElementInspector] Copied debug info to clipboard");
        this.notificationManager.triggerCopyCallback();
      } catch (err) {
        console.error("[ElementInspector] Failed to copy:", err);
        this.notificationManager.showNotification("\u2717 Copy Failed", "error");
      }
    }
    /**
     * Update selection highlight in panel
     */
    updateSelection() {
      if (!this.panel) return;
      const items = this.panel.querySelectorAll("[data-index]");
      items.forEach((item, index) => {
        const el = item;
        if (index === this.currentDepthIndex) {
          el.style.background = "rgba(59, 130, 246, 0.4)";
          el.style.borderLeft = "2px solid #3b82f6";
          el.scrollIntoView({ block: "nearest" });
        } else {
          el.style.background = "";
          el.style.borderLeft = "";
        }
      });
    }
    /**
     * Navigate to next/previous element via scroll
     */
    navigate(direction) {
      if (this.elementsAtCursor.length <= 1) return;
      if (direction === "down") {
        this.currentDepthIndex = Math.min(
          this.currentDepthIndex + 1,
          this.elementsAtCursor.length - 1
        );
      } else {
        this.currentDepthIndex = Math.max(this.currentDepthIndex - 1, 0);
      }
      this.highlightCallback?.(this.elementsAtCursor[this.currentDepthIndex]);
      this.updateSelection();
    }
    /**
     * Remove the panel
     */
    remove() {
      if (this.panel) {
        this.panel.remove();
        this.panel = null;
      }
    }
    /**
     * Reset state
     */
    reset() {
      this.remove();
      this.elementsAtCursor = [];
      this.currentDepthIndex = 0;
    }
    /**
     * Check if panel is visible
     */
    isVisible() {
      return this.panel !== null;
    }
  };

  // ts/utils/_element-inspector/_LabelRenderer.ts
  var LabelRenderer = class {
    debugCollector;
    notificationManager;
    constructor(debugCollector, notificationManager) {
      this.debugCollector = debugCollector;
      this.notificationManager = notificationManager;
    }
    /**
     * Determine if a label should be shown for this element
     */
    shouldShowLabel(element, rect, depth) {
      if (element.id) {
        return rect.width > 20 && rect.height > 20;
      }
      if (rect.width > 100 || rect.height > 100) {
        return true;
      }
      const importantTags = [
        "header",
        "nav",
        "main",
        "section",
        "article",
        "aside",
        "footer",
        "form",
        "table"
      ];
      if (importantTags.includes(element.tagName.toLowerCase()) && (rect.width > 50 || rect.height > 50)) {
        return true;
      }
      const interactiveTags = ["button", "a", "input", "select", "textarea"];
      if (interactiveTags.includes(element.tagName.toLowerCase()) && (rect.width > 30 || rect.height > 30)) {
        return true;
      }
      if (depth > 8 && rect.width < 100 && rect.height < 100) {
        return false;
      }
      return false;
    }
    /**
     * Find non-overlapping position for a label
     */
    findLabelPosition(rect, occupiedPositions) {
      const scrollY = window.scrollY;
      const scrollX = window.scrollX;
      const positions = [
        { top: rect.top + scrollY - 24, left: rect.left + scrollX },
        { top: rect.top + scrollY - 24, left: rect.right + scrollX - 200 },
        { top: rect.top + scrollY + 4, left: rect.left + scrollX + 4 },
        { top: rect.top + scrollY + 4, left: rect.right + scrollX - 204 },
        { top: rect.bottom + scrollY + 4, left: rect.left + scrollX },
        { top: rect.bottom + scrollY + 4, left: rect.right + scrollX - 200 },
        {
          top: rect.top + scrollY + rect.height / 2 - 10,
          left: rect.left + scrollX - 210
        },
        {
          top: rect.top + scrollY + rect.height / 2 - 10,
          left: rect.right + scrollX + 10
        },
        { top: rect.top + scrollY - 48, left: rect.left + scrollX },
        { top: rect.bottom + scrollY + 28, left: rect.left + scrollX }
      ];
      for (const pos of positions) {
        if (!this.isPositionOccupied(pos, occupiedPositions)) {
          return { ...pos, isValid: true };
        }
      }
      return { top: 0, left: 0, isValid: false };
    }
    /**
     * Check if a position overlaps with occupied positions
     */
    isPositionOccupied(pos, occupiedPositions) {
      const labelWidth = 250;
      const labelHeight = 20;
      for (const occupied of occupiedPositions) {
        if (!(pos.left + labelWidth < occupied.left || pos.left > occupied.right || pos.top + labelHeight < occupied.top || pos.top > occupied.bottom)) {
          return true;
        }
      }
      return false;
    }
    /**
     * Create a label element for the given DOM element
     */
    createLabel(element, depth) {
      const tag = element.tagName.toLowerCase();
      const id = element.id;
      const classes = element.className;
      let labelText = `<span class="element-inspector-label-tag">${tag}</span>`;
      if (id) {
        labelText += ` <span class="element-inspector-label-id">#${id}</span>`;
      }
      if (classes && typeof classes === "string") {
        const classList = classes.split(/\s+/).filter((c) => c.length > 0);
        if (classList.length > 0) {
          const classPreview = classList.slice(0, 2).join(".");
          labelText += ` <span class="element-inspector-label-class">.${classPreview}</span>`;
          if (classList.length > 2) {
            labelText += `<span class="element-inspector-label-class">+${classList.length - 2}</span>`;
          }
        }
      }
      if (depth > 5) {
        labelText += ` <span style="color: #999; font-size: 9px;">d${depth}</span>`;
      }
      const label = document.createElement("div");
      label.className = "element-inspector-label";
      label.innerHTML = labelText;
      label.title = "Click to copy comprehensive debug info for AI";
      return label;
    }
    /**
     * Add hover highlight behavior to label
     */
    addHoverHighlight(label, box, element, onHover) {
      label.addEventListener("mouseenter", () => {
        onHover(box, element);
        box.classList.add("highlighted");
        if (element instanceof HTMLElement) {
          element.style.outline = "3px solid rgba(59, 130, 246, 0.8)";
          element.style.outlineOffset = "2px";
        }
      });
      label.addEventListener("mouseleave", () => {
        onHover(null, null);
        box.classList.remove("highlighted");
        if (element instanceof HTMLElement) {
          element.style.outline = "";
          element.style.outlineOffset = "";
        }
      });
    }
    /**
     * Add copy-to-clipboard behavior on right-click
     */
    addCopyToClipboard(label, element) {
      label.addEventListener("contextmenu", async (e) => {
        e.stopPropagation();
        e.preventDefault();
        const debugInfo = this.debugCollector.gatherElementDebugInfo(element);
        try {
          await navigator.clipboard.writeText(debugInfo);
          this.notificationManager.showNotification("\u2713 Copied!", "success");
          console.log("[ElementInspector] Copied debug info to clipboard");
          this.notificationManager.triggerCopyCallback();
        } catch (err) {
          console.error("[ElementInspector] Failed to copy:", err);
          this.notificationManager.showNotification("\u2717 Copy Failed", "error");
        }
      });
    }
  };

  // ts/utils/_element-inspector/_depth-utils.ts
  var DEPTH_COLORS = [
    "#3B82F6",
    // Blue (depth 0-2)
    "#10B981",
    // Green (depth 3-5)
    "#F59E0B",
    // Yellow (depth 6-8)
    "#EF4444",
    // Red (depth 9-11)
    "#EC4899"
    // Pink (depth 12+)
  ];
  function getDepth(element) {
    let depth = 0;
    let current = element;
    while (current && current !== document.body) {
      depth++;
      current = current.parentElement;
    }
    return depth;
  }
  function getColorForDepth(depth) {
    const index = Math.min(Math.floor(depth / 3), DEPTH_COLORS.length - 1);
    return DEPTH_COLORS[index];
  }

  // ts/utils/_element-inspector/_element-scanner.ts
  var ElementScanner = class _ElementScanner {
    elementBoxMap = /* @__PURE__ */ new Map();
    currentlyHoveredBox = null;
    currentlyHoveredElement = null;
    debugCollector;
    notificationManager;
    // Extracted managers
    layerPicker;
    labelRenderer;
    // Scan all elements but only render those in viewport
    // (viewport filter in renderBatch handles performance)
    static BATCH_SIZE = 1e4;
    static MIN_SIZE = 10;
    // Skip elements smaller than 10px
    // Pagination state
    currentBatchStart = 0;
    allVisibleElements = [];
    overlayContainerRef = null;
    // Overlapped element selection
    lastCursorX = 0;
    lastCursorY = 0;
    wheelHandler = null;
    directHighlightElement = null;
    constructor(debugCollector, notificationManager) {
      this.debugCollector = debugCollector;
      this.notificationManager = notificationManager;
      this.layerPicker = new LayerPickerPanel(
        debugCollector,
        notificationManager,
        (el) => getDepth(el),
        (depth) => getColorForDepth(depth)
      );
      this.layerPicker.setHighlightCallback((el) => {
        if (this.overlayContainerRef) {
          this.highlightElement(el, this.overlayContainerRef);
        }
      });
      this.labelRenderer = new LabelRenderer(debugCollector, notificationManager);
    }
    getElementBoxMap() {
      return this.elementBoxMap;
    }
    /**
     * Get currently selected depth index (from scroll wheel selection)
     */
    getCurrentDepthIndex() {
      return this.layerPicker.getCurrentDepthIndex();
    }
    /**
     * Get elements at the current cursor position (sorted by depth)
     */
    getElementsAtCursor() {
      return this.layerPicker.getElementsAtCursor();
    }
    /**
     * Get the currently selected element (via scroll wheel depth selection)
     */
    getDepthSelectedElement() {
      return this.layerPicker.getSelectedElement() || this.currentlyHoveredElement;
    }
    clearElementBoxMap() {
      this.elementBoxMap.clear();
      this.currentlyHoveredBox = null;
      this.currentlyHoveredElement = null;
      this.currentBatchStart = 0;
      this.allVisibleElements = [];
      this.overlayContainerRef = null;
      if (this.wheelHandler) {
        document.removeEventListener("wheel", this.wheelHandler);
        this.wheelHandler = null;
      }
      this.layerPicker.reset();
      this.clearDirectHighlight();
    }
    scanElements(overlayContainer) {
      this.overlayContainerRef = overlayContainer;
      if (this.allVisibleElements.length === 0) {
        this.collectVisibleElements();
      }
      this.renderBatch(overlayContainer);
      this.setupWheelHandler(overlayContainer);
    }
    /**
     * Collect all visible elements (run once on activation)
     */
    collectVisibleElements() {
      const startTime = performance.now();
      const allElements = document.querySelectorAll("*");
      for (const element of allElements) {
        if (!element || !element.tagName) continue;
        if (element.closest("#element-inspector-overlay")) continue;
        const tagName = element.tagName.toLowerCase();
        if (["script", "style", "link", "meta", "head", "noscript", "br"].includes(
          tagName
        )) {
          continue;
        }
        const rect = element.getBoundingClientRect();
        if (rect.width < _ElementScanner.MIN_SIZE || rect.height < _ElementScanner.MIN_SIZE) {
          continue;
        }
        if (element instanceof HTMLElement) {
          if (element.offsetParent === null && tagName !== "body" && tagName !== "html") {
            if (element.style.display === "none") continue;
          }
        }
        this.allVisibleElements.push(element);
      }
      const elapsed = (performance.now() - startTime).toFixed(1);
      console.log(
        `[ElementInspector] Found ${this.allVisibleElements.length} visible elements in ${elapsed}ms`
      );
    }
    /**
     * Render current batch of elements
     */
    renderBatch(overlayContainer) {
      const startTime = performance.now();
      const fragment = document.createDocumentFragment();
      const occupiedPositions = [];
      const scrollY = window.scrollY;
      const scrollX = window.scrollX;
      const batchEnd = Math.min(
        this.currentBatchStart + _ElementScanner.BATCH_SIZE,
        this.allVisibleElements.length
      );
      let count = 0;
      for (let i = this.currentBatchStart; i < batchEnd; i++) {
        const element = this.allVisibleElements[i];
        const rect = element.getBoundingClientRect();
        const margin = 100;
        if (rect.bottom < -margin || rect.top > window.innerHeight + margin || rect.right < -margin || rect.left > window.innerWidth + margin) {
          continue;
        }
        const depth = getDepth(element);
        const color = getColorForDepth(depth);
        const tagName = element.tagName.toLowerCase();
        const area = rect.width * rect.height;
        const borderWidth = area > 1e5 ? 1 : area > 1e4 ? 1.5 : 2;
        const box = document.createElement("div");
        box.className = "element-inspector-box";
        box.style.cssText = `
                top: ${rect.top + scrollY}px;
                left: ${rect.left + scrollX}px;
                width: ${rect.width}px;
                height: ${rect.height}px;
                border-color: ${color};
                border-width: ${borderWidth}px;
            `;
        const id = element.id ? `#${element.id}` : "";
        box.title = `Right-click to copy | Scroll to cycle depth: ${tagName}${id}`;
        this.elementBoxMap.set(box, element);
        box.addEventListener("mouseenter", () => {
          this.currentlyHoveredBox = box;
          this.currentlyHoveredElement = element;
        });
        box.addEventListener("mouseleave", () => {
          if (this.currentlyHoveredBox === box) {
            this.currentlyHoveredBox = null;
            this.currentlyHoveredElement = null;
          }
        });
        box.addEventListener("click", (e) => {
          box.style.pointerEvents = "none";
          const underlyingElement = document.elementFromPoint(
            e.clientX,
            e.clientY
          );
          box.style.pointerEvents = "";
          if (underlyingElement && underlyingElement !== box) {
            const clickEvent = new MouseEvent("click", {
              bubbles: true,
              cancelable: true,
              view: window,
              clientX: e.clientX,
              clientY: e.clientY
            });
            underlyingElement.dispatchEvent(clickEvent);
          }
        });
        box.addEventListener("contextmenu", async (e) => {
          e.preventDefault();
          e.stopPropagation();
          const selectedElement = this.currentlyHoveredElement || element;
          const selectedBox = this.currentlyHoveredBox || box;
          selectedBox.classList.add("highlighted");
          const debugInfo = this.debugCollector.gatherElementDebugInfo(selectedElement);
          try {
            await navigator.clipboard.writeText(debugInfo);
            this.notificationManager.showNotification("\u2713 Copied!", "success");
            console.log("[ElementInspector] Copied:", debugInfo);
            this.notificationManager.triggerCopyCallback();
          } catch (err) {
            console.error("[ElementInspector] Copy failed:", err);
            this.notificationManager.showNotification("\u2717 Copy Failed", "error");
            selectedBox.classList.remove("highlighted");
          }
        });
        const shouldShowLabel = this.labelRenderer.shouldShowLabel(
          element,
          rect,
          depth
        );
        if (shouldShowLabel) {
          const label = this.labelRenderer.createLabel(element, depth);
          if (label) {
            const labelPos = this.labelRenderer.findLabelPosition(
              rect,
              occupiedPositions
            );
            if (labelPos.isValid) {
              label.style.top = `${labelPos.top}px`;
              label.style.left = `${labelPos.left}px`;
              this.labelRenderer.addCopyToClipboard(label, element);
              this.labelRenderer.addHoverHighlight(
                label,
                box,
                element,
                (b, e) => {
                  this.currentlyHoveredBox = b;
                  this.currentlyHoveredElement = e;
                }
              );
              const labelPadding = 8;
              occupiedPositions.push({
                top: labelPos.top - labelPadding,
                left: labelPos.left - labelPadding,
                bottom: labelPos.top + 20 + labelPadding,
                right: labelPos.left + 250 + labelPadding
              });
              fragment.appendChild(label);
            }
          }
        }
        fragment.appendChild(box);
        count++;
      }
      overlayContainer.appendChild(fragment);
      const elapsed = (performance.now() - startTime).toFixed(1);
      const total = this.allVisibleElements.length;
      const remaining = total - batchEnd;
      console.log(
        `[ElementInspector] Rendered ${count} elements (${this.currentBatchStart + 1}-${batchEnd}/${total}) in ${elapsed}ms` + (remaining > 0 ? ` | Ctrl+I for next ${Math.min(remaining, _ElementScanner.BATCH_SIZE)}` : "")
      );
      if (remaining > 0) {
        this.notificationManager.showNotification(
          `${batchEnd}/${total} elements | Ctrl+I for more`,
          "success",
          2e3
        );
      }
    }
    /**
     * Load next batch of elements (called by Ctrl+I)
     */
    loadNextBatch() {
      if (!this.overlayContainerRef) return false;
      const total = this.allVisibleElements.length;
      const nextStart = this.currentBatchStart + _ElementScanner.BATCH_SIZE;
      if (nextStart >= total) {
        this.notificationManager.showNotification(
          "All elements loaded",
          "success"
        );
        return false;
      }
      this.currentBatchStart = nextStart;
      this.renderBatch(this.overlayContainerRef);
      return true;
    }
    /**
     * Check if more batches are available
     */
    hasMoreBatches() {
      return this.currentBatchStart + _ElementScanner.BATCH_SIZE < this.allVisibleElements.length;
    }
    /**
     * Setup scroll wheel handler for cycling through overlapped elements
     */
    setupWheelHandler(_overlayContainer) {
      this.wheelHandler = (e) => {
        if (e.target?.closest?.(".element-inspector-layer-picker"))
          return;
        const cursorMoved = Math.abs(e.clientX - this.lastCursorX) > 5 || Math.abs(e.clientY - this.lastCursorY) > 5;
        if (cursorMoved) {
          this.lastCursorX = e.clientX;
          this.lastCursorY = e.clientY;
          const elements2 = this.getElementsAtPoint(e.clientX, e.clientY);
          this.layerPicker.show(e.clientX, e.clientY, elements2);
        }
        const elements = this.layerPicker.getElementsAtCursor();
        if (elements.length <= 1) {
          this.layerPicker.remove();
          return;
        }
        e.preventDefault();
        e.stopPropagation();
        this.layerPicker.navigate(e.deltaY > 0 ? "down" : "up");
      };
      document.addEventListener("wheel", this.wheelHandler, { passive: false });
    }
    /**
     * Get all elements at a specific point, sorted from deepest to shallowest
     */
    getElementsAtPoint(x, y) {
      const elements = [];
      const allAtPoint = document.elementsFromPoint(x, y);
      for (const el of allAtPoint) {
        if (!el || !el.tagName) continue;
        if (el.closest("#element-inspector-overlay")) continue;
        if (el.closest(".element-inspector-layer-picker")) continue;
        const tag = el.tagName.toLowerCase();
        if (["html", "body", "script", "style", "head"].includes(tag)) continue;
        elements.push(el);
      }
      return elements;
    }
    /**
     * Clear direct highlight on element (for elements not in batch)
     */
    clearDirectHighlight() {
      if (this.directHighlightElement instanceof HTMLElement) {
        this.directHighlightElement.style.outline = "";
        this.directHighlightElement.style.outlineOffset = "";
      }
      this.directHighlightElement = null;
    }
    /**
     * Highlight a specific element and update hover state
     */
    highlightElement(element, overlayContainer) {
      overlayContainer.querySelectorAll(".element-inspector-box.highlighted").forEach((box) => {
        box.classList.remove("highlighted");
      });
      this.clearDirectHighlight();
      let found = false;
      for (const [box, el] of this.elementBoxMap) {
        if (el === element) {
          box.classList.add("highlighted");
          this.currentlyHoveredBox = box;
          this.currentlyHoveredElement = element;
          found = true;
          break;
        }
      }
      if (!found && element instanceof HTMLElement) {
        element.style.outline = "3px solid #3b82f6";
        element.style.outlineOffset = "2px";
        this.directHighlightElement = element;
        this.currentlyHoveredElement = element;
      }
    }
  };

  // ts/utils/_element-inspector/_debug-info-collector.ts
  var DebugInfoCollector = class {
    gatherElementDebugInfo(element) {
      const info = {};
      info.url = window.location.href;
      info.timestamp = (/* @__PURE__ */ new Date()).toISOString();
      const className = typeof element.className === "string" ? element.className : "";
      info.element = {
        tag: element.tagName.toLowerCase(),
        id: element.id || null,
        classes: className ? className.split(/\s+/).filter((c) => c) : [],
        selector: this.buildCSSSelector(element),
        xpath: this.getXPath(element)
      };
      info.attributes = {};
      for (let i = 0; i < element.attributes.length; i++) {
        const attr = element.attributes[i];
        info.attributes[attr.name] = attr.value;
      }
      if (element instanceof HTMLElement) {
        const computed = window.getComputedStyle(element);
        info.styles = {
          display: computed.display,
          position: computed.position,
          width: computed.width,
          height: computed.height,
          margin: computed.margin,
          padding: computed.padding,
          backgroundColor: computed.backgroundColor,
          color: computed.color,
          fontSize: computed.fontSize,
          fontFamily: computed.fontFamily,
          zIndex: computed.zIndex,
          opacity: computed.opacity,
          visibility: computed.visibility,
          overflow: computed.overflow
        };
        if (element.style.cssText) {
          info.inlineStyles = element.style.cssText;
        }
        const rect = element.getBoundingClientRect();
        info.dimensions = {
          width: rect.width,
          height: rect.height,
          top: rect.top,
          left: rect.left,
          bottom: rect.bottom,
          right: rect.right
        };
        info.scroll = {
          scrollTop: element.scrollTop,
          scrollLeft: element.scrollLeft,
          scrollHeight: element.scrollHeight,
          scrollWidth: element.scrollWidth
        };
        info.content = {
          innerHTML: element.innerHTML.substring(0, 200) + (element.innerHTML.length > 200 ? "..." : ""),
          textContent: element.textContent?.substring(0, 200) + (element.textContent && element.textContent.length > 200 ? "..." : "")
        };
      }
      info.eventListeners = this.getEventListeners(element);
      info.parentChain = this.getParentChain(element);
      info.appliedStylesheets = this.getAppliedStylesheets();
      info.matchingCSSRules = this.getMatchingCSSRules(element);
      return this.formatDebugInfoForAI(info);
    }
    buildCSSSelector(element) {
      const tag = element.tagName.toLowerCase();
      const id = element.id;
      const classes = element.className;
      let selector = tag;
      if (id) {
        selector += `#${id}`;
      }
      if (classes && typeof classes === "string") {
        const classList = classes.split(/\s+/).filter((c) => c);
        if (classList.length > 0) {
          selector += `.${classList.join(".")}`;
        }
      }
      return selector;
    }
    getXPath(element) {
      if (element.id) {
        return `//*[@id="${element.id}"]`;
      }
      const parts = [];
      let current = element;
      while (current && current.nodeType === Node.ELEMENT_NODE) {
        let index = 0;
        let sibling = current.previousSibling;
        while (sibling) {
          if (sibling.nodeType === Node.ELEMENT_NODE && sibling.nodeName === current.nodeName) {
            index++;
          }
          sibling = sibling.previousSibling;
        }
        const tagName = current.nodeName.toLowerCase();
        const pathIndex = index > 0 ? `[${index + 1}]` : "";
        parts.unshift(tagName + pathIndex);
        current = current.parentElement;
      }
      return "/" + parts.join("/");
    }
    getEventListeners(element) {
      const listeners = [];
      const eventAttrs = [
        "onclick",
        "onload",
        "onchange",
        "onsubmit",
        "onmouseover",
        "onmouseout"
      ];
      eventAttrs.forEach((attr) => {
        if (element.hasAttribute(attr)) {
          listeners.push(attr);
        }
      });
      return listeners;
    }
    getParentChain(element) {
      const chain = [];
      let current = element.parentElement;
      let depth = 0;
      while (current && depth < 5) {
        chain.push(this.buildCSSSelector(current));
        current = current.parentElement;
        depth++;
      }
      return chain;
    }
    getAppliedStylesheets() {
      const sheets = [];
      for (let i = 0; i < document.styleSheets.length; i++) {
        try {
          const sheet = document.styleSheets[i];
          if (sheet.href) {
            sheets.push(sheet.href);
          } else if (sheet.ownerNode) {
            sheets.push("<inline style>");
          }
        } catch (e) {
          sheets.push("<cross-origin stylesheet>");
        }
      }
      return sheets;
    }
    getMatchingCSSRules(element) {
      const matchingRules = [];
      for (let i = 0; i < document.styleSheets.length; i++) {
        try {
          const sheet = document.styleSheets[i];
          if (!sheet.cssRules) continue;
          for (let j = 0; j < sheet.cssRules.length; j++) {
            const rule = sheet.cssRules[j];
            if (rule instanceof CSSStyleRule) {
              try {
                if (element.matches(rule.selectorText)) {
                  matchingRules.push({
                    selector: rule.selectorText,
                    cssText: rule.cssText.substring(0, 200) + (rule.cssText.length > 200 ? "..." : ""),
                    source: sheet.href || "<inline style>",
                    ruleIndex: j
                  });
                }
              } catch (e) {
              }
            }
          }
        } catch (e) {
        }
      }
      return matchingRules;
    }
    formatDebugInfoForAI(info) {
      return `# Element Debug Information

## Page Context
- URL: ${info.url}
- Timestamp: ${info.timestamp}

## Element Identification
- Tag: <${info.element.tag}>
- ID: ${info.element.id || "none"}
- Classes: ${info.element.classes.join(", ") || "none"}
- CSS Selector: ${info.element.selector}
- XPath: ${info.element.xpath}

## Attributes
${Object.entries(info.attributes).map(([key, value]) => `- ${key}: ${value}`).join("\n")}

## Computed Styles
${Object.entries(info.styles || {}).map(([key, value]) => `- ${key}: ${value}`).join("\n")}

${info.inlineStyles ? `## Inline Styles
${info.inlineStyles}
` : ""}

## Dimensions & Position
- Width: ${info.dimensions?.width}px
- Height: ${info.dimensions?.height}px
- Top: ${info.dimensions?.top}px
- Left: ${info.dimensions?.left}px

## Scroll State
- scrollTop: ${info.scroll?.scrollTop}
- scrollLeft: ${info.scroll?.scrollLeft}

## Content (truncated)
${info.content?.textContent || "none"}

## Event Listeners
${info.eventListeners.length > 0 ? info.eventListeners.join(", ") : "none detected"}

## Parent Chain
${info.parentChain.map((p, i) => `${i + 1}. ${p}`).join("\n")}

## Applied Stylesheets
${info.appliedStylesheets.slice(0, 10).map((s, i) => `${i + 1}. ${s}`).join("\n")}

## Matching CSS Rules (${info.matchingCSSRules?.length || 0} rules)
${info.matchingCSSRules && info.matchingCSSRules.length > 0 ? info.matchingCSSRules.slice(0, 10).map(
        (rule, i) => `
### ${i + 1}. ${rule.selector}
- Source: ${rule.source}
- Rule Index: ${rule.ruleIndex}
- CSS: ${rule.cssText}
`
      ).join("\n") : "No matching rules found (may be due to CORS restrictions)"}

---
This debug information was captured by Element Inspector and can be used for AI-assisted debugging.
Note: Exact CSS line numbers require browser DevTools API access.
`;
    }
  };

  // ts/utils/_element-inspector/_selection-manager.ts
  var SelectionManager = class {
    selectionMode = false;
    selectionStart = null;
    selectionRect = null;
    selectionOverlay = null;
    currentlySelectedElements = /* @__PURE__ */ new Set();
    elementBoxMap;
    debugCollector;
    notificationManager;
    elementScanner = null;
    constructor(elementBoxMap, debugCollector, notificationManager) {
      this.elementBoxMap = elementBoxMap;
      this.debugCollector = debugCollector;
      this.notificationManager = notificationManager;
    }
    /**
     * Set the element scanner reference for depth-aware selection
     */
    setElementScanner(scanner) {
      this.elementScanner = scanner;
    }
    isActive() {
      return this.selectionMode;
    }
    startSelectionMode() {
      this.selectionMode = true;
      document.body.classList.add("element-inspector-selection-mode");
      this.selectionOverlay = document.createElement("div");
      this.selectionOverlay.className = "selection-overlay";
      document.body.appendChild(this.selectionOverlay);
      this.notificationManager.showNotification("Drag to select area", "success");
      document.addEventListener("mousedown", this.onSelectionMouseDown);
      document.addEventListener("mousemove", this.onSelectionMouseMove);
      document.addEventListener("mouseup", this.onSelectionMouseUp);
    }
    cancelSelectionMode() {
      this.selectionMode = false;
      document.body.classList.remove("element-inspector-selection-mode");
      this.clearSelectionHighlights();
      if (this.selectionOverlay) {
        this.selectionOverlay.remove();
        this.selectionOverlay = null;
      }
      if (this.selectionRect) {
        this.selectionRect.remove();
        this.selectionRect = null;
      }
      document.removeEventListener("mousedown", this.onSelectionMouseDown);
      document.removeEventListener("mousemove", this.onSelectionMouseMove);
      document.removeEventListener("mouseup", this.onSelectionMouseUp);
      this.selectionStart = null;
    }
    onSelectionMouseDown = (e) => {
      if (!this.selectionMode) return;
      e.preventDefault();
      this.selectionStart = {
        x: e.clientX,
        y: e.clientY
      };
      this.selectionRect = document.createElement("div");
      this.selectionRect.className = "selection-rectangle";
      this.selectionRect.style.left = `${e.clientX}px`;
      this.selectionRect.style.top = `${e.clientY}px`;
      this.selectionRect.style.width = "0px";
      this.selectionRect.style.height = "0px";
      document.body.appendChild(this.selectionRect);
    };
    onSelectionMouseMove = (e) => {
      if (!this.selectionMode || !this.selectionStart || !this.selectionRect) {
        return;
      }
      e.preventDefault();
      const currentX = e.clientX;
      const currentY = e.clientY;
      const left = Math.min(this.selectionStart.x, currentX);
      const top = Math.min(this.selectionStart.y, currentY);
      const width = Math.abs(currentX - this.selectionStart.x);
      const height = Math.abs(currentY - this.selectionStart.y);
      this.selectionRect.style.left = `${left}px`;
      this.selectionRect.style.top = `${top}px`;
      this.selectionRect.style.width = `${width}px`;
      this.selectionRect.style.height = `${height}px`;
      this.updateSelectionHighlights({ left, top, width, height });
    };
    onSelectionMouseUp = async (e) => {
      if (!this.selectionMode || !this.selectionStart || !this.selectionRect)
        return;
      e.preventDefault();
      const currentX = e.clientX;
      const currentY = e.clientY;
      const left = Math.min(this.selectionStart.x, currentX);
      const top = Math.min(this.selectionStart.y, currentY);
      const width = Math.abs(currentX - this.selectionStart.x);
      const height = Math.abs(currentY - this.selectionStart.y);
      if (width < 5 || height < 5) {
        this.cancelSelectionMode();
        this.notificationManager.showNotification("Selection too small", "error");
        return;
      }
      const selectedElements = this.findElementsInRect({
        left,
        top,
        width,
        height
      });
      console.log(
        `[ElementInspector] Found ${selectedElements.length} elements in selection`
      );
      const selectionInfo = this.gatherSelectionInfo(selectedElements, {
        left,
        top,
        width,
        height
      });
      try {
        await navigator.clipboard.writeText(selectionInfo);
        this.notificationManager.showNotification(
          `\u2713 ${selectedElements.length} elements copied!`,
          "success"
        );
        console.log("[ElementInspector] Selection info copied to clipboard");
        this.notificationManager.triggerCopyCallback();
      } catch (err) {
        console.error("[ElementInspector] Failed to copy:", err);
        this.notificationManager.showNotification("\u2717 Copy Failed", "error");
      }
      this.cancelSelectionMode();
    };
    updateSelectionHighlights(rect) {
      const selectedElements = this.findElementsInRect(rect);
      const newSelection = new Set(selectedElements);
      const selectedBoxes = /* @__PURE__ */ new Set();
      this.elementBoxMap.forEach((element, box) => {
        if (newSelection.has(element)) {
          selectedBoxes.add(box);
        }
      });
      this.elementBoxMap.forEach((element, box) => {
        if (this.currentlySelectedElements.has(element) && !newSelection.has(element)) {
          box.style.borderWidth = "2px";
          box.style.background = "rgba(255, 255, 255, 0.01)";
          box.style.transform = "";
          box.style.zIndex = "";
          if (element instanceof HTMLElement) {
            element.classList.remove("element-inspector-selected");
          }
        }
      });
      selectedBoxes.forEach((box) => {
        const element = this.elementBoxMap.get(box);
        if (element && !this.currentlySelectedElements.has(element)) {
          const depth = this.getDepth(element);
          const color = this.getColorForDepth(depth);
          box.style.borderWidth = "4px";
          box.style.background = this.hexToRgba(color, 0.25);
          box.style.transform = "scale(1.02)";
          box.style.zIndex = "1000000";
          if (element instanceof HTMLElement) {
            element.classList.add("element-inspector-selected");
          }
        }
      });
      this.currentlySelectedElements = newSelection;
    }
    clearSelectionHighlights() {
      this.elementBoxMap.forEach((element, box) => {
        if (this.currentlySelectedElements.has(element)) {
          box.style.borderWidth = "2px";
          box.style.background = "rgba(255, 255, 255, 0.01)";
          box.style.transform = "";
          box.style.zIndex = "";
        }
      });
      this.currentlySelectedElements.forEach((element) => {
        if (element instanceof HTMLElement) {
          element.classList.remove("element-inspector-selected");
        }
      });
      this.currentlySelectedElements.clear();
    }
    hexToRgba(hex, alpha) {
      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
      if (!result) return `rgba(59, 130, 246, ${alpha})`;
      const r = parseInt(result[1], 16);
      const g = parseInt(result[2], 16);
      const b = parseInt(result[3], 16);
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
    findElementsInRect(rect) {
      const selectedElements = [];
      const allElements = document.querySelectorAll("*");
      const selectionRect = {
        left: rect.left,
        top: rect.top,
        right: rect.left + rect.width,
        bottom: rect.top + rect.height
      };
      let targetDepth = null;
      const depthTolerance = 2;
      if (this.elementScanner) {
        const depthSelectedElement = this.elementScanner.getDepthSelectedElement();
        if (depthSelectedElement) {
          targetDepth = this.getDepth(depthSelectedElement);
          console.log(
            `[SelectionManager] Filtering by depth: ${targetDepth} (+-${depthTolerance})`
          );
        }
      }
      allElements.forEach((element) => {
        if (element.closest("#element-inspector-overlay") || element.classList.contains("selection-rectangle") || element.classList.contains("selection-overlay") || element.closest(".element-inspector-layer-picker")) {
          return;
        }
        const tagName = element.tagName.toLowerCase();
        if ([
          "script",
          "style",
          "link",
          "meta",
          "head",
          "noscript",
          "br",
          "html",
          "body"
        ].includes(tagName)) {
          return;
        }
        if (element instanceof HTMLElement) {
          const computed = window.getComputedStyle(element);
          if (computed.display === "none" || computed.visibility === "hidden") {
            return;
          }
        }
        if (targetDepth !== null) {
          const elementDepth = this.getDepth(element);
          if (Math.abs(elementDepth - targetDepth) > depthTolerance) {
            return;
          }
        }
        const elementRect = element.getBoundingClientRect();
        if (elementRect.width < 10 || elementRect.height < 10) {
          return;
        }
        const elementBounds = {
          left: elementRect.left,
          top: elementRect.top,
          right: elementRect.right,
          bottom: elementRect.bottom
        };
        const intersects = !(elementBounds.right < selectionRect.left || elementBounds.left > selectionRect.right || elementBounds.bottom < selectionRect.top || elementBounds.top > selectionRect.bottom);
        if (intersects) {
          selectedElements.push(element);
        }
      });
      return selectedElements;
    }
    gatherSelectionInfo(elements, rect) {
      let info = `# Rectangle Selection Debug Information

## Selection Area
- Position: (${Math.round(rect.left)}, ${Math.round(rect.top)})
- Size: ${Math.round(rect.width)}x${Math.round(rect.height)}px
- URL: ${window.location.href}
- Timestamp: ${(/* @__PURE__ */ new Date()).toISOString()}
- Elements Found: ${elements.length}

---

`;
      const elementTypes = {};
      elements.forEach((el) => {
        const tag = el.tagName.toLowerCase();
        elementTypes[tag] = (elementTypes[tag] || 0) + 1;
      });
      info += `## Element Type Summary
`;
      Object.entries(elementTypes).sort((a, b) => b[1] - a[1]).forEach(([tag, count]) => {
        info += `- ${tag}: ${count}
`;
      });
      info += `
---

`;
      const maxDetailedElements = 20;
      const detailedCount = Math.min(elements.length, maxDetailedElements);
      info += `## Detailed Element Information (${detailedCount} of ${elements.length} elements)

`;
      info += `> **Note**: Showing comprehensive debug info for the first ${detailedCount} elements.
`;
      info += `> Each element includes: attributes, computed styles, dimensions, matching CSS rules, etc.

`;
      info += `---

`;
      elements.slice(0, maxDetailedElements).forEach((element, index) => {
        info += `# Element ${index + 1}/${elements.length}

`;
        const elementDebugInfo = this.debugCollector.gatherElementDebugInfo(element);
        info += elementDebugInfo;
        info += `
${"=".repeat(80)}

`;
      });
      if (elements.length > maxDetailedElements) {
        info += `## Remaining Elements (${elements.length - maxDetailedElements} elements - basic info)

`;
        elements.slice(maxDetailedElements).forEach((element, index) => {
          const actualIndex = maxDetailedElements + index + 1;
          const selector = this.debugCollector.buildCSSSelector(element);
          const rect2 = element.getBoundingClientRect();
          const text = element.textContent?.trim().substring(0, 50);
          info += `### ${actualIndex}. ${selector}
`;
          info += `- Position: (${Math.round(rect2.left)}, ${Math.round(rect2.top)}) | Size: ${Math.round(rect2.width)}x${Math.round(rect2.height)}px
`;
          if (text) info += `- Text: "${text}${text.length > 50 ? "..." : ""}"
`;
          info += `
`;
        });
      }
      info += `
---
Generated by Element Inspector - Rectangle Selection Mode (Enhanced)
`;
      info += `Press Ctrl+Alt+I to start selection mode again.
`;
      return info;
    }
    getDepth(element) {
      let depth = 0;
      let current = element;
      while (current && current !== document.body) {
        depth++;
        current = current.parentElement;
      }
      return depth;
    }
    getColorForDepth(depth) {
      const colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#EC4899"];
      const index = Math.min(Math.floor(depth / 3), colors.length - 1);
      return colors[index];
    }
  };

  // ts/utils/_element-inspector/_notification-manager.ts
  var NotificationManager = class {
    onCopyCallback = null;
    /**
     * Set callback to be called after successful copy
     * Used to trigger ESC/deactivate after copy
     */
    setOnCopyCallback(callback) {
      this.onCopyCallback = callback;
    }
    /**
     * Trigger the copy callback (called after successful copy)
     */
    triggerCopyCallback() {
      if (this.onCopyCallback) {
        setTimeout(() => {
          this.onCopyCallback?.();
        }, 400);
      }
    }
    showNotification(message, type, duration = 1e3) {
      const notification = document.createElement("div");
      notification.textContent = message;
      notification.style.cssText = `
            position: fixed;
            top: 16px;
            right: 16px;
            padding: 10px 20px;
            background: ${type === "success" ? "rgba(16, 185, 129, 0.95)" : "rgba(239, 68, 68, 0.95)"};
            color: white;
            border-radius: 6px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 13px;
            font-weight: 600;
            z-index: 10000000;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
            opacity: 0;
            transform: translateY(-10px) scale(0.95);
            transition: opacity 0.2s ease, transform 0.2s ease;
        `;
      document.body.appendChild(notification);
      requestAnimationFrame(() => {
        notification.style.opacity = "1";
        notification.style.transform = "translateY(0) scale(1)";
      });
      setTimeout(() => {
        notification.style.opacity = "0";
        notification.style.transform = "translateY(-10px) scale(0.95)";
        setTimeout(() => notification.remove(), 200);
      }, duration);
    }
    showCameraFlash() {
      const flash = document.createElement("div");
      flash.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.4);
            z-index: 9999999;
            pointer-events: none;
            opacity: 1;
            transition: opacity 0.1s ease;
        `;
      document.body.appendChild(flash);
      setTimeout(() => {
        flash.style.opacity = "0";
      }, 30);
      setTimeout(() => {
        flash.remove();
      }, 130);
    }
  };

  // ts/utils/_element-inspector/_page-structure-exporter.ts
  var PageStructureExporter = class {
    notificationManager;
    constructor(notificationManager) {
      this.notificationManager = notificationManager;
    }
    async copyPageStructure() {
      console.log("[ElementInspector] Generating full page structure...");
      this.notificationManager.showCameraFlash();
      const structure = this.generatePageStructure();
      try {
        await navigator.clipboard.writeText(structure);
        console.log("[ElementInspector] Page structure copied to clipboard!");
        this.notificationManager.showNotification(
          "\u2713 Page structure copied!",
          "success"
        );
        this.notificationManager.triggerCopyCallback();
      } catch (err) {
        console.error("[ElementInspector] Failed to copy page structure:", err);
        this.notificationManager.showNotification("\u2717 Copy Failed", "error");
      }
    }
    generatePageStructure() {
      const info = {
        url: window.location.href,
        timestamp: (/* @__PURE__ */ new Date()).toISOString(),
        viewport: {
          width: window.innerWidth,
          height: window.innerHeight,
          scrollX: window.scrollX,
          scrollY: window.scrollY
        },
        document: {
          title: document.title,
          doctype: document.doctype ? document.doctype.name : "none",
          characterSet: document.characterSet,
          readyState: document.readyState
        },
        structure: this.buildElementTree(document.body, 0, 10),
        stylesheets: this.getAllStylesheets(),
        scripts: this.getAllScripts()
      };
      return this.formatPageStructureForAI(info);
    }
    buildElementTree(element, depth, maxDepth) {
      if (depth > maxDepth) {
        return { truncated: true };
      }
      const className = typeof element.className === "string" ? element.className : "";
      const node = {
        tag: element.tagName.toLowerCase(),
        id: element.id || void 0,
        classes: className ? className.split(/\s+/).filter((c) => c) : void 0
      };
      const importantAttrs = [
        "href",
        "src",
        "type",
        "name",
        "value",
        "data-*",
        "aria-*",
        "title",
        "alt",
        "placeholder",
        "role"
      ];
      const attrs = {};
      for (let i = 0; i < element.attributes.length; i++) {
        const attr = element.attributes[i];
        if (importantAttrs.some((pattern) => {
          if (pattern.endsWith("*")) {
            return attr.name.startsWith(pattern.slice(0, -1));
          }
          return attr.name === pattern;
        })) {
          attrs[attr.name] = attr.value;
        }
      }
      if (Object.keys(attrs).length > 0) {
        node.attributes = attrs;
      }
      const textContent = this.getDirectTextContent(element);
      if (textContent) {
        node.text = textContent;
      }
      const children = [];
      for (let i = 0; i < element.children.length; i++) {
        const child = element.children[i];
        if (child.tagName !== "SCRIPT" && child.tagName !== "STYLE") {
          children.push(this.buildElementTree(child, depth + 1, maxDepth));
        }
      }
      if (children.length > 0) {
        node.children = children;
      }
      return node;
    }
    /**
     * Get direct text content of an element (excluding child element text)
     */
    getDirectTextContent(element) {
      let text = "";
      for (let i = 0; i < element.childNodes.length; i++) {
        const node = element.childNodes[i];
        if (node.nodeType === Node.TEXT_NODE) {
          const trimmed = (node.textContent || "").trim();
          if (trimmed) {
            text += (text ? " " : "") + trimmed;
          }
        }
      }
      if (text.length > 200) {
        text = text.substring(0, 200) + "...";
      }
      return text || void 0;
    }
    getAllStylesheets() {
      const sheets = [];
      for (let i = 0; i < document.styleSheets.length; i++) {
        try {
          const sheet = document.styleSheets[i];
          const sheetInfo = {
            index: i,
            href: sheet.href || "<inline>",
            ruleCount: sheet.cssRules?.length || 0
          };
          if (sheet.cssRules && sheet.cssRules.length > 0) {
            const sampleRules = [];
            for (let j = 0; j < Math.min(5, sheet.cssRules.length); j++) {
              sampleRules.push(sheet.cssRules[j].cssText);
            }
            sheetInfo.sampleRules = sampleRules;
          }
          sheets.push(sheetInfo);
        } catch (e) {
          sheets.push({
            index: i,
            href: "<cross-origin or restricted>",
            error: "Cannot access due to CORS"
          });
        }
      }
      return sheets;
    }
    getAllScripts() {
      const scripts = [];
      const scriptElements = document.querySelectorAll("script");
      scriptElements.forEach((script, index) => {
        scripts.push({
          index,
          src: script.src || "<inline>",
          type: script.type || "text/javascript",
          async: script.async,
          defer: script.defer
        });
      });
      return scripts;
    }
    formatPageStructureForAI(info) {
      return `# Full Page Structure

## Page Information
- URL: ${info.url}
- Title: ${info.document.title}
- Timestamp: ${info.timestamp}
- Viewport: ${info.viewport.width}x${info.viewport.height}
- Scroll Position: (${info.viewport.scrollX}, ${info.viewport.scrollY})

## Document Structure
\`\`\`json
${JSON.stringify(info.structure, null, 2)}
\`\`\`

## Stylesheets (${info.stylesheets.length} total)
${info.stylesheets.map(
        (s, i) => `
### ${i + 1}. ${s.href}
- Rules: ${s.ruleCount}
${s.sampleRules ? `- Sample Rules:
${s.sampleRules.map((r) => `  - ${r.substring(0, 100)}...`).join("\n")}` : ""}
${s.error ? `- Error: ${s.error}` : ""}
`
      ).join("\n")}

## Scripts (${info.scripts.length} total)
${info.scripts.map((s, i) => `${i + 1}. ${s.src} ${s.async ? "[async]" : ""} ${s.defer ? "[defer]" : ""}`).join("\n")}

---
Generated by Element Inspector - Full page structure for AI-assisted debugging.
Press Alt+I to toggle element inspector overlay.
`;
    }
  };

  // ts/utils/_element-inspector/_console-collector.ts
  var ConsoleCollector = class {
    notificationManager;
    consoleLogs = [];
    networkErrors = [];
    maxLogs = 1e3;
    isCapturing = false;
    // Store original console methods
    originalConsole;
    constructor(notificationManager) {
      this.notificationManager = notificationManager;
      this.originalConsole = {
        log: console.log.bind(console),
        warn: console.warn.bind(console),
        error: console.error.bind(console),
        info: console.info.bind(console),
        debug: console.debug.bind(console)
      };
      this.startCapturing();
      this.captureNetworkErrors();
    }
    /**
     * Capture network errors (404s, etc.) using Performance API
     */
    captureNetworkErrors() {
      window.addEventListener(
        "error",
        (e) => {
          if (e.target && e.target.tagName) {
            const target = e.target;
            const src = target.src || target.href || "";
            if (src) {
              this.networkErrors.push(`Failed to load resource: ${src}`);
            }
          }
        },
        true
      );
    }
    startCapturing() {
      if (this.isCapturing) return;
      this.isCapturing = true;
      const self = this;
      console.log = function(...args) {
        self.captureLog("log", args);
        self.originalConsole.log.apply(console, args);
      };
      console.warn = function(...args) {
        self.captureLog("warn", args);
        self.originalConsole.warn.apply(console, args);
      };
      console.error = function(...args) {
        self.captureLog("error", args);
        self.originalConsole.error.apply(console, args);
      };
      console.info = function(...args) {
        self.captureLog("info", args);
        self.originalConsole.info.apply(console, args);
      };
      console.debug = function(...args) {
        self.captureLog("debug", args);
        self.originalConsole.debug.apply(console, args);
      };
    }
    captureLog(type, args) {
      const entry = {
        type,
        timestamp: (/* @__PURE__ */ new Date()).toISOString(),
        args: args.map((arg) => this.stringify(arg)),
        source: this.getCallSource()
      };
      this.consoleLogs.push(entry);
      if (this.consoleLogs.length > this.maxLogs) {
        this.consoleLogs.shift();
      }
    }
    /**
     * Get the source file and line number of the console call
     */
    getCallSource() {
      try {
        const stack = new Error().stack;
        if (!stack) return "";
        const lines = stack.split("\n");
        for (let i = 4; i < lines.length; i++) {
          const line = lines[i];
          const match = line.match(
            /(?:at\s+)?(?:.*?\s+\()?([^\s()]+):(\d+):(\d+)\)?$/
          );
          if (match) {
            const [, file, lineNum] = match;
            const fileName = file.split("/").pop() || file;
            if (fileName.includes("console-collector")) continue;
            return `${fileName}:${lineNum}`;
          }
        }
      } catch (e) {
      }
      return "";
    }
    stringify(obj) {
      if (obj === null) return "null";
      if (obj === void 0) return "undefined";
      if (typeof obj === "string") return obj;
      if (typeof obj === "number" || typeof obj === "boolean") return String(obj);
      if (obj instanceof Error) {
        return `${obj.name}: ${obj.message}
${obj.stack || ""}`;
      }
      try {
        return JSON.stringify(obj, null, 2);
      } catch (e) {
        return String(obj);
      }
    }
    getConsoleLogs() {
      const globalInterceptor = window.__consoleInterceptor;
      if (globalInterceptor && typeof globalInterceptor.getDevToolsFormat === "function") {
        const logs = globalInterceptor.getDevToolsFormat();
        if (logs && logs !== "No console logs captured.") {
          return logs;
        }
      }
      const failedResources = this.getFailedResources();
      const totalEntries = this.consoleLogs.length + failedResources.length + this.networkErrors.length;
      if (totalEntries === 0) {
        return "No console logs captured.";
      }
      let output = "";
      if (failedResources.length > 0) {
        failedResources.forEach((resource) => {
          output += `Failed to load resource: the server responded with a status of 404 (Not Found)
`;
          output += `   ${resource}
`;
        });
      }
      if (this.networkErrors.length > 0) {
        this.networkErrors.forEach((error) => {
          output += `${error}
`;
        });
      }
      this.consoleLogs.forEach((entry) => {
        const source = entry.source ? `${entry.source} ` : "";
        output += `${source}${entry.args.join(" ")}
`;
      });
      return output;
    }
    /**
     * Get failed resources from Performance API
     */
    getFailedResources() {
      const failed = [];
      if (window.performance && window.performance.getEntriesByType) {
        const resources = window.performance.getEntriesByType(
          "resource"
        );
        resources.forEach((r) => {
          if (r.responseStatus && r.responseStatus >= 400) {
            failed.push(r.name);
          }
        });
      }
      return failed;
    }
    async captureDebugSnapshot() {
      this.notificationManager.showCameraFlash();
      const screenshotBlob = await this.captureScreenshotBlob();
      const logsText = this.getConsoleLogs();
      if (!screenshotBlob && !logsText) {
        this.notificationManager.showNotification("Copy failed", "error");
        this.notificationManager.triggerCopyCallback();
        return;
      }
      if (screenshotBlob) {
        try {
          await navigator.clipboard.write([
            new ClipboardItem({ "image/png": screenshotBlob })
          ]);
          this.notificationManager.showNotification(
            "Screenshot copied - paste now!",
            "success",
            2500
          );
        } catch (e) {
          this.originalConsole.error(
            "[ConsoleCollector] Screenshot clipboard failed:",
            e
          );
        }
      }
      if (logsText && logsText !== "No console logs captured.") {
        const delay = screenshotBlob ? 3e3 : 0;
        await new Promise((r) => setTimeout(r, delay));
        try {
          await navigator.clipboard.writeText(logsText);
          this.notificationManager.showNotification(
            "Console logs copied - paste now!",
            "success"
          );
        } catch (e) {
          this.originalConsole.error(
            "[ConsoleCollector] Logs clipboard failed:",
            e
          );
        }
      } else if (!screenshotBlob) {
        this.notificationManager.showNotification("No logs to copy", "error");
      }
      this.notificationManager.triggerCopyCallback();
    }
    /**
     * Capture screenshot using getDisplayMedia (OS-level capture)
     * Returns the screenshot blob, or null if failed/cancelled
     */
    async captureScreenshotBlob() {
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: {
            displaySurface: "browser"
          },
          preferCurrentTab: true,
          selfBrowserSurface: "include",
          systemAudio: "exclude"
        });
        const video = document.createElement("video");
        video.srcObject = stream;
        video.muted = true;
        await new Promise((resolve, reject) => {
          video.onloadedmetadata = () => {
            video.play().then(() => resolve()).catch(reject);
          };
          video.onerror = reject;
          setTimeout(() => reject(new Error("Video load timeout")), 3e3);
        });
        await new Promise((r) => setTimeout(r, 100));
        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          stream.getTracks().forEach((t) => t.stop());
          return null;
        }
        ctx.drawImage(video, 0, 0);
        stream.getTracks().forEach((t) => t.stop());
        const blob = await new Promise((resolve) => {
          canvas.toBlob((b) => resolve(b), "image/png");
        });
        return blob;
      } catch (err) {
        if (err.name !== "NotAllowedError") {
          this.originalConsole.error(
            "[ConsoleCollector] Screenshot failed:",
            err
          );
        }
        return null;
      }
    }
    clearLogs() {
      this.consoleLogs = [];
      this.originalConsole.log("[ConsoleCollector] Logs cleared");
    }
  };

  // ts/utils/element-inspector.ts
  var ElementInspector = class {
    isActive = false;
    overlayManager;
    elementScanner;
    debugCollector;
    selectionManager;
    notificationManager;
    consoleCollector;
    constructor() {
      this.notificationManager = new NotificationManager();
      this.debugCollector = new DebugInfoCollector();
      this.overlayManager = new OverlayManager();
      this.elementScanner = new ElementScanner(
        this.debugCollector,
        this.notificationManager
      );
      this.selectionManager = new SelectionManager(
        this.elementScanner.getElementBoxMap(),
        this.debugCollector,
        this.notificationManager
      );
      this.selectionManager.setElementScanner(this.elementScanner);
      new PageStructureExporter(this.notificationManager);
      this.consoleCollector = new ConsoleCollector(this.notificationManager);
      this.notificationManager.setOnCopyCallback(() => {
        this.deactivate();
      });
      this.init();
    }
    init() {
      document.addEventListener("keydown", (e) => {
        const key = e.key.toLowerCase();
        if ([
          "Tab",
          "Enter",
          "ArrowUp",
          "ArrowDown",
          "ArrowLeft",
          "ArrowRight"
        ].includes(e.key)) {
          return;
        }
        if (e.ctrlKey && e.shiftKey && !e.altKey && key === "i") {
          e.preventDefault();
          e.stopPropagation();
          console.log(
            "[ElementInspector] Ctrl+Shift+I pressed - capturing debug snapshot"
          );
          this.consoleCollector.captureDebugSnapshot();
          return;
        }
        if (e.ctrlKey && e.altKey && !e.shiftKey && key === "i") {
          e.preventDefault();
          this.startSelectionMode();
          return;
        }
        if (e.ctrlKey && !e.altKey && !e.shiftKey && key === "i") {
          e.preventDefault();
          if (this.isActive) {
            console.log("[ElementInspector] Ctrl+I pressed - loading next batch");
            this.elementScanner.loadNextBatch();
          } else {
            console.log(
              "[ElementInspector] Ctrl+I pressed - activating inspector"
            );
            this.toggle();
          }
          return;
        }
        if (e.altKey && !e.shiftKey && !e.ctrlKey && key === "i") {
          e.preventDefault();
          this.toggle();
          return;
        }
        if (e.key === "Escape") {
          if (this.selectionManager.isActive()) {
            e.preventDefault();
            this.selectionManager.cancelSelectionMode();
            this.deactivate();
          } else if (this.isActive) {
            e.preventDefault();
            this.deactivate();
          }
          return;
        }
      });
      console.log("[ElementInspector] Initialized");
      console.log("  Ctrl+I / Alt+I: Toggle inspector overlay");
      console.log("  Ctrl+I (while active): Load next 512 elements");
      console.log("  Ctrl+Alt+I: Rectangle selection mode");
      console.log("  Ctrl+Shift+I: Debug snapshot (screenshot + console logs)");
      console.log(
        "  Scroll wheel: Cycle through overlapped elements (affects rect selection depth)"
      );
      console.log("  Right-click: Copy element debug info");
      console.log("  Left-click: Pass through to underlying element");
      console.log("  Escape: Deactivate inspector / Cancel selection");
    }
    toggle() {
      if (this.isActive) {
        this.deactivate();
      } else {
        this.activate();
      }
    }
    activate() {
      console.log("[ElementInspector] Activating...");
      this.isActive = true;
      const overlayContainer = this.overlayManager.createOverlay();
      this.elementScanner.scanElements(overlayContainer);
      console.log("[ElementInspector] Active - Press Alt+I to deactivate");
    }
    deactivate() {
      console.log("[ElementInspector] Deactivating...");
      this.isActive = false;
      this.elementScanner.clearElementBoxMap();
      this.overlayManager.removeOverlay();
    }
    refresh() {
      if (this.isActive) {
        this.deactivate();
        this.activate();
      }
    }
    startSelectionMode() {
      if (!this.isActive) {
        this.activate();
      }
      this.selectionManager.startSelectionMode();
    }
  };
  var existing = window.elementInspector;
  var elementInspector = existing instanceof ElementInspector ? existing : new ElementInspector();
  window.elementInspector = elementInspector;
  var resizeTimeout;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = window.setTimeout(() => {
      if (window.elementInspector?.isActive) {
        window.elementInspector.refresh();
      }
    }, 500);
  });
})();
