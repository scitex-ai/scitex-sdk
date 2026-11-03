/** React lifecycle and portal binding for the canonical SDK header. */
import { useLayoutEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { AppHeader as HeaderComponent } from "../../../ts/app/app-header";

export interface AppHeaderProps {
  title: string;
  version?: string;
  projectSelector?: ReactNode;
  actions?: ReactNode;
  apiDocsUrl?: string | null;
  apiDocsLabel?: string;
}

export function AppHeader({ title, version, projectSelector, actions, apiDocsUrl, apiDocsLabel }: AppHeaderProps) {
  const container = useRef<HTMLDivElement>(null);
  const component = useRef<HeaderComponent | null>(null);
  const [slots, setSlots] = useState<HeaderComponent | null>(null);
  const text = useRef({ title, version, apiDocsUrl, apiDocsLabel });
  text.current = { title, version, apiDocsUrl, apiDocsLabel };
  const hasProjectSelector = projectSelector != null;

  useLayoutEffect(() => {
    if (!container.current) return;
    const header = new HeaderComponent({
      container: container.current,
      ...text.current,
      projectSlot: hasProjectSelector,
    });
    component.current = header;
    setSlots(header);
    return () => {
      component.current = null;
      header.destroy();
    };
    // Text updates below preserve the component and its mounted picker.
  }, [hasProjectSelector]);

  useLayoutEffect(() => {
    component.current?.setTitle(title);
    component.current?.setVersion(version ?? "");
    component.current?.setApiDocsUrl(apiDocsUrl, apiDocsLabel);
  }, [title, version, apiDocsUrl, apiDocsLabel]);

  return <>
    <div ref={container} />
    {slots?.projectSlot && createPortal(projectSelector, slots.projectSlot)}
    {slots && createPortal(actions, slots.actionsEl)}
  </>;
}
