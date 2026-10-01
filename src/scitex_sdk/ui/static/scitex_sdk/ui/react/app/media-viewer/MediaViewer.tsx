/**
 * MediaViewer -- React component for displaying non-text files.
 * Mirrors: ts/app/media-viewer/_MediaViewer.ts
 *
 * Supports: Image (zoom/pan), PDF (iframe), Mermaid, Graphviz, Binary.
 * CSV type is detected but not rendered -- handle externally via DataTable.
 */

import React, { useState, useCallback, useRef, useEffect } from "react";
import type { BaseProps } from "../../_base/types";

const CLS = "stx-app-media-viewer";

export type MediaFileType =
  | "image"
  | "pdf"
  | "csv"
  | "mermaid"
  | "graphviz"
  | "binary"
  | "text";

const IMAGE_EXT = new Set([
  ".png",
  ".jpg",
  ".jpeg",
  ".gif",
  ".webp",
  ".svg",
  ".bmp",
  ".ico",
]);
const PDF_EXT = new Set([".pdf"]);
const CSV_EXT = new Set([".csv", ".tsv"]);
const MERMAID_EXT = new Set([".mmd", ".mermaid"]);
const GRAPHVIZ_EXT = new Set([".dot", ".gv"]);
const BINARY_EXT = new Set([
  ".zip",
  ".tar",
  ".gz",
  ".rar",
  ".7z",
  ".exe",
  ".dll",
  ".so",
  ".dylib",
  ".mp3",
  ".mp4",
  ".wav",
  ".avi",
  ".mkv",
  ".mov",
  ".doc",
  ".docx",
  ".xls",
  ".xlsx",
  ".ppt",
  ".pptx",
  ".woff",
  ".woff2",
  ".ttf",
  ".eot",
  ".otf",
]);

function detectType(path: string): MediaFileType {
  const ext = path.substring(path.lastIndexOf(".")).toLowerCase();
  if (IMAGE_EXT.has(ext)) return "image";
  if (PDF_EXT.has(ext)) return "pdf";
  if (CSV_EXT.has(ext)) return "csv";
  if (MERMAID_EXT.has(ext)) return "mermaid";
  if (GRAPHVIZ_EXT.has(ext)) return "graphviz";
  if (BINARY_EXT.has(ext)) return "binary";
  return "text";
}

export interface MediaViewerProps extends BaseProps {
  /** File path to display */
  filePath: string;
  /** Override detected file type */
  fileType?: MediaFileType;
  /** Build URL for file content */
  getFileUrl: (path: string, raw?: boolean, download?: boolean) => string;
  /** Called on download */
  onDownload?: (path: string) => void;
}

// ── Diagram sub-component (handles async loading) ─────────────────────

const DiagramRenderer: React.FC<{
  filePath: string;
  type: "mermaid" | "graphviz";
  getFileUrl: (path: string, raw?: boolean, download?: boolean) => string;
}> = ({ filePath, type, getFileUrl }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const renderDiagram = async () => {
      try {
        const url = getFileUrl(filePath, true);
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const ct = response.headers.get("content-type") || "";
        let code: string;
        if (ct.includes("application/json")) {
          const json = await response.json();
          code = (json.content ?? "").trim();
        } else {
          code = (await response.text()).trim();
        }

        if (cancelled) return;

        if (!code) {
          setError("Empty diagram file");
          setLoading(false);
          return;
        }

        if (!containerRef.current) return;

        if (type === "mermaid") {
          const { default: mermaid } = await import("mermaid");
          mermaid.initialize({
            startOnLoad: false,
            theme:
              document.documentElement.getAttribute("data-theme") === "dark"
                ? "dark"
                : "default",
            securityLevel: "loose",
          });

          const id = `mmd-${Date.now()}`;
          const div = document.createElement("div");
          div.className = "mermaid";
          div.id = id;
          div.textContent = code;
          containerRef.current.innerHTML = "";
          containerRef.current.appendChild(div);
          await mermaid.run({ nodes: [div] });
        } else {
          const { Graphviz } = await import("@hpcc-js/wasm-graphviz");
          const graphviz = await Graphviz.load();
          const svg = graphviz.dot(code);
          if (containerRef.current) {
            containerRef.current.innerHTML = svg;
          }
        }

        if (!cancelled) setLoading(false);
      } catch (err) {
        if (!cancelled) {
          console.error(`[${type}Viewer] Render error:`, err);
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      }
    };

    renderDiagram();
    return () => {
      cancelled = true;
    };
  }, [filePath, type, getFileUrl]);

  if (error) {
    return (
      <div className={`${CLS}__error`}>
        <i className="fas fa-exclamation-triangle" />
        <p>Failed to render diagram: {error}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={`${CLS}__loading`}>
        <i className="fas fa-spinner fa-spin" /> Loading {type} diagram...
      </div>
    );
  }

  return <div ref={containerRef} className={`${CLS}__diagram-rendered`} />;
};

