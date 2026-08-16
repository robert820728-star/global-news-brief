# Mobile ChatGPT Basic News Schedule Design

## Goal

Provide a copy-and-paste prompt for a normal ChatGPT mobile conversation to create a daily 06:00 Scheduled Task from this public GitHub repository while using the lowest-cost practical ChatGPT mode.

## Chosen approach

Add a dedicated mobile profile instead of weakening the existing Codex workflow. The setup prompt tells the user to select ChatGPT Instant, disable automatic switching to Thinking when that control is available, create the schedule, and run it once immediately. A separate daily prompt removes local shell, capsule, map, chart, and publisher requirements while retaining the minimum acceptance contract: a rolling fourteen-day candidate list, six public-value scores per candidate, reader coverage for every C-or-higher item, and a reader-facing note for every item without an image.

## Boundaries

- Do not modify the existing Codex automation contract.
- Do not require file uploads, voice, custom GPTs, Codex, shell access, or repository writes during a daily run.
- Use GitHub/web access and Scheduled Task conversation memory only.
- Keep the monitoring inputs to regions, optional weighted topics, and the GitHub URL.
- Publish this change directly to GitHub `main` as requested.

## Verification

One contract test checks that the mobile files select Instant, reject Thinking/Pro, contain the required fourteen-day/C-or-higher/image rules, and contain no Codex or shell bootstrap dependency. Existing pipeline contract tests remain green.
