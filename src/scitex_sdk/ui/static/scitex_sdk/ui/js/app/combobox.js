/* =============================================================================
 * SciTeX App — Combobox (fuzzy-typeahead select)  —  pure-JS bundle
 * =============================================================================
 * Plain-JS sibling of the TS class at
 * `ts/app/combobox/_Combobox.ts` — intended for **Django-template
 * consumers** (e.g. `scitex_todo/templates/scitex_todo/board_v3.html`)
 * that ship without a vite build step and therefore can't
 * `import { Combobox } from "scitex_ui/ts/app/combobox"`.
 *
 * Load via `{% static 'scitex_ui/js/app/combobox.js' %}` and use the
 * global:
 *
 *     const cb = new STX.Combobox({
 *       container: "#cb-container",     // HTMLElement | selector
 *       trigger:   "#cb-btn",            // HTMLElement | selector
 *       items:     [{ value: "p0", label: "P0 (highest)" }, ...],
 *       value:     "p1",                 // optional initial selection
 *       placeholder: "Search…",
 *       fuzzy:     true,                 // default true
 *       onChange:  (item) => console.log(item.value),
 *       onCreate:  (raw)  => console.log("new:", raw),  // optional
 *     });
 *
 * Behaviour mirrors the TS class 1:1:
 *   - ArrowUp / ArrowDown navigates the filtered list
 *   - Enter selects the highlighted row
 *   - Esc closes the popover
 *   - Click-outside closes
 *   - Optional `onCreate` exposes a "+ Create '<query>'" row when the
 *     query does not match an existing item.label
 *
 * The DOM markup is identical to the TS class — same CSS prefix
 * (`stx-app-combobox`) so the existing `css/app/combobox.css` styles
 * both implementations.
 * ============================================================================= */

