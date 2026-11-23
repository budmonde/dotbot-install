# Change the plugin or its usage guidance

Start with a concrete recipe or launcher affected by the change.
Use the [mission](mission.md) to locate the owner and the [installer protocol](../skills/dotbot-install-usage/references/protocol.md) to identify what the caller can rely on today.

## Change invocation or results

Dotbot parses its command line before loading plugins.
Change the [runner](../runner.py) when the caller needs to select a lifecycle operation before Dotbot starts.
Check that Dotbot still receives its own arguments in order and its exit result reaches the caller.
The [runner tests](../tests/test_runner.py) exercise both the command-line and imported entry points.

Change the [install directive](../install.py) when the contract for recipe entries, child processes, or reported results changes.
Exercise the affected boundary in the [directive tests](../tests/test_install.py).
For example, when changing the entry format, verify that a valid entry delivers the intended arguments and that a malformed later entry is rejected before any installer starts.

When an interface changes, try an existing consumer invocation against it.
If consumers must migrate, identify which recipes, installers, or launchers need to change and give their maintainers a working replacement before they update the plugin.

## Publish and verify the contract

Update the [protocol reference](../skills/dotbot-install-usage/references/protocol.md) when callers must provide different inputs or interpret results differently.
Update the [usage skill](../skills/dotbot-install-usage/SKILL.md) when that changes how a recipe author selects or implements a resource.
Keep the [README example](../README.md) runnable when setup or invocation changes.

From the plugin checkout, install the test dependencies with `python -m pip install -e ".[test]"` in a development environment and run `python -m pytest`.
Preview affected recipe changes with Dotbot’s dry run to check selection and argument handling.
When a change affects actual execution, exercise a disposable installer and check its observable result.
