/** Options for AjaxLoader */
export interface AjaxLoaderOptions {
  /** CSS selector for the container to inject content into */
  containerSelector: string;
  /** CSS selector for links that trigger AJAX loading */
  linkSelector: string;
  /** Header name to signal partial response (default: X-Workspace-Shell) */
  headerName?: string;
  /** Header value (default: "1") */
  headerValue?: string;
  /** Whether to update browser history (default: true) */
  pushState?: boolean;
  /** Callback after content is loaded */
  onLoad?: (url: string, container: HTMLElement) => void;
  /** Callback on error */
  onError?: (url: string, error: Error) => void;
}