(function () {
  "use strict";

  const CLS = "stx-app-combobox";
  const NS = (window.STX = window.STX || {});

  /** fzf-style subsequence match: every char of `query` appears in
   *  `hay` IN ORDER, not necessarily consecutively. Case is normalised
   *  by the caller. */
  function fuzzyMatch(query, hay) {
    if (!query) return true;
    let i = 0;
    for (const c of query) {
      const found = hay.indexOf(c, i);
      if (found < 0) return false;
      i = found + 1;
    }
    return true;
  }

  class Combobox {
    constructor(config) {
      if (!config) throw new Error("Combobox: config required");
      this.config = config;
      this.currentValue = config.value;
      this.open = false;
      this.highlightedIndex = -1;
      this.filtered = [];

      this.container =
        typeof config.container === "string"
          ? document.querySelector(config.container)
          : config.container;
      if (!this.container) {
        throw new Error(
          `Combobox: container not found: ${config.container}`
        );
      }
      this.triggerEl =
        typeof config.trigger === "string"
          ? document.querySelector(config.trigger)
          : config.trigger;
      if (!this.triggerEl) {
        throw new Error(`Combobox: trigger not found: ${config.trigger}`);
      }

      this._outsideClick = (e) => {
        const t = e.target;
        if (
          this.open &&
          !this.container.contains(t) &&
          !this.triggerEl.contains(t)
        ) {
          this.close();
        }
      };
      this.triggerEl.addEventListener("click", (e) => {
        e.stopPropagation();
        this.toggle();
      });
      document.addEventListener("click", this._outsideClick);

      this._syncTriggerLabel();
    }

    /** Open the popover. */
    show() {
      if (this.open) return;
      this.open = true;
      this._renderMenu();
      this.container.style.display = "block";
      this._positionMenu();
      requestAnimationFrame(() => this.inputEl && this.inputEl.focus());
    }
    /** Close the popover. */
    close() {
      if (!this.open) return;
      this.open = false;
      this.container.style.display = "none";
      this.highlightedIndex = -1;
    }
    /** Toggle open/close. */
    toggle() { this.open ? this.close() : this.show(); }

    /** Replace the option list (e.g. after consumer created a new value). */
    setItems(items) {
      this.config.items = items;
      if (this.open) {
        this._applyFilter(this.inputEl ? this.inputEl.value : "");
        this._renderList();
      }
    }
    /** Programmatically set the selected value. Does NOT fire onChange. */
    setValue(v) { this.currentValue = v; this._syncTriggerLabel(); }
    /** Get the currently selected value. */
    getValue() { return this.currentValue; }

    /** Tear down + remove the document listener. */
    destroy() {
      document.removeEventListener("click", this._outsideClick);
      this.container.innerHTML = "";
    }

    // ----- render -----

    _renderMenu() {
      this.container.innerHTML = "";
      this.container.className = CLS;

      const menu = document.createElement("div");
      menu.className = `${CLS}__menu`;
      menu.setAttribute("role", "listbox");

      const input = document.createElement("input");
      input.type = "text";
      input.className = `${CLS}__input`;
      input.placeholder = this.config.placeholder || "Search…";
      input.autocomplete = "off";
      input.spellcheck = false;
      input.setAttribute("aria-autocomplete", "list");
      input.addEventListener("input", () => {
        this._applyFilter(input.value);
        this.highlightedIndex = this.filtered.length ? 0 : -1;
        this._renderList();
      });
      input.addEventListener("keydown", (e) => this._onInputKeydown(e));
      menu.appendChild(input);
      this.inputEl = input;

      const list = document.createElement("div");
      list.className = `${CLS}__list`;
      menu.appendChild(list);
      this.listEl = list;

      this.container.appendChild(menu);
      this.menuEl = menu;

      this._applyFilter("");
      this.highlightedIndex = this.filtered.length ? 0 : -1;
      this._renderList();
    }

    _renderList() {
      if (!this.listEl) return;
      this.listEl.innerHTML = "";

      if (!this.filtered.length) {
        const empty = document.createElement("div");
        empty.className = `${CLS}__empty`;
        empty.textContent = this.config.emptyText || "No matches";
        this.listEl.appendChild(empty);
      } else {
        let lastGroup;
        this.filtered.forEach((entry, idx) => {
          const item = entry.item;
          if (item.group && item.group !== lastGroup) {
            const hdr = document.createElement("div");
            hdr.className = `${CLS}__group`;
            hdr.textContent = item.group;
            this.listEl.appendChild(hdr);
            lastGroup = item.group;
          } else if (!item.group) {
            lastGroup = undefined;
          }
          const row = document.createElement("div");
          row.className = `${CLS}__item`;
          row.setAttribute("role", "option");
          row.dataset.value = item.value;
          if (item.disabled) row.classList.add(`${CLS}__item--disabled`);
          if (idx === this.highlightedIndex) {
            row.classList.add(`${CLS}__item--highlighted`);
          }
          if (this.currentValue === item.value) {
            row.classList.add(`${CLS}__item--selected`);
          }
          row.textContent = item.label;
          if (!item.disabled) {
            row.addEventListener("mouseenter", () => {
              this.highlightedIndex = idx;
              this._refreshHighlight();
            });
            row.addEventListener("click", (e) => {
              e.stopPropagation();
              this._select(entry);
            });
          }
          this.listEl.appendChild(row);
        });
      }

      // "+ Create '<query>'" row (when onCreate provided + no exact match).
      const rawQuery = this.inputEl ? this.inputEl.value : "";
      const q = rawQuery.trim();
      if (this.config.onCreate && q.length > 0) {
        const lc = q.toLowerCase();
        const exists = this.config.items.some(
          (it) => it.label.toLowerCase() === lc
        );
        if (!exists) {
          const labelFn =
            this.config.createLabel ||
            ((raw) => `+ Create “${raw}”`);
          const row = document.createElement("div");
          row.className = `${CLS}__item ${CLS}__item--create`;
          row.setAttribute("role", "option");
          row.textContent = labelFn(q);
          row.addEventListener("click", (e) => {
            e.stopPropagation();
            this.config.onCreate(q);
            this.close();
          });
          this.listEl.appendChild(row);
        }
      }
    }

    _refreshHighlight() {
      if (!this.listEl) return;
      this.listEl
        .querySelectorAll(`.${CLS}__item--highlighted`)
        .forEach((el) => el.classList.remove(`${CLS}__item--highlighted`));
      const rows = this.listEl.querySelectorAll(`.${CLS}__item`);
      const target = rows[this.highlightedIndex];
      if (target) {
        target.classList.add(`${CLS}__item--highlighted`);
        target.scrollIntoView({ block: "nearest" });
      }
    }

    _positionMenu() {
      const rect = this.triggerEl.getBoundingClientRect();
      this.container.style.position = "absolute";
      this.container.style.top = `${rect.bottom + window.scrollY}px`;
      if (this.config.align === "right") {
        this.container.style.right = `${window.innerWidth - rect.right}px`;
        this.container.style.left = "auto";
      } else {
        this.container.style.left = `${rect.left + window.scrollX}px`;
        this.container.style.right = "auto";
      }
      this.container.style.zIndex = "100";
    }

    _syncTriggerLabel() {
      if (this.config.updateTriggerLabel === false) return;
      const item = (this.config.items || []).find(
        (it) => it.value === this.currentValue
      );
      if (item) this.triggerEl.textContent = item.label;
    }

    // ----- behaviour -----

    _onInputKeydown(e) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        if (this.filtered.length) {
          this.highlightedIndex = Math.min(
            this.filtered.length - 1, this.highlightedIndex + 1
          );
          this._refreshHighlight();
        }
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        if (this.filtered.length) {
          this.highlightedIndex = Math.max(0, this.highlightedIndex - 1);
          this._refreshHighlight();
        }
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        if (
          this.highlightedIndex >= 0 &&
          this.highlightedIndex < this.filtered.length
        ) {
          this._select(this.filtered[this.highlightedIndex]);
        } else if (this.config.onCreate) {
          const q = (this.inputEl ? this.inputEl.value : "").trim();
          if (q.length > 0) {
            const lc = q.toLowerCase();
            const exists = this.config.items.some(
              (it) => it.label.toLowerCase() === lc
            );
            if (!exists) {
              this.config.onCreate(q);
              this.close();
            }
          }
        }
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        this.close();
        if (this.triggerEl.focus) this.triggerEl.focus();
        return;
      }
    }

    _select(entry) {
      if (entry.item.disabled) return;
      this.currentValue = entry.item.value;
      this._syncTriggerLabel();
      if (this.config.onChange) this.config.onChange(entry.item);
      this.container.dispatchEvent(
        new CustomEvent("combobox:change", {
          detail: { value: entry.item.value, item: entry.item },
          bubbles: true,
        })
      );
      this.close();
    }

    _applyFilter(query) {
      const q = (query || "").toLowerCase().trim();
      const items = this.config.items || [];
      if (!q) {
        this.filtered = items.map((item, index) => ({ item, index }));
        return;
      }
      const fuzzy = this.config.fuzzy !== false;
      const out = [];
      items.forEach((item, index) => {
        const hay = `${item.label} ${item.value} ${item.group || ""}`
          .toLowerCase();
        const match = fuzzy ? fuzzyMatch(q, hay) : hay.includes(q);
        if (match) out.push({ item, index });
      });
      this.filtered = out;
    }
  }

  // Static helper exposed on the class for test parity with the TS impl.
  Combobox.fuzzyMatch = fuzzyMatch;

  NS.Combobox = Combobox;
})();
