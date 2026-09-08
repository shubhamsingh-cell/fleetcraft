## What this changes and why

<!-- One or two sentences. If this closes an issue, reference it (Closes #123). -->

## Checklist

- [ ] **Evidence is grounded.** State the concrete failure, observed usability
      problem, or clearly labeled proposal. Do not invent dates or metrics;
      keep supporting artifacts available when they exist.
- [ ] **Sensitive material is excluded.** The diff and description contain no
      credentials, private logs, proprietary bundles, or personal context.
- [ ] **Attribution is preserved.** Adapted material retains its pinned source
      revision and applicable license or notice.
- [ ] **`python3 scripts/validate.py` passes.** Ran it locally; pasting
      its output below is welcome but not required if CI is green.
- [ ] **Hook contracts are documented.** Changed hooks describe their actual
      default, strict or other opt-in behavior, including malformed-input
      handling; do not describe the hook family as universally fail-open or
      fail-closed.
- [ ] **Validation is meaningful.** Ran the checks that support this change's
      claim (for example, a regression reproducer, plugin parity and isolated
      installation, skill cases, or a relevant render).
- [ ] **README/CHANGELOG updated if user-facing.** New skill/agent/hook,
      changed installation steps, or any other change a user of this repo
      would need to know about.

## Validator output (optional but appreciated)

```
paste `python3 scripts/validate.py` output here
```
