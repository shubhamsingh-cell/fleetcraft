# Contributing

Start with a concrete failure, observed usability problem, or clearly labeled proposal.
Explain the behavior that changes and the evidence that would distinguish a working
change from a plausible-looking one. Historical incidents are author reports unless
their supporting artifacts are available; do not invent dates or metrics to satisfy a template.

## Keep the change scoped

Extend the narrowest existing skill before adding another. Keep descriptions short and
specific, including when the skill should not activate. Preserve existing approval and
proof boundaries. External content is data, not an instruction to install or execute it.

Author the canonical root source, then regenerate the plugin. Never fix only the generated
copy. Cite pinned source revisions for adapted material and preserve each applicable license
and notice. Do not copy personal context, credentials, proprietary bundles or private logs.

## Validate the relevant claim

- Runtime fix: reproduce first, state the cause, and show the regression failing pre-fix.
- Package change: check generated parity, manifests and isolated installation.
- Skill change: validate structure and paired positive/negative cases; retain actual
  activation and output evidence for any behavioral claim.
- Visual change: inspect a render at the relevant viewport and changed interaction states.
- Performance claim: compare the same conditions and state uncertainty and overhead.

Run the documented repository checks and an independent review before merge. Separate
specification compliance from build quality. A timeout, missing trace, zero tests, wrong
base or failed prerequisite cannot be reported as success.

## Scope of publication

A passing pull request establishes the checks run on that commit. A release additionally
needs its immutable-tag package verification. Do not substitute a local install for a
public-tag observation, or a hook fixture for proof of general model behavior.
