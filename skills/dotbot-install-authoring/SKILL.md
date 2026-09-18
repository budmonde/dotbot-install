---
name: dotbot-install-authoring
description: Author or review lifecycle resources for the dotbot-install Dotbot plugin, including ownership, status/apply/upgrade semantics, exact versions, interaction boundaries, destructive operations, and proportionate verification. Use when adding or changing an install directive resource; not for native Dotbot links or cleanup, or for one-shot shell actions with no meaningful lifecycle.
---

# Dotbot install authoring

The plugin owns invocation and lifecycle vocabulary.
The consuming repository owns resource policy, backend helpers, and post-install validation.

## Establish the accepted contract

Before writing code:

1. Read [the plugin protocol](references/protocol.md).
2. Inspect the latest accepted user direction, relevant design artifact, closest committed installer, and any review correction in its history.
   Do not treat an abandoned intermediate implementation as precedent.
3. Record this resource contract in working notes:

   | Question | Required decision |
   | --- | --- |
   | Owned state | What exact local or remote state may this repository create or replace? |
   | Accepted external state | What usable state owned by another manager must remain untouched? |
   | `status` | Which observation maps to each necessary lifecycle state? |
   | `apply` | What is the smallest mutation that converges missing or repairable owned state? |
   | `upgrade` | What additional advancement or cleanup is explicitly authorized? |
   | Interaction | Can execution finish with null stdin and output withheld until exit? |
   | Destructive boundary | What may be deleted, under which operation, and after which verification? |
   | Postcondition | What single final observation proves convergence? |

Do not implement an unspecified row merely because the vendor API makes it detectable.
Inventory, rotation, cleanup, migration, and account selection each require an accepted policy.

## Choose the smallest surface

Use this order:

1. A native Dotbot directive for links, cleanup, and configuration state it already models.
2. A short `shell` action when there is no useful read-only probe, version authority, or repair policy.
3. A thin resource wrapper over an existing consuming-repository backend.
4. A custom lifecycle resource only for irreducible resource policy.

Extract a backend when at least two real resources share lifecycle semantics, not merely similar commands.
If a custom resource is much larger than its nearest committed peers, identify the irreducible differences before keeping that size.

Authentication deserves an explicit ownership decision.
Use a read-only environment check when dotfiles only needs to require an existing login.
Use an installer resource to establish authentication only when the operator has delegated that action and the execution boundary can support it safely.

## Implement one lifecycle

- Prefer one observation, one minimal mutation, and one final observation.
- Carry structured probe results forward instead of repeating local or remote inventory calls in one phase.
- Preserve usable external-manager state unless the recipe explicitly claims it.
- Keep `status` read-only.
- Keep ordinary `apply` idempotent and free of version advancement.
- Do not add destructive duplicate cleanup unless the accepted `apply` contract explicitly owns it;
  otherwise reserve it for `upgrade`.
- Complete and verify a replacement before deleting superseded owned state.
- Derive exact-version behavior from the recipe command;
  do not duplicate the version in code.
- Prefer structured vendor output.
  Parse human output only when no stable structured interface exists.
- Keep stdout exclusively for the final lifecycle state and send secret-free diagnostics to stderr.

Return `blocked` when prerequisites or external conditions prevent a reliable decision or action.
Return `unsupported` when the detected state is intentionally outside this resource's ownership and is acceptable to preserve.
Do not manufacture finer state distinctions unless they lead to different safe behavior.

## Handle interaction deliberately

The plugin runs children with null stdin and captures stdout and stderr until exit.
An installer cannot rely on a prompt or on the operator seeing live device instructions.
The recipe description is emitted before the child starts, so make it state any immediate clipboard or browser expectation.

Choose one explicit boundary:

- invoke the resource from a bootstrap or wrapper that provides inherited terminal I/O;
- use vendor-supported noninteractive flags and automatic browser launch when the recipe is explicitly intended to establish authentication;
- extend the plugin with a declared interactive mode when live terminal exchange is a real recurring requirement;
- otherwise keep login operator-owned and validate it with envtest.

Never pass a token on the command line, print a token or unrestricted environment, or place credential files under dotfiles management.

## Verify behavior rather than structure

Test the smallest externally meaningful matrix:

- read-only `status` for current and one non-current boundary;
- `apply` convergence and preservation of accepted external state;
- `upgrade` separately when it differs from `apply`;
- destructive ordering when cleanup exists;
- interaction failure when the resource establishes authentication;
- protocol-clean stdout and a final postcondition.

Prefer tests at the handler or backend boundary.
Avoid tests that freeze private helper call order unless that order is the safety property.

Run the plugin suite after changing plugin mechanics or this contract:

```text
python -m pytest
```

Then use the consuming repository's focused lifecycle tests, Dotbot dry-run, and relevant read-only environment checks.
