# Direct Article Image Delivery Route Design

## Goal

Prevent mobile-native from treating a failed native image-search/card result as proof that an image is unavailable when the cited article exposes a usable current-event image URL.

## Root cause

The existing evidence contract proves that the source page and four source tiers were inspected, but it does not prove that an image URL found in the article (`img`, `srcset`, `og:image`, or equivalent structured media field) was opened as media and passed to a host-visible delivery attempt. Consequently, a failed search card can be recorded as the delivery attempt even when a direct JPEG/WebP URL remains usable.

## Design

Add `direct_media_url_attempted` to each existing event record in `image-evidence.json`. It means that every usable direct media URL discovered on the selected source page was actually opened/fetched through the host's available media path before source exhaustion or `NATIVE_MEDIA_UNAVAILABLE` was declared. It does not mean that a bare URL or Markdown link was delivered.

The canonical route is:

1. Inspect the cited article and extract current-event `img`, `srcset`, `og:image`, and equivalent direct media URLs.
2. Open/fetch a usable direct JPEG/WebP URL as media and attempt visible delivery.
3. If no usable direct media URL can be delivered, continue the existing official/party, wire, and reliable-media same-event fallbacks.
4. Permit `source_exhausted` or `delivery_unavailable` only when `direct_media_url_attempted=true` and the existing four-tier exhaustion requirements hold.

A successfully delivered direct article image does not require unnecessary later fallback searches. A known direct image URL with no visible-delivery attempt cannot become `NATIVE_MEDIA_UNAVAILABLE`.

## Scope boundaries

- Reuse the existing image-evidence artifact, mobile run manager, capability code, visual recovery stage, and tests.
- Do not add a schema file, validator, receipt, recovery state, compatibility mode, or source class.
- Do not weaken the qualified-image delivery hard gate.
- Do not treat an external image URL or Markdown link as visible delivery.

## Verification

- A simulated current article with a qualified direct JPEG but `direct_media_url_attempted=false` must be rejected.
- A direct article JPEG opened and visibly delivered may pass without searching later fallback tiers.
- Existing source-exhaustion and visual-recovery regressions remain green.
