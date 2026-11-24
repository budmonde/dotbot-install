# dotbot-install

`dotbot-install` adds an `install` directive to [Dotbot](https://github.com/anishathalye/dotbot).
Use it to run a repository’s installers in recipe order and report whether each resource reached an acceptable state.

## Use the plugin

Use Python 3.8 or newer and Dotbot 1.23 or newer.
The example assumes a consuming repository with Dotbot at `dotbot/`, this plugin at `dotbot-install/`, and an npm installer at `install/resources/npm-global.py` that accepts a package name.
In the consuming repository, add this entry to `install.conf.yaml`:

```yaml
- install:
    - [[install/resources/npm-global.py, prettier], Installing Prettier]
```

Preview it from that repository’s root:

```sh
python dotbot-install/runner.py dotbot/bin/dotbot -p dotbot-install/install.py -c install.conf.yaml --only install --dry-run
```

The preview lists the installer and its package argument without running it.
Omit `--dry-run` to apply the recipe or pass `--upgrade` to request an upgrade.
Installing the plugin checkout with `python -m pip install .` also provides the `dotbot-install-runner` command.

Use [dotbot-install-usage](skills/dotbot-install-usage/SKILL.md) to select a provider or write an installer.
Its [protocol reference](skills/dotbot-install-usage/references/protocol.md) defines the recipe syntax, operations, and results.
For changes to the plugin itself, start with the [project instructions](AGENTS.md).
