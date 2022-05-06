# [0.7.0] - 2022-05-06

## Fixed

- There are things other than GEX libraries, like TCR and BCR, so maybe we should label those appropriately in
    the multi config csv?  Well, that is now fixed.

# [0.6.0] - 2022-05-05

## Fixed

- path to FASTQs is no longer truncated

# [0.5.0] - 2022-05-04

## Fixed

- Now we actually add the data path in the multi config CSV!

# [0.4.0] - 2022-05-04

## Changed

- Moved `parse_args()` from `__main__` to `utils`
- Renamed `multi_job_internal()` to `_multi_job`

## Fixes

- Fixed problem of spaces being removed where they should not have been
- Changed "gene_expression" to "gene expression" in `multi.create_library_section()`
- Fixed where extra `cellranger` was being added to the path to the cellranger executable
- Fixed where an extra space was being added at the end of the lines for the job script in `_multi_job`

[0.6.0]: https://github.com/milescsmith/cellranger-scripts/releases/tag/0.5.0...0.6.0
[0.5.0]: https://github.com/milescsmith/cellranger-scripts/releases/tag/0.4.0...0.5.0
[0.4.0]: https://github.com/milescsmith/cellranger-scripts/releases/tag/0.3.0...0.4.0
[0.3.0]: https://github.com/milescsmith/cellranger-scripts/releases/tag/0.3.0