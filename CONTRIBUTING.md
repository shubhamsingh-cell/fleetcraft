# Contributing

This repo is not a framework and not a best-practices list. Every rule in
`skills/`, `agents/`, and `hooks/` exists because a specific, dated failure
happened in a real production setup and someone had to fix it. That's the
whole reason the rule is here instead of in the model's general judgment —
the model already "knows" most generic best practices; it forgot this one
specific thing, once, at a specific moment, and the rule closes exactly
that gap. Read the existing files before you propose anything: notice how
almost every non-trivial claim in them is anchored to a dated incident
("the 2026-07-16/17 failure," "measured over 30 days," "found in a
2026-08-27 audit"). That anchoring is not decoration. It's the bar.

## What belongs here

- Opinionated operating rules extracted from a real, dated failure — a
  skill section, an agent contract clause, a hook check.
- Sanitized war stories: what broke, when, and the rule that now prevents
  it, with identifying details stripped (see **Sanitization**, below).
- Small, self-contained tooling that enforces a rule deterministically
  (the hooks) or checks the repo's own integrity (`scripts/validate.py`).

## What doesn't belong here

- Generic best-practice advice ("write tests," "use meaningful variable
  names," "prefer composition over inheritance"). If it would read the
  same in any repo, in any year, it doesn't belong in this one — it's not
  wrong, it's just not what this repo is *for*.
- Framework or application code. This is a skills/agents/hooks kit, not a
  library. If your contribution needs its own dependency tree, it's
  probably a different project.
- A rule motivated by "this seems better" or "this is more idiomatic."
  See the evidence bar below — that's not evidence, it's taste, and taste
  changes; a documented failure doesn't.
- Speculative rules for failures that haven't happened yet ("what if
  someone does X"). If X hasn't caused a real incident, write it down
  somewhere else and bring it back if it ever does.

## The evidence bar

Every new rule, and every change to an existing rule's *substance* (not
wording), needs:

1. **The failure, named.** What broke, concretely — not "this could cause
   confusion" but "the assistant ran `git push --force` on a shared branch
   because it read a stale local ref as current."
2. **The date.** Even approximate. Dates let a future reader (and future
   you) tell a fresh rule from a load-bearing one, and they're what makes
   the "sanitized but real" claim in the README checkable instead of just
   asserted.
3. **What the rule changes about the failure mode.** A rule that doesn't
   map back to the specific failure it prevents is scope creep, even if
   it's a good idea in general.

"I think this would help" is not evidence. "This is a well-known
anti-pattern" is not evidence. A citation to an external best-practices
guide is not evidence — this repo's evidence base is one production
setup's documented incidents, and that's a deliberate, stated limitation
(see the README's "Honest limitations" section), not something to paper
over with borrowed authority. If you don't have a dated failure, open an
issue with the `rule_proposal` template and say so plainly; a maintainer
may still take it, but as a judgment call, not as something the process
can wave through.

## Proposing a new skill vs. extending an existing one

Extend an existing skill when your rule is a specific instance of a
problem that skill's mechanism already governs — a new proof-fabrication
shape belongs in `design-judge`'s vetoes, not a new skill; a new
delegation failure mode belongs in `fleet-orchestrator`'s gate classes,
not a new skill.

Propose a new skill only when the rule needs its own trigger conditions,
its own routing (when should this fire that none of the existing skills'
triggers cover?), and enough accumulated substance to be worth a separate
file instead of a paragraph. One dated incident is evidence for a rule;
it is rarely enough evidence for a whole new skill on its own — a new
skill usually earns its place after a rule (or a small cluster of related
rules) has already proven itself as an addition to an existing file and
the fit is genuinely awkward there.

Either way, open an issue first with the `rule_proposal` template before
sending a large PR. It's a lot cheaper to agree on "yes, this is a real
failure and it belongs in `growth-web-architect`, not a new skill" before
the writing than after.

## Sanitization

Nothing here names a real employer, client, colleague, or product. When
you bring in a war story, genericize it before it goes in a commit —
replace the specific org/person/product with a role or category
("a client," "a teammate," "the CRM product") and keep every detail that
makes the failure and its fix legible: what broke, why, the date, and the
rule that now catches it. Sanitizing is a rewrite, not a redaction — the
failure has to survive the pass as clearly as it went in. If genericizing
would make the failure unintelligible, that's a sign the write-up needs
more mechanism and less anecdote, not that the identifying detail should
stay.

Before opening a PR, re-read your diff once specifically hunting for
names — company names, product names, people's names or initials, email
domains, Slack handles, ticket IDs from an internal tracker. `git log`
messages and PR descriptions get the same pass; a sanitized file with an
unsanitized commit message defeats the point.

## Before opening a PR

Run the validator:

```bash
python3 scripts/validate.py
```

It checks skill/agent frontmatter shape, that every hook compiles and
exits cleanly on an empty `{}` payload, and that no file leaked an
absolute path from someone's home directory (a machine-specific macOS or
Linux user path) or stray Obsidian-style double-bracket link syntax. CI
runs the same script on every push and PR — a
failing `validate.py` blocks merge, so it's cheaper to run it locally
first. It's dependency-free (stdlib only); if you've got Python 3, you can
run it.

## Hooks: fail open, and blocking is a deliberate, documented choice

Every hook in `hooks/` is non-blocking by default and fails open: on a
parse error, a missing file, or any unexpected input, it stays silent and
exits 0 rather than erroring the turn or denying a tool call. This is not
a style preference — a hook that crashes or hangs on a malformed payload
wedges a real session, and a hook that blocks on a false positive trains
the user to strip it out of `settings.json` the first time it gets in the
way. See `hooks/README.md` for the full contract each hook follows,
including which ones fail loud on a parse error (rare, and stated
explicitly why) versus fail silent (the default).

If your hook needs to block or deny a tool call, that has to be the
deliberate point of the hook, not a side effect of not handling an edge
case — and it needs to say so in its own docstring and in `hooks/
README.md`, the same way `tool-routing-guard.py`'s one blocking path
documents exactly why a reminder-only version of that nudge was tried
first, measured, and found not to work. "Might as well block, it's
probably fine" is not that bar.

`scripts/validate.py` enforces the mechanical half of this contract for
you (compiles, exits 0 on `{}`); it can't check that a hook's blocking
behavior is documented and deliberate — that's a review-time judgment
call, not a script.
