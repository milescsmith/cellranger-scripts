* [1.0.0] - 2023-03-01

** Added

- Support for Cell Ranger ARC

** Changed

- renamed "__main__.py" to "cli.py":
- moved the functions related to multi out of __main__.py and placed in multi.py

# [0.8.3] - 2022-06-06

## Changed

- Use the "Sample_Project" data for the folder name instead of the "Sample_ID" if the "Sample_ID"
  data is used to name the fastqs

# [0.8.2] - 2022-06-06

## Added

- added `feat` to the autodetect list for sample names

# [0.8.1] - 2022-06-06

## Added

- added few spots to log info for debugging purposes

# [0.8.0] - 2022-06-06

## Added

- added an option to specify whether to use the "Sample_ID" or "Sample_Name" columns from the samplesheet when
  naming files in the config file

## Changed

- Using `structlog` now
- Update dependencies

## Fixed

- the `[Data]` section of the samplesheet is now found automatically instead of the number of rows being hardcoded
- the sample name is now properly used in the job script for the `--id` argument

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

[0.8.1]: https://github.com/milescsmith/cellranger-scripts/releases/tag/0.8.0...0.8.1
[0.8.0]: https://github.com/milescsmith/cellranger-scripts/releases/tag/0.7.0...0.8.0
[0.7.0]: https://github.com/milescsmith/cellranger-scripts/releases/tag/0.6.0...0.7.0
[0.6.0]: https://github.com/milescsmith/cellranger-scripts/releases/tag/0.5.0...0.6.0
[0.5.0]: https://github.com/milescsmith/cellranger-scripts/releases/tag/0.4.0...0.5.0
[0.4.0]: https://github.com/milescsmith/cellranger-scripts/releases/tag/0.3.0...0.4.0
[0.3.0]: https://github.com/milescsmith/cellranger-scripts/releases/tag/0.3.0