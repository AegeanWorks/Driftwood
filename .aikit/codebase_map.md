# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document provides an automated, up-to-date registry of all modules, classes, and exported functions across this repository.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `14`
- **Total Classes**: `15`
- **Total Top-Level Functions**: `24`
- **Total Class Methods**: `46`
- **Total Source Lines**: `948`

---

## 📦 Modules & Exported Symbols

### [`driftwood/__init__.py`](driftwood/__init__.py)
> *Driftwood: rank code hotspots from local git history and file complexity.*

**Size**: `19` lines (`524` bytes)

---

### [`driftwood/__main__.py`](driftwood/__main__.py)
**Size**: `3` lines (`57` bytes)

---

### [`driftwood/cli.py`](driftwood/cli.py)
> *Command-line entry point for the driftwood hotspot report.*

**Size**: `102` lines (`3391` bytes)

**Functions:**
- `def _positive_int(raw)`
- `def _non_negative_float(raw)`
- `def build_parser()`
- `def _matches(path, include, exclude)`
- `def main(argv)`

---

### [`driftwood/complexity.py`](driftwood/complexity.py)
> *Language-aware complexity estimates that need only the standard library.*

**Size**: `90` lines (`2365` bytes)

**Functions:**
- `def python_complexity(source)` - *Cyclomatic-style count for Python: 1 + decision points (bounded by source size).*
- `def generic_complexity(source)` - *Cheap multi-language estimate: 1 + lines carrying a branching marker.*
- `def _line_has_decision(line)`
- `def file_complexity(path)` - *Estimate complexity for a file, returning 0 for unreadable or oversized files.*
- `def complexity_map(root, paths)` - *Map each existing relative path in `paths` to its complexity estimate.*

---

### [`driftwood/gitlog.py`](driftwood/gitlog.py)
> *Read per-file churn from a local git repository without third-party tools.*

**Size**: `138` lines (`4548` bytes)

**Classes:**
- `class GitError` - *A git invocation failed; the message carries Why and Fix guidance.*
- `class FileChurn` - *Aggregated history for one file: commit count and added/deleted lines.*
  - Method `.with_change(added, deleted)`
  - Property `.churn`

**Functions:**
- `def _run_git(repo, args)`
- `def _unquote_path(raw)` - *Decode git's C-style quoted path and say whether the input was quoted.*
- `def normalize_path(raw)` - *Reduce git's rename notation to the newest path, using forward slashes.*
- `def parse_numstat(text)` - *Aggregate `git log --numstat --format=__COMMIT__%H` output per file.*
- `def collect_churn(repo, *, since, max_commits, runner)` - *Return `{path: FileChurn}` for history up to `max_commits` commits.*
- `def repo_root(repo, runner)` - *Resolve the work-tree root that `repo` belongs to.*

---

### [`driftwood/report.py`](driftwood/report.py)
> *Render ranked hotspots as a fixed-width table or JSON.*

**Size**: `54` lines (`1748` bytes)

**Functions:**
- `def _row(index, item)`
- `def format_table(hotspots)` - *Render an aligned, header-first table; paths stay at the end to avoid wrapping.*
- `def format_json(hotspots)` - *Render hotspots as stable JSON for scripting.*

---

### [`driftwood/scoring.py`](driftwood/scoring.py)
> *Blend churn and complexity into a single, comparable hotspot score.*

**Size**: `89` lines (`2712` bytes)

**Classes:**
- `class Hotspot` - *One ranked file: raw metrics plus the normalized blended score.*

**Functions:**
- `def normalize(values)` - *Min-max scale values to 0..1.*
- `def rank_hotspots(churn, complexity, *, top, churn_weight, complexity_weight)` - *Return hotspots ordered by score, highest first.*

---

### [`tests/__init__.py`](tests/__init__.py)
**Size**: `0` lines (`0` bytes)

---

### [`tests/test_cli.py`](tests/test_cli.py)
**Size**: `91` lines (`3424` bytes)