// ── Main component ────────────────────────────────────────────────────

export const MediaViewer: React.FC<MediaViewerProps> = ({
  filePath,
  fileType,
  getFileUrl,
  onDownload,
  className,
  style,
}) => {
  const type = fileType || detectType(filePath);
  const fileName = filePath.split("/").pop() || filePath;
  const [imgError, setImgError] = useState(false);
  const diagramRef = useRef<HTMLDivElement>(null);

  // Zoom state for images
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const dragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0 });

  const download = useCallback(() => {
    const a = document.createElement("a");
    a.href = getFileUrl(filePath, true, true);
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    onDownload?.(filePath);
  }, [filePath, fileName, getFileUrl, onDownload]);

  if (type === "text" || type === "csv") return null;

  const toolbar = (icon: string) => (
    <div className={`${CLS}__toolbar`}>
      <div className={`${CLS}__toolbar-left`}>
        <i className={icon} />
        <span title={filePath}>{fileName}</span>
      </div>
      <div className={`${CLS}__toolbar-right`}>
        <button className={`${CLS}__btn`} title="Download" onClick={download}>
          <i className="fas fa-download" />
        </button>
        <button
          className={`${CLS}__btn`}
          title="Open in new tab"
          onClick={() =>
            window.open(getFileUrl(filePath, true, false), "_blank")
          }
        >
          <i className="fas fa-external-link-alt" />
        </button>
      </div>
    </div>
  );

  return (
    <div
      className={`${CLS} ${className ?? ""}`}
      style={{ display: "flex", ...style }}
    >
      {type === "image" && (
        <div className={`${CLS}__image-wrapper`}>
          {toolbar("fas fa-image")}
          <div
            className={`${CLS}__image-container`}
            onWheel={(e) => {
              e.preventDefault();
              setScale((s) =>
                Math.max(0.1, Math.min(10, s * (e.deltaY > 0 ? 0.9 : 1.1))),
              );
            }}
          >
            {imgError ? (
              <div className={`${CLS}__error`}>
                <i className="fas fa-exclamation-triangle" /> Failed to load
                image
              </div>
            ) : (
              <img
                className={`${CLS}__image`}
                src={getFileUrl(filePath, true, false)}
                alt={fileName}
                style={{
                  transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
                  cursor: dragging.current ? "grabbing" : "grab",
                }}
                onError={() => setImgError(true)}
                onMouseDown={(e) => {
                  dragging.current = true;
                  dragStart.current = {
                    x: e.clientX - translate.x,
                    y: e.clientY - translate.y,
                  };
                }}
                onMouseMove={(e) => {
                  if (!dragging.current) return;
                  setTranslate({
                    x: e.clientX - dragStart.current.x,
                    y: e.clientY - dragStart.current.y,
                  });
                }}
                onMouseUp={() => {
                  dragging.current = false;
                }}
                onDoubleClick={() => {
                  setScale(1);
                  setTranslate({ x: 0, y: 0 });
                }}
                draggable={false}
              />
            )}
          </div>
        </div>
      )}

      {type === "pdf" && (
        <div className={`${CLS}__pdf-wrapper`}>
          {toolbar("fas fa-file-pdf")}
          <iframe
            className={`${CLS}__pdf-frame`}
            src={getFileUrl(filePath, true, false)}
          />
        </div>
      )}

      {type === "binary" && (
        <div className={`${CLS}__binary-wrapper`}>
          <i className={`fas fa-file-archive ${CLS}__binary-icon`} />
          <h3>Binary File</h3>
          <p>{fileName}</p>
          <button className={`${CLS}__download-btn`} onClick={download}>
            <i className="fas fa-download" /> Download
          </button>
        </div>
      )}

      {(type === "mermaid" || type === "graphviz") && (
        <div className={`${CLS}__diagram-wrapper`}>
          {toolbar(
            type === "mermaid" ? "fas fa-project-diagram" : "fas fa-sitemap",
          )}
          <div ref={diagramRef} className={`${CLS}__diagram-content`}>
            <DiagramRenderer
              filePath={filePath}
              type={type}
              getFileUrl={getFileUrl}
            />
          </div>
        </div>
      )}
    </div>
  );
};
