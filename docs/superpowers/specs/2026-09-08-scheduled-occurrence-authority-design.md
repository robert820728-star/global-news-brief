# Scheduled Occurrence Authority Design

## Goal

Prevent an ordinary follow-up message in an existing ChatGPT conversation, including `重新執行`, from being treated as a new or resumed Scheduled Task occurrence.

## Authority and data flow

The only authority that may enter the daily-news pipeline is an actual Scheduled Task trigger that exposes a control-plane `scheduled_for` value. The executor must bind that value to the durable `run_id`, `main_sha`, timezone, and 24-hour window before discovery. A conversational follow-up has no such authority and therefore cannot fresh-resolve news, create or resume a run, perform discovery, or render any Reader.

If occurrence authority is missing, the response is a concise lifecycle blocker receipt. It may identify the missing `scheduled_for` evidence and instruct the operator to trigger or inspect the real task, but it must not contain news candidates, scores, a degraded Reader, or claims that a task occurrence ran.

## Compatibility

Actual manual Scheduled Task runs remain valid when the control plane creates a real occurrence with `scheduled_for`. Installation smoke remains outside occurrence execution. Formal daily 06:00 scheduling and the cancelled ten-minute validation automation are unchanged.

## Verification

A regression test requires the gate marker and the fail-closed obligations in the install contract, scheduled prompt template, daily controller, and mobile execution contract. The full repository suite, capsule verification, remote CI, and clean exports remain the release gates.
