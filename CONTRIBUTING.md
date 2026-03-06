# Contributing to gitplex

Thank you for your interest in contributing. Please read this document before opening a PR.

---

## Getting started

```bash
git clone https://github.com/firexrwt/gitplex.git
cd gitplex
pip install -e .
```

The `gitplex` command will be available immediately after the editable install.

---

## Branches

- `main` — stable, always runnable. Direct pushes only for maintainers.
- Feature branches — name them `feature/short-description` or `fix/short-description`.
- Open a PR against `main` when ready.

---

## Commit messages

Keep them short and in English:

```
add bulk stash operation
fix: repo list not refreshing after clone
bump version to 0.4.0
```

No issue references required for small fixes. For larger changes, briefly explain *why* in the commit body.

---

## Code style

- Match the existing style: no type annotations on internal helpers, short inline comments only where the logic isn't obvious.
- No dead code, no unused imports, no commented-out blocks.
- Keep widgets self-contained — don't reach into another widget's internals directly, post messages instead.

---

## What belongs in a PR

- One feature or one fix per PR.
- No speculative refactoring unrelated to the PR goal.
- No extra abstractions "for the future".
- No formatting-only changes mixed with logic changes.

---

## Testing

There is no automated test suite yet. Manual testing is mandatory:

- Launch `gitplex` and exercise the feature you changed.
- Test on at least one real repository with actual dirty state.
- Make sure unrelated features still work (commit, stage, bulk ops, etc.).

---

## AI-assisted code

Contributions written with AI tools (Claude Code, Opencode, Codex, Copilot, Cursor, or any other agent or assistant) are **allowed**, but are held to a higher review standard.

If your PR contains AI-generated or AI-assisted code, you **must**:

1. **Read every line yourself.** You are responsible for the code, not the model.
2. **Understand what it does.** If you can't explain a section of code in plain words, don't submit it.
3. **Verify correctness.** AI produces plausible-looking but subtly broken logic more often than it seems.
4. **Check for regressions.** Run the app, use the affected feature, make sure unrelated features still work.
5. **Strip the bloat.** Remove anything the PR doesn't actually need — extra error handling for impossible cases, helper functions used once, over-engineered abstractions.
6. **Label it.** Add `AI-assisted` to the PR description.

PRs where AI-generated code has clearly not been reviewed will be closed without merge.
