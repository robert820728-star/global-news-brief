# Mobile ChatGPT Basic News Schedule Design

## Goal

Provide a copy-and-paste prompt for a normal ChatGPT mobile conversation to create a daily 06:00 Scheduled Task from this public GitHub repository while using the lowest-cost practical ChatGPT mode.

## Chosen approach

Add a dedicated mobile profile instead of weakening the existing Codex workflow. The setup prompt tells the user to select ChatGPT Instant, disable automatic switching to Thinking when that control is available, create the schedule, and run it once immediately. A separate daily prompt removes local shell, capsule, map, chart, and publisher requirements while retaining the minimum acceptance contract: a rolling fourteen-day candidate list, six public-value scores per candidate, reader coverage for every C-or-higher item, and a reader-facing note for every item without an image.

For mobile image delivery, preserve the selected news image and reduce only its payload before embedding. Prefer the publisher's lower-resolution variant of the exact same image from `srcset` or its documented thumbnail/CDN metadata. When the current task genuinely has image-conversion capability, resize that same image to a 640 px longest edge, encode as JPEG or WebP at roughly 75–82 quality, and target 200 KB or less. Do not substitute another image merely to meet the size target. If neither a small variant nor conversion is available, embed the same original image when its public HTTPS URL is stable; successful viewing takes priority over the size target. Every embedded image must include alternative text. Only when the original image is also unsuitable for public embedding should the output show a plain-language image description instead of a broken image. Never replace a missing image with a visible image URL or source-page link; ordinary news citations remain unchanged.

## Image delivery options considered

1. Directly hotlink the full-size publisher image: smallest implementation, but fragile and unnecessarily heavy on mobile. Rejected.
2. Use the exact same image's publisher-provided small variant, or resize that same image when conversion is actually available, then allow the same original and finally a text-only fallback: preserves the editorial choice, avoids broken placeholders, and needs no new service. Chosen.
3. Download, resize, and serve images from an owned CDN: most controllable, but adds storage, copyright, cache invalidation, and daily publishing infrastructure. Deferred until the user explicitly wants a managed image backend.

## Boundaries

- Do not modify the existing Codex automation contract.
- Do not require file uploads, voice, custom GPTs, Codex, shell access, or repository writes during a daily run.
- Do not fabricate resized URLs or claim image transcoding unless the current task actually provides that capability.
- Use GitHub/web access and Scheduled Task conversation memory only.
- Keep the monitoring inputs to regions, optional weighted topics, and the GitHub URL.
- Publish this change directly to GitHub `main` as requested.

## Verification

One contract test checks that the mobile files select Instant, reject Thinking/Pro, contain the required fourteen-day/C-or-higher/image rules, and contain no Codex or shell bootstrap dependency. A second contract test requires the 640 px/200 KB target, one-image limit, same-original fallback, alternative text, rejection of unstable image URLs, and absence of a visible image source-page fallback. Existing pipeline contract tests remain green.
