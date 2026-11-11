/** Read Django's request token without requiring a JavaScript-readable cookie. */
export function csrfToken(): string {
  if (typeof document === "undefined") return "";
  const rendered = document.querySelector<HTMLInputElement>(
    'input[name="csrfmiddlewaretoken"]',
  )?.value;
  if (rendered) return rendered;
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}
