/**
 * MarkdownPreview - Rich markdown renderer for the workspace viewer.
 *
 * Ported from scitex-cloud's workspace-viewer/_MarkdownPreview.ts (identical).
 * Renders markdown with inline images, cards, tables, code blocks,
 * audio/video players.
 */

import type { ViewerAdapter } from "./types";

/** Build a URL for a project file (image, audio, video). */
function resolveFileUrl(src: string, adapter: ViewerAdapter | null): string {
  if (
    src.startsWith("http://") ||
    src.startsWith("https://") ||
    src.startsWith("data:")
  ) {
    return src;
  }
  if (adapter) return adapter.getFileUrl(src);
  return src;
}

function isAudioUrl(url: string): boolean {
  return /\.(mp3|wav|ogg|flac|aac|m4a)(\?|$)/i.test(url);
}

function isVideoUrl(url: string): boolean {
  return /\.(mp4|webm|ogv|mov|avi)(\?|$)/i.test(url);
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function renderMarkdown(
  markdown: string,
  adapter: ViewerAdapter | null,
): string {
  const lines = markdown.split("\n");
  const html: string[] = [];
  let inCodeBlock = false;
  let codeLanguage = "";
  let codeLines: string[] = [];
  let inTable = false;
  let tableRows: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith("```")) {
      if (inCodeBlock) {
        html.push(renderCodeBlock(codeLines.join("\n"), codeLanguage));
        codeLines = [];
        codeLanguage = "";
        inCodeBlock = false;
      } else {
        flushTable();
        codeLanguage = line.slice(3).trim();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      tableRows.push(line);
      inTable = true;
      continue;
    } else if (inTable) {
      flushTable();
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const text = renderInline(headingMatch[2], adapter);
      html.push(`<h${level} class="md-heading">${text}</h${level}>`);
      continue;
    }

    if (/^(-{3,}|_{3,}|\*{3,})$/.test(line.trim())) {
      html.push("<hr>");
      continue;
    }

    if (line.trim().startsWith("<")) {
      html.push(line);
      continue;
    }

    if (line.trim() === "") {
      html.push("");
      continue;
    }

    const ulMatch = line.match(/^(\s*)[-*+]\s+(.+)$/);
    if (ulMatch) {
      html.push(
        `<li class="md-list-item">${renderInline(ulMatch[2], adapter)}</li>`,
      );
      continue;
    }

    const olMatch = line.match(/^(\s*)\d+\.\s+(.+)$/);
    if (olMatch) {
      html.push(
        `<li class="md-list-item">${renderInline(olMatch[2], adapter)}</li>`,
      );
      continue;
    }

    if (line.startsWith("> ")) {
      html.push(
        `<blockquote class="md-blockquote">${renderInline(line.slice(2), adapter)}</blockquote>`,
      );
      continue;
    }

    html.push(`<p>${renderInline(line, adapter)}</p>`);
  }

  if (inCodeBlock) {
    html.push(renderCodeBlock(codeLines.join("\n"), codeLanguage));
  }
  flushTable();

  return html.join("\n");

  function flushTable(): void {
    if (!inTable || tableRows.length === 0) return;
    html.push(renderTable(tableRows));
    tableRows = [];
    inTable = false;
  }
}

function renderInline(text: string, adapter: ViewerAdapter | null): string {
  text = text.replace(
    /!\[([^\]]*)\]\(([^)]+)\)/g,
    (_match, alt: string, src: string) => {
      const resolvedSrc = resolveFileUrl(src, adapter);
      if (isAudioUrl(src)) {
        return `<div class="md-player"><audio controls preload="metadata"><source src="${escapeHtml(resolvedSrc)}"></audio><span class="md-player-label">${escapeHtml(alt || src)}</span></div>`;
      }
      if (isVideoUrl(src)) {
        return `<div class="md-player"><video controls preload="metadata" style="max-width:100%"><source src="${escapeHtml(resolvedSrc)}"></video></div>`;
      }
      return `<img class="md-image" src="${escapeHtml(resolvedSrc)}" alt="${escapeHtml(alt)}" loading="lazy">`;
    },
  );

  text = text.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    (_match, label: string, href: string) => {
      if (isAudioUrl(href)) {
        const resolvedHref = resolveFileUrl(href, adapter);
        return `<div class="md-player"><audio controls preload="metadata"><source src="${escapeHtml(resolvedHref)}"></audio><span class="md-player-label">${escapeHtml(label)}</span></div>`;
      }
      if (isVideoUrl(href)) {
        const resolvedHref = resolveFileUrl(href, adapter);
        return `<div class="md-player"><video controls preload="metadata" style="max-width:100%"><source src="${escapeHtml(resolvedHref)}"></video></div>`;
      }
      return `<a href="${escapeHtml(href)}" target="_blank" rel="noopener">${escapeHtml(label)}</a>`;
    },
  );

  text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/__(.+?)__/g, "<strong>$1</strong>");
  text = text.replace(/\*(.+?)\*/g, "<em>$1</em>");
  text = text.replace(/_(.+?)_/g, "<em>$1</em>");
  text = text.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>');
  text = text.replace(/~~(.+?)~~/g, "<del>$1</del>");

  return text;
}

function renderCodeBlock(code: string, language: string): string {
  const langClass = language ? ` data-language="${escapeHtml(language)}"` : "";
  const langLabel = language
    ? `<span class="md-code-lang">${escapeHtml(language)}</span>`
    : "";
  return `<div class="md-code-block"${langClass}>${langLabel}<pre><code>${escapeHtml(code)}</code></pre></div>`;
}

function renderTable(rows: string[]): string {
  if (rows.length === 0) return "";

  const parseRow = (row: string): string[] =>
    row
      .split("|")
      .slice(1, -1)
      .map((c) => c.trim());

  const isSeparator = (row: string): boolean =>
    /^\|[\s:]*-{2,}[\s:]*(\|[\s:]*-{2,}[\s:]*)*\|$/.test(row.trim());

  const html: string[] = ['<table class="md-table">'];

  let headerDone = false;
  for (let i = 0; i < rows.length; i++) {
    if (isSeparator(rows[i])) {
      headerDone = true;
      continue;
    }
    const cells = parseRow(rows[i]);
    const tag = !headerDone ? "th" : "td";
    if (!headerDone) html.push("<thead>");
    html.push("<tr>");
    for (const cell of cells) {
      html.push(`<${tag}>${cell}</${tag}>`);
    }
    html.push("</tr>");
    if (!headerDone) {
      html.push("</thead><tbody>");
      headerDone = true;
    }
  }

  html.push("</tbody></table>");
  return html.join("");
}

/**
 * MarkdownPreviewPanel - manages a preview container that renders markdown.
 */
export class MarkdownPreviewPanel {
  private container: HTMLElement;
  private adapter: ViewerAdapter | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  setAdapter(adapter: ViewerAdapter): void {
    this.adapter = adapter;
  }

  render(content: string): void {
    this.container.innerHTML = "";
    const wrapper = document.createElement("div");
    wrapper.className = "md-preview-content";
    wrapper.innerHTML = renderMarkdown(content, this.adapter);
    this.container.appendChild(wrapper);
  }
}
