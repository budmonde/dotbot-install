# Mission

Give repositories that use Dotbot a common way to run installers and tell whether the requested setup succeeded.

## Design principles

**Keep recipes familiar to a Dotbot user.**
Prefer one `install` directive with ordered entries for different installers and operations.
Follow Dotbot conventions such as the `shell` directive’s command-and-description pairs, and leave directive selection, ordering, and dry runs under Dotbot’s control.
The runner should consume only the options needed to select an installer operation and pass Dotbot’s own arguments through unchanged.

**Keep resource policy with the installer.**
The plugin defines how to invoke an installer and interpret its result.
The consuming repository decides what to install, which versions or existing installations are acceptable, and what it may replace.
If a provider can express a new requirement as an ordinary command argument, a recipe author should be able to use it without changing the plugin.

**Make repeated setup predictable.**
A recipe author should be able to inspect, apply, or upgrade the same declaration.
Inspection must leave the resource untouched, ordinary setup should preserve an installation that already meets the recipe, and an upgrade must respect any version the recipe explicitly requests.
Validate the whole install list before starting its first entry so a malformed later entry cannot leave an otherwise avoidable partial installation.
