# Regional Supplement Model Admission Design

## Goal

Guarantee that every verified in-window article group originating from a regional supplement is visible to the model before semantic event merging and six-dimension scoring. Media heat remains a recall and prioritization signal only.

## Scope

- Treat discovery sources whose role is `regional_supplement` as complete-admission sources.
- Resolve their candidate rows through `normalized_articles` and `provisional_article_groups` in the preprocessing artifact.
- Fail closed when any required regional group or any of its regional candidate rows is absent from the model selection artifact's `candidate_groups`.
- Do not require every GDELT group in this regional validator; global discovery completeness remains governed by the existing full-discovery and semantic-ledger contracts.
- Do not grade, select, exclude, or semantically merge events in this validator.

## Interface

`scripts/validate_local_source_admission.py` accepts:

- `--preprocessed`: output from `preprocess_news_candidates.py`.
- `--selection`: the model selection artifact containing `candidate_groups`.
- `--source-pool`: `news-source-pool.json` or another compatible source policy.

It exits non-zero for missing local groups, missing local candidate rows, duplicate group declarations, malformed references, or an empty configured local-source set. On success it prints auditable counts.

## Runtime contract

`REGIONAL_SUPPLEMENT_COMPLETE_MODEL_ADMISSION_GATE` runs after the model input artifact is materialized and before semantic merging or scoring. Absence from GDELT heat, Google Trends, Google News coverage, or keyword queues is never a valid reason to omit a regional-supplement group.

## Tests

- A CNA and China News group omitted from model input must fail.
- All required regional groups and rows present must pass.
- A regional group present without all of its regional article rows must fail.
- An unlisted GDELT-only group must not make this regional validator fail.

