# Reusable lesson map

This map covers the relevant consolidated engineering lessons considered during the
September integration. It is not an exhaustive reconstruction of every private session.
Private histories are not shipped as proof; the mechanism and its public validation
surface are what belong in Fleetcraft.

| Lesson | Where it belongs | Evidence boundary |
|---|---|---|
| Two concurrent updates can both be valuable and still conflict | Reconciliation record; base-aware orchestration | Compare immutable revisions; never accept a review of the wrong candidate |
| Bounded work does not need a fleet | Orchestrator delegation threshold and negative evaluation cases | Measure unnecessary activation; a prose threshold is not native enforcement |
| A builder's confidence is not independent acceptance | Executor/verifier separation and two verdicts | A failed or missing review remains OPEN |
| Passing tests that never exercised the defect give false confidence | Regression reproduction artifacts | Same fixture must fail before repair and pass after |
| Standard test discovery can silently run zero tests | Test package and CI collection checks | Default command must run a nonempty suite |
| A generated package can drift while source tests stay green | Deterministic build and non-mutating parity check | Exact generated content, not a rebuilt substitute, is checked |
| Pushed source is different from an installable public release | Strict manifests, isolated install and tag archive check | Verify actual destination/tag/cache, not a local clone or toast |
| Sending a task to an agent does not prove research happened | Retrieval-honesty hook | Observed retrieval attempt only; attempted retrieval still does not prove truth |
| Installed once does not mean a tool exists for every adopter | Capability-aware source rules and opt-in routing | No hard-coded connected-provider or model-version guarantee |
| A diagnostic recipe can mutate production state | Performance skill | Plain planning/read-only inspection first; explicit scope for expensive execution or mutation |
| Approved design is a baseline, not a suggestion | Product/growth/image/design skills | Render changed states; label unseen behavior as inferred |
| Output proof and metrics can be inflated beyond evidence | Design and evidence contracts | Real artifacts or illustrative labels; preserve denominators and limits |
| The requested output length is part of the task | Evaluation case-level output constraints | Count actual output; a near miss is a failed constraint |
| A handoff must survive the next reader's lack of context | Project-handoff and context-record guidance | Preserve decisions, owners, artifacts, failures and open gates |
| Learning does not authorize automatic persistent writes | Incident-miner and handoff boundaries | Draft first; respect an existing authorized destination and scope |
| False baselines and incomplete traces can manufacture improvement | Evaluation parser, provenance and paired controls | Trace integrity, activation and quality are separate verdicts |

## Deliberately not imported

Host-proprietary document/connector bundles, credentials, private incident logs, bulk
service inventories, provider routers, unreviewed remote MCPs and automatic memory/hook
installers are not part of the generated runtime. Popularity or a permissive repository
license does not establish that a dependency is useful or compatible.

The external design references and licenses are in [SOURCE_LEDGER.json](SOURCE_LEDGER.json)
and [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). Every comparative improvement claim
still needs its own task set, baseline and raw evidence.
