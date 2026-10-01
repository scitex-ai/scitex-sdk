/**
 * @scitex/ui/pdf-viewer/react — thin React adapter over the L1 vanilla-TS core.
 *
 * Owns only mount/unmount + option→imperative-call bridging. All rendering,
 * pen input, and mark state live in the neutral L1 core so the React and
 * standalone consumers share identical behavior.
 */

import {
  type CSSProperties,
  type ReactElement,
  useEffect,
  useRef,
} from "react";
import {
  createPdfViewer,
  type Mark,
  type PdfPalette,
  type PdfSource,
  type PdfTool,
  type PdfViewerApi,
  type PdfViewerHooks,
} from "../../../ts/app/pdf-viewer";

export interface PdfViewerProps {
  src?: PdfSource;
  tool?: PdfTool;
  marks?: Mark[];
  palette?: PdfPalette;
  hooks?: PdfViewerHooks;
  className?: string;
  style?: CSSProperties;
}

export function PdfViewer(props: PdfViewerProps): ReactElement {
  const { src, tool, marks, palette, hooks, className, style } = props;
  const containerRef = useRef<HTMLDivElement>(null);
  const apiRef = useRef<PdfViewerApi | null>(null);

  // Construct once against the container; controlled updates flow via effects.
  useEffect(() => {
    if (!containerRef.current) return;
    const api = createPdfViewer({
      container: containerRef.current,
      src,
      tool,
      palette,
      hooks,
    });
    apiRef.current = api;
    return () => {
      api.destroy();
      apiRef.current = null;
    };
    // Construct-once: later prop changes are applied by the effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (src !== undefined) void apiRef.current?.load(src);
  }, [src]);

  useEffect(() => {
    if (tool !== undefined) apiRef.current?.setTool(tool);
  }, [tool]);

  useEffect(() => {
    if (marks !== undefined) apiRef.current?.setMarks(marks);
  }, [marks]);

  useEffect(() => {
    if (palette !== undefined) apiRef.current?.setPalette(palette);
  }, [palette]);

  return <div ref={containerRef} className={className} style={style} />;
}
