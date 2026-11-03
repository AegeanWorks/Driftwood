# Decisions

Why this project is built the way it is, oldest first. One entry per decision that changes a
contract, a dependency, a data format or the architecture; IDs are consecutive and never reused.

<!-- Entry format:
### ADR-NNN: <decision in one line>
- **Date**: YYYY-MM-DD
- **Status**: Accepted
- **Context**: <what forced the decision>
- **Decision**: <what was decided>
- **Consequences**: <what follows, including what it costs>
-->

### ADR-001: Blend normalized churn and complexity with stdlib-only analysis
- **Date**: 2026-10-28
- **Status**: Accepted
- **Context**: A hotspot report must be comparable across files and run offline, without installing language-specific analyzers.
- **Decision**: Churn comes from `git log --numstat`; complexity is a decision-point count (Python tokens, generic line heuristic). Both metrics are min-max normalized across the selected files and blended 0.6/0.4.
- **Consequences**: Scores are relative to the analyzed range, so changing `--since` or `--commits` changes them; the metric is a heuristic, not a linter, and only text files that still exist are scored. No dependency beyond git and the standard library.

### ADR-002: Saturate a flat metric instead of zeroing it
- **Date**: 2026-10-28
- **Status**: Accepted
- **Context**: Min-max scaling of a metric with no spread mapped every file to `0.0`, so a repository with one churned file (or uniformly churned files) reported real hotspots as `0.000`.
- **Decision**: When a metric has no spread, positive values map to `1.0` and zero stays `0.0`; `--min-score` now filters before `--top` slices.
- **Consequences**: Scores stay comparable and a lone hotspot is visible. A flat metric can no longer distinguish two equally hot files, which is intended: there is no evidence in the data to rank them apart, so the path tie-break applies.

### ADR-003: Case-sensitive filters and strict numstat skipping
- **Date**: 2026-11-03
- **Status**: Accepted
- **Context**: `--include`/`--exclude` used `fnmatch.fnmatch`, which is case-insensitive on Windows and case-sensitive elsewhere, so the same filter kept different files per platform; `parse_numstat` also raised `ValueError` on a tab-separated line with non-numeric counts instead of skipping it like other malformed lines.
- **Decision**: Match filters with `fnmatch.fnmatchcase` so git paths filter identically on every platform; skip numstat lines whose counts do not parse as integers.
- **Consequences**: Windows runs that relied on case-insensitive matching now need exact-case globs; corrupt or future git count tokens no longer crash the report and are ignored like binary entries.
