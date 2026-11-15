# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document catalogues Python modules, classes, and exported functions. See Map Coverage for any stack it does not index.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `14`
- **Total Classes**: `19`
- **Total Top-Level Functions**: `36`
- **Total Class Methods**: `107`
- **Total Source Lines**: `1880`

## 🧭 Map Coverage
- **Indexed**: python (`14` module(s))
- **Not indexed by this map**: none (no non-Python source files were found)

---

## 📦 Modules & Exported Symbols

### [`driftwood/__init__.py`](driftwood/__init__.py)
> *Driftwood: rank code hotspots from local git history and file complexity.*

**Size**: `19` lines (`524` bytes)

---

### [`driftwood/__main__.py`](driftwood/__main__.py)
**Size**: `4` lines (`88` bytes)

---

### [`driftwood/cli.py`](driftwood/cli.py)
> *Command-line entry point for the driftwood hotspot report.*

**Size**: `265` lines (`9161` bytes)

**Functions:**
- `def _positive_int(raw)`
- `def _non_negative_float(raw)`
- `def _is_supported_since(value)` - *Reject git's silent approxidate fallbacks, accept documented forms only.*
- `def _since_value(raw)`
- `def build_parser()`
- `def _display_score(score)` - *The score as the table renders it, so --min-score filters what is shown.*
- `def _matches(path, include, exclude)`
- `def _group_by_dir(churn, complexity)` - *Aggregate file churn and complexity per directory (top-level: ``.``).*
- `def main(argv)`

---

### [`driftwood/complexity.py`](driftwood/complexity.py)
> *Language-aware complexity estimates that need only the standard library.*

**Size**: `114` lines (`3346` bytes)

**Functions:**
- `def python_complexity(source)` - *Cyclomatic-style count for Python: 1 + decision points (bounded by source size).*
- `def generic_complexity(source)` - *Cheap multi-language estimate: 1 + lines carrying a branching marker.*
- `def _line_has_decision(line)`
- `def file_complexity(path)` - *Estimate complexity for a file, returning 0 for unreadable, oversized or binary files.*
- `def complexity_map(root, paths)` - *Map each existing relative path in `paths` to its complexity estimate.*

---

### [`driftwood/gitlog.py`](driftwood/gitlog.py)
> *Read per-file churn from a local git repository without third-party tools.*

**Size**: `225` lines (`7880` bytes)

**Classes:**
- `class GitError` - *A git invocation failed; the message carries Why and Fix guidance.*
- `class FileChurn` - *Aggregated history for one file: commit count and added/deleted lines.*
  - Method `.with_change(added, deleted)`
  - Property `.churn`

**Functions:**
- `def git_session(total_seconds)` - *Cap the cumulative wall time of the git calls made inside the block.*
- `def session_deadline()` - *The active session's absolute deadline, or None outside git_session().*
- `def _call_timeout()`
- `def _run_git(repo, args)`
- `def _unquote_path(raw)` - *Decode git's C-style quoted path and say whether the input was quoted.*
- `def normalize_path(raw)` - *Reduce git's rename notation to the newest path, using forward slashes.*
- `def parse_numstat(text)` - *Aggregate `git log --numstat --format=__COMMIT__%H` output per file.*
- `def list_worktree_files(repo, runner)` - *List tracked plus untracked-but-not-ignored files, NUL-safe.*
- `def collect_churn(repo, *, since, max_commits, runner)` - *Return `{path: FileChurn}` for history up to `max_commits` commits.*
- `def repo_root(repo, runner)` - *Resolve the work-tree root that `repo` belongs to.*

---

### [`driftwood/report.py`](driftwood/report.py)
> *Render ranked hotspots as a fixed-width table or JSON.*

**Size**: `117` lines (`4105` bytes)

**Functions:**
- `def _sanitize_path(path)` - *Keep one-hotspot-one-line: replace control and line-separator characters.*
- `def _row(index, item)`
- `def format_table(hotspots)` - *Render an aligned, header-first table; paths stay at the end to avoid wrapping.*
- `def _csv_safe_cell(text)` - *Neutralize spreadsheet formula interpretation of a leading character.*
- `def format_csv(hotspots)` - *Render hotspots as CSV, one row per hotspot, header always present.*
- `def format_json(hotspots)` - *Render hotspots as stable JSON for scripting.*

---

### [`driftwood/scoring.py`](driftwood/scoring.py)
> *Blend churn and complexity into a single, comparable hotspot score.*

**Size**: `102` lines (`3684` bytes)

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
**Size**: `375` lines (`16748` bytes)

**Classes:**
- `class CliTests`
  - Method `._run(argv, churn, error)`
  - Method `.test_table_output_sorted_by_score()`
  - Method `.test_json_output()`
  - Method `.test_group_by_dir_adds_file_metrics()`
  - Method `.test_group_by_dir_puts_top_level_files_under_dot()`
  - Method `.test_group_by_dir_ranks_dirs_by_complexity_too()`
  - Method `.test_exclude_filter_drops_paths()`
  - Method `.test_include_filter_keeps_matching_paths()`
  - Method `.test_empty_include_keeps_all_paths()`
  - Method `.test_git_error_returns_one_with_remediation()`
  - Method `.test_min_score_filters_before_top_slices()`
  - Method `.test_display_score_matches_table_column()`
  - Method `.test_min_score_keeps_row_that_displays_above_threshold()`
  - Method `.test_include_match_is_case_sensitive()`
  - Method `.test_invalid_numeric_flags_exit_two()`
  - Method `.test_parser_defaults_are_fresh()`
  - Method `.test_empty_churn_table_returns_zero_with_guidance()`
  - Method `.test_repo_root_git_error_returns_one()`
  - Method `.test_file_arg_uses_parent_dir()`
  - Method `.test_broken_pipe_does_not_raise()`
  - Method `.test_broken_pipe_on_real_fd_redirects_to_devnull()`
  - Method `.test_broken_pipe_does_not_close_stdout()`
  - Method `.test_main_runs_git_inside_budget_session()`
  - Method `.test_all_adds_zero_churn_files_ranked_by_complexity()`
  - Method `.test_all_restricted_to_code_files()`
  - Method `.test_all_off_by_default()`
  - Method `.test_since_accepts_documented_forms()`
  - Method `.test_since_rejects_approxidate_garbage()`
  - Method `.test_since_garbage_exits_two_before_git()`
  - Method `.test_blank_since_returns_two_without_traceback()`

