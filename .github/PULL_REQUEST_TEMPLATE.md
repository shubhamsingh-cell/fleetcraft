## What this changes and why

<!-- One or two sentences. If this closes an issue, reference it (Closes #123). -->

## Checklist

- [ ] **Precedent named.** If this adds or changes a rule's substance, the
      PR description (or the file itself) names the specific, dated
      failure that motivated it — see `CONTRIBUTING.md`'s evidence bar.
      Not required for pure wording/typo/formatting fixes.
- [ ] **Sanitization checked.** No employer, client, colleague, or product
      name appears anywhere in the diff — files, commit messages, or this
      PR description. Genericized while keeping the failure and its date
      intact.
- [ ] **`python3 scripts/validate.py` passes.** Ran it locally; pasting
      its output below is welcome but not required if CI is green.
- [ ] **Hooks fail open.** Any new or changed hook stays non-blocking by
      default and exits 0 on a parse error / unexpected input. If it
      *does* block or deny, that's flagged explicitly in its own
      docstring and in `hooks/README.md`, with the reasoning — not the
      default, an exception.
- [ ] **README/CHANGELOG updated if user-facing.** New skill/agent/hook,
      changed installation steps, or any other change a user of this repo
      would need to know about.

## Validator output (optional but appreciated)

```
paste `python3 scripts/validate.py` output here
```
