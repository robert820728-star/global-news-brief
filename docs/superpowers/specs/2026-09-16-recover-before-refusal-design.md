# Recover Before Refusal Design

## Outcome

The daily-news controller must prefer producing the requested news. Any failure that can be repaired inside the current occurrence and run is an internal recovery action, not a user-visible refusal.

## Decision

Use one controller, `publish_news_brief.py --resume-before-deliver`, for every delivery attempt. Legacy `--deliver-receipt` becomes a compatibility alias to this controller when a checkpoint is supplied. Validators continue rejecting invalid artifacts, but their failures are translated into the earliest owning pipeline stage instead of a terminal delivery error.

## Recovery classes

| Failure | Controller action |
| --- | --- |
| Incomplete or failed checkpoint stage | Resume that same stage. |
| Missing, unreadable, or invalid stage artifact | Redo the owning stage. |
| Candidate/audit/manifest mismatch | Redo `audit-news-candidates` or `materialize-manifest`, whichever owns the invalid output. |
| Map, attachment, or image validation failure | Redo the corresponding visual stage. |
| Reader/render validation failure | Redo `render`. |
| Missing or invalid receipt with otherwise valid inputs | Republish automatically, then deliver. |
| Final delivery revalidation failure | Translate the error to the owning stage and resume; do not emit a Reader or blocker yet. |
| Unreadable checkpoint | Attempt `checkpoint-recovery` from durable same-run evidence. |

Only an external authority/identity violation that prevents safe identification of the occurrence, or a stage whose bounded recovery attempts are actually exhausted, may become a concise user-visible blocker.

## Acceptance

1. No delivery CLI path can emit a manual Reader or directly terminate for a recoverable run-local failure.
2. Every recovery decision is machine-readable and names an executable target stage.
3. Missing/invalid receipt alone never blocks delivery.
4. Existing validation strictness remains unchanged.
5. Formal prompts and skills state that validator/transport failures enter bounded recovery before any blocker response.