**Classes:**
- `class CliTests`
  - Method `._run(argv, churn, error)`
  - Method `.test_table_output_sorted_by_score()`
  - Method `.test_json_output()`
  - Method `.test_exclude_filter_drops_paths()`
  - Method `.test_include_filter_keeps_matching_paths()`
  - Method `.test_git_error_returns_one_with_remediation()`
  - Method `.test_min_score_filters_before_top_slices()`
  - Method `.test_invalid_numeric_flags_exit_two()`

**Functions:**
- `def _churn()`

---

### [`tests/test_complexity.py`](tests/test_complexity.py)
**Size**: `72` lines (`2381` bytes)

**Classes:**
- `class PythonComplexityTests`
  - Method `.test_counts_decision_tokens()`
  - Method `.test_syntax_error_falls_back_to_line_scan()`
  - Method `.test_trivial_module_is_one()`
- `class GenericComplexityTests`
  - Method `.test_counts_branch_lines_across_languages()`
  - Method `.test_comment_and_blank_lines_are_skipped()`
- `class FileComplexityTests`
  - Method `.test_dispatches_python_and_generic_files()`
  - Method `.test_missing_file_and_map_skip_absent_paths()`

---

### [`tests/test_gitlog.py`](tests/test_gitlog.py)
**Size**: `104` lines (`3205` bytes)

**Classes:**
- `class ParseNumstatTests`
  - Method `.test_aggregates_changes_across_commits()`
  - Method `.test_ignores_binary_and_malformed_lines()`
  - Method `.test_renamed_paths_resolve_to_new_location()`
  - Method `.test_empty_input_is_empty_mapping()`
- `class NormalizePathTests`
  - Method `.test_plain_path_keeps_forward_slashes()`
  - Method `.test_quoted_path_is_unquoted()`
  - Method `.test_quoted_non_ascii_path_is_decoded()`
  - Method `.test_quoted_backslash_is_not_a_separator()`
- `class CollectChurnTests`
  - Method `.test_passes_filters_and_reuses_parser()`
  - Method `.test_rejects_non_positive_commit_limit()`
  - Method `.test_repo_root_strips_whitespace()`

---

### [`tests/test_integration_git.py`](tests/test_integration_git.py)
**Size**: `88` lines (`3170` bytes)

**Classes:**
- `class RealRepositoryTests`
  - Method `.setUp()`
  - Method `._commit(message)`
  - Method `.test_collect_churn_reads_real_history()`
  - Method `.test_repo_root_resolves_subdirectory()`
  - Method `.test_rename_moves_churn_to_new_path()`
  - Method `.test_non_ascii_path_is_decoded()`

**Functions:**
- `def _git(repo, *args)`

---

### [`tests/test_report.py`](tests/test_report.py)
**Size**: `37` lines (`1189` bytes)

**Classes:**
- `class FormatTableTests`
  - Method `.test_header_and_rows()`
  - Method `.test_empty_report_explains_why_and_fix()`
- `class FormatJsonTests`
  - Method `.test_payload_is_stable_and_parseable()`

---

### [`tests/test_scoring.py`](tests/test_scoring.py)
**Size**: `61` lines (`2329` bytes)

**Classes:**
- `class NormalizeTests`
  - Method `.test_scales_to_unit_interval()`
  - Method `.test_flat_positive_values_saturate_and_zeros_stay_zero()`
  - Method `.test_empty_mapping()`
- `class RankHotspotsTests`
  - Method `.test_blends_normalized_metrics()`
  - Method `.test_missing_complexity_counts_as_zero()`
  - Method `.test_single_churned_file_is_not_scored_zero()`
  - Method `.test_top_limits_rows_and_is_deterministic()`
  - Method `.test_empty_churn_returns_empty()`
  - Method `.test_negative_weights_and_bad_top_are_rejected()`

**Functions:**
- `def _churn(churn, commits, added, deleted)`

---
