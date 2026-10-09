# Workspace commands

Use one command registry and keymap for a leaf's existing actions. The opt-in
`WorkspaceCommands` component supplies a searchable command palette and shortcut
controls. It adds no default shortcuts and does not replace the shell's existing
keyboard listeners. The host chooses a free factory binding and explicit
payload-free commands to offer; a preference cannot grant project access.

```ts
import { CommandRegistry, Keymap, WorkspaceCommands } from
  "@scitex/sdk/ui/ts/shell/workspace-commands";
import { ProjectSelector, PROJECT_SELECTOR_OPEN } from
  "@scitex/sdk/ui/ts/app/project-selector";

const registry = new CommandRegistry();
const keymap = new Keymap({ registry });
const picker = new ProjectSelector({
  container: "#project-picker",
  provider, // the leaf's existing authorized ProjectProvider
  commands: registry,
  openCommandId: PROJECT_SELECTOR_OPEN,
});
// Check a proposed factory binding before mounting. This example is optional;
// the host must also check its legacy/editor/browser shortcuts.
const conflict = keymap.bind("global", "C-x C-p", PROJECT_SELECTOR_OPEN);
if (conflict) throw new Error(`Shortcut occupied: ${conflict.sequenceKey}`);

// Load existing host preferences after defining factory bindings, when present.
// keymap.loadOverrides(savedPreferences);
const commands = new WorkspaceCommands({
  container: "#workspace-commands",
  registry,
  keymap,
  commandIds: [PROJECT_SELECTOR_OPEN],
  // Optional: persist with the host's existing preference adapter.
  // onPreferencesChange: (preferences) => savePreferences(preferences),
});

// On page/SPA teardown, detach keyboard/composition listeners, then remove
// the picker's owned commands. Other commands and preferences remain owned
// by their original registrants.
commands.destroy();
picker.destroy();
```

Load `scitex_sdk/ui/css/shell/workspace-commands.css` and the existing picker CSS.
For native browser modules, import `WorkspaceCommands`, `CommandRegistry` and
`Keymap` from `scitex_sdk/ui/js/shell/workspace-commands.js`, and the picker from
`scitex_sdk/ui/js/app/project-selector.js`. Reuse those instances across the
components; the palette rejects a keymap from another registry or a second
palette owner of that keymap.

The project button, palette entry and configured shortcut open the same picker.
Opening does not select a project, write provider state or grant user scope.
Selection keeps the existing payload validation and provider acknowledgement
contract. Pending selection prevents another opening action. Registering an
opening command is optional, so existing picker consumers retain their default
command registration.

Apply changes the effective shortcut; Disable affects keyboard dispatch only;
Reset restores that command's factory binding while retaining other commands'
preferences. A collision is shown and rolled back. Shortcut notation uses
`C` for Ctrl, `M` for Alt, `S` for Shift and `M2` for Command/Super, with spaces
between successive keys. Editable elements suppress shortcuts unless the host
explicitly opts a binding in. Composition and AltGraph input are always preserved.
After changing registry modes/commands or loading preferences externally, call
`commands.refresh()` to update the palette.

This is reusable frontend wiring. Generic Hub activation, authenticated demo
context and a particular leaf's mounted integration remain with their existing
owners. No macro language, account persistence endpoint or scientific export is
introduced.
