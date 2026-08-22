# GDELT Archive-Primary Acquisition Design

Use official 15-minute export archives as the only complete GDELT discovery path. Exact-window filtering, URL normalization, heat calculation, and keyword convergence remain deterministic and do not use a model. If archive acquisition fails, allow one DOC API request as incomplete supplemental coverage without 429 waiting or retry; then use an age-labeled cache. CNA and China News Service remain regional supplements, and downstream model-card volume is unchanged.

Acceptance requires an archive-success test proving DOC API is not called, configuration and schedule contracts naming archive first, and existing focused fetcher tests passing.