**Functions:**
- `def _churn()`

---

### [`tests/test_complexity.py`](tests/test_complexity.py)
**Size**: `107` lines (`4005` bytes)

**Classes:**
- `class PythonComplexityTests`
  - Method `.test_counts_decision_tokens()`
  - Method `.test_syntax_error_falls_back_to_line_scan()`
  - Method `.test_trivial_module_is_one()`
- `class GenericComplexityTests`
  - Method `.test_counts_branch_lines_across_languages()`
  - Method `.test_comment_and_blank_lines_are_skipped()`
  - Method `.test_case_paren_counted()`
- `class FileComplexityTests`
  - Method `.test_dispatches_python_and_generic_files()`
  - Method `.test_missing_file_and_map_skip_absent_paths()`
  - Method `.test_map_rejects_absolute_and_parent_escape()`
  - Method `.test_capped_read_rejects_oversized()`
  - Method `.test_binary_null_byte_scores_zero()`
  - Method `.test_map_skips_symlinks()`

---

### [`tests/test_gitlog.py`](tests/test_gitlog.py)
**Size**: `234` lines (`8212` bytes)

**Classes:**
- `class _FakeClock` - *Stands in for gitlog.time so tests move the clock without sleeping.*
  - Method `.__init__()`
  - Method `.monotonic()`
- `class ListWorktreeFilesTests`
  - Method `.test_splits_nul_separated_entries_and_drops_empties()`
  - Method `.test_asks_git_for_tracked_plus_untracked_respecting_gitignore()`
  - Method `.test_empty_output_is_empty_list()`
- `class GitTimeoutBudgetTests`
  - Method `.test_no_session_keeps_default_per_call_timeout()`
  - Method `.test_session_lets_a_single_call_use_remaining_budget()`
  - Method `.test_exhausted_budget_fails_fast_and_names_the_budget()`
  - Method `.test_session_resets_deadline_on_exit()`
- `class ParseNumstatTests`
  - Method `.test_aggregates_changes_across_commits()`
  - Method `.test_ignores_binary_and_malformed_lines()`
  - Method `.test_renamed_paths_resolve_to_new_location()`
  - Method `.test_empty_input_is_empty_mapping()`
  - Method `.test_non_numeric_counts_are_skipped()`
- `class NormalizePathTests`
  - Method `.test_plain_path_keeps_forward_slashes()`
  - Method `.test_quoted_path_is_unquoted()`
  - Method `.test_quoted_non_ascii_path_is_decoded()`
  - Method `.test_quoted_backslash_is_not_a_separator()`
- `class CollectChurnTests`
  - Method `.test_passes_filters_and_reuses_parser()`
  - Method `.test_rejects_non_positive_commit_limit()`
  - Method `.test_rejects_blank_since()`
  - Method `.test_negative_counts_are_skipped()`
  - Method `.test_extra_tab_path_joined()`
  - Method `.test_repo_root_strips_whitespace()`
  - Method `.test_repo_root_rejects_empty_output()`
  - Method `.test_repo_root_preserves_trailing_space()`

**Functions:**
- `def _captured_run(timeouts)`

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
**Size**: `135` lines (`5383` bytes)

**Classes:**
- `class FormatTableTests`
  - Method `.test_header_and_rows()`
  - Method `.test_empty_report_explains_why_and_fix()`
  - Method `.test_embedded_newline_does_not_add_row()`
  - Method `.test_all_control_chars_sanitized()`
  - Method `.test_unicode_line_separators_sanitized()`
  - Method `.test_generator_input_renders()`
  - Method `.test_long_path_truncated_with_ellipsis()`
  - Method `.test_json_preserves_unicode_and_rejects_nan()`
- `class FormatJsonTests`
  - Method `.test_payload_is_stable_and_parseable()`
- `class FormatCsvTests`
  - Method `._rows(raw)`
  - Method `.test_header_and_data_rows()`
  - Method `.test_empty_input_is_header_only()`
  - Method `.test_comma_path_is_quoted_as_one_cell()`
  - Method `.test_control_and_bidi_chars_sanitized()`
  - Method `.test_score_matches_table_display_precision()`
  - Method `.test_formula_leading_paths_get_tick_guard()`
  - Method `.test_normal_path_gets_no_tick()`
  - Method `.test_no_trailing_blank_line()`

---

### [`tests/test_scoring.py`](tests/test_scoring.py)
**Size**: `95` lines (`3897` bytes)

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
  - Method `.test_nan_inf_weights_rejected()`
  - Method `.test_non_int_top_rejected()`
  - Method `.test_zero_weights_yield_zero_scored_but_retained()`
  - Method `.test_invalid_complexity_values_rejected()`

**Functions:**
- `def _churn(churn, commits, added, deleted)`

---
