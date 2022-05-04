# [0.4.0] - 2022-05-04

## Changed

- Moved `parse_args()` from `__main__` to `utils`
- Renamed `multi_job_internal()` to `_multi_job`

## Fixes

- Fixed problem of spaces being removed where they should not have been
- Changed "gene_expression" to "gene expression" in `multi.create_library_section()`
- Fixed where extra `cellranger` was being added to the path to the cellranger executable
- Fixed where an extra space was being added at the end of the lines for the job script in `_multi_job`

[0.4.0]: https://github.com/milescsmith/cellranger-scripts/releases/tag/0.4.0
[0.3.0]: https://github.com/milescsmith/cellranger-scripts/releases/tag/0.3.0