/**
 * FileTabs — React tab bar for open files.
 * Mirrors: ts/app/file-tabs/_FileTabs.ts
 */

import React, { useCallback } from "react";
import type { BaseProps } from "../../_base/types";

const CLS = "stx-app-file-tabs";

export interface FileTab {
  path: string;
  label?: string;
  isDirty?: boolean;
  isPermanent?: boolean;
}

export interface FileTabsProps extends BaseProps {
  /** Open tabs */
  tabs: FileTab[];
  /** Currently active tab path */
  activeTab: string | null;
  /** Called when tab is clicked */
  onTabSwitch: (path: string) => void;
  /** Called when tab close button is clicked */
  onTabClose: (path: string) => void;
  /** Called when + button clicked */
  onNewFile?: (name: string) => void;
  /** Show + button (default: true) */
  showNewButton?: boolean;
  /** Tab that cannot be closed */
  permanentTab?: string;
}

export const FileTabs: React.FC<FileTabsProps> = ({
  tabs,
  activeTab,
  onTabSwitch,
  onTabClose,
  onNewFile,
  showNewButton = true,
  permanentTab,
  className,
  style,
}) => {
  const handleNewFile = useCallback(() => {
    if (!onNewFile) return;
    const name = prompt("New file name:");
    if (name?.trim()) onNewFile(name.trim());
  }, [onNewFile]);

  return (
    <div className={`${CLS} ${className ?? ""}`} style={style}>
      {tabs.map((tab) => {
        const isActive = tab.path === activeTab;
        const isPermanent = tab.path === permanentTab || tab.isPermanent;
        const label = tab.label || tab.path.split("/").pop() || tab.path;

        return (
          <button
            key={tab.path}
            className={`${CLS}__tab${isActive ? ` ${CLS}__tab--active` : ""}${tab.isDirty ? ` ${CLS}__tab--dirty` : ""}`}
            title={tab.path}
            onClick={() => onTabSwitch(tab.path)}
          >
            <span className={`${CLS}__label`}>{label}</span>
            {tab.isDirty && <span className={`${CLS}__dirty`}>{"\u25CF"}</span>}
            {!isPermanent && (
              <span
                className={`${CLS}__close`}
                onClick={(e) => {
                  e.stopPropagation();
                  onTabClose(tab.path);
                }}
              >
                {"\u00D7"}
              </span>
            )}
          </button>
        );
      })}
      {showNewButton && onNewFile && (
        <button
          className={`${CLS}__new`}
          title="New file"
          onClick={handleNewFile}
        >
          +
        </button>
      )}
    </div>
  );
};
