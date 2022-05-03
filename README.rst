cellranger_scripts

|PyPI| |Status| |Python Version| |License| |Read the Docs| |Tests| |Codecov| |pre-commit| |Black|
|Activity|

.. |PyPI| image:: https://img.shields.io/pypi/v/cellranger-scripts.svg
   :target: https://pypi.org/project/cellranger-scripts/
   :alt: PyPI
.. |Status| image:: https://img.shields.io/pypi/status/cellranger-scripts.svg
   :target: https://pypi.org/project/cellranger-scripts/
   :alt: Status
.. |Python Version| image:: https://img.shields.io/pypi/pyversions/cellranger-scripts
   :target: https://pypi.org/project/cellranger-scripts
   :alt: Python Version
.. |License| image:: https://img.shields.io/pypi/l/cellranger-scripts
   :target: https://opensource.org/licenses/GPL-3.0
   :alt: License
.. |Read the Docs| image:: https://img.shields.io/readthedocs/cellranger-scripts/latest.svg?label=Read%20the%20Docs
   :target: https://cellranger-scripts.readthedocs.io/
   :alt: Read the documentation at https://cellranger-scripts.readthedocs.io/
.. |Tests| image:: https://github.com/milescsmith/cellranger-scripts/workflows/Tests/badge.svg
   :target: https://github.com/milescsmith/cellranger-scripts/actions?workflow=Tests
   :alt: Tests
.. |Codecov| image:: https://codecov.io/gh/milescsmith/cellranger-scripts/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/milescsmith/cellranger-scripts
   :alt: Codecov
.. |pre-commit| image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit
.. |Black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Black
.. |Activity| image:: https://repobeats.axiom.co/api/embed/a212f644c6aab9c2a3b78f1ec3824662a6f635fc.svg
   :target: https://repobeats.axiom.co
   :alt: Repobeats analytics image

Writing the various scripts and sample sheets for `Cell Ranger <https://support.10xgenomics.com/single-cell-gene-expression/software/pipelines/latest/what-is-cell-ranger>`_ and a job manager to process the sequencing data for
samples generated using 10X Genomics kits quickly becomes tedious; however, most of the information needed is present
in the original sample sheet used for demultiplexing and the other config files share most of their settings.

Cellranger-scripts attempts to simplify the generation of the scripts necessary to take the data from bcls to 
`sample_molecule_info.h5`

Features
--------

* Create config files for Cell Ranger multi
* Create SLURM scripts for running Cell Ranger multi


Requirements
------------

* Python >= 3.8.3
* bcl2fastq-style samplesheet


Installation
------------

.. You can install *cellranger_scripts* via pip_ from PyPI_:

You can install *cellranger_scripts* via pip_ from github_:

.. code:: console

   $ pip install git+https://github.com/milescsmith/cellranger-scripts


Usage
-----

Currently, cellranger-scripts has two subcommands:

* multi_config: generates the config CSVs required by Cell Ranger multi
* multi_job: generates job files to run Cell Ranger multi on a job manager

multi_config:
~~~~~~~~~~~~~
.. code:: console

   Usage: cellranger-scripts multi_config [OPTIONS] SAMPLESHEET PROJECT_PATH OUTDIR

   Generate library config csvs for Cell Ranger multi.

   Arguments:
   SAMPLESHEET   Path to the samplesheet.csv used by bcl2fastq  [required]
   PROJECT_PATH  Path to the project root  [required]
   OUTDIR        Location to which the library config CSVs should be saved.
                  Each file will be named according to The 'Sample_Project'
                  column value in the samplesheet  [required]

   Options:
   -d, --data_subfolder DIRECTORY  If the FASTQs are located in a subfolder,
                                    what is the relative path to the data?,
                                    (e.g., use ifFASTQs are located somewhere
                                    like 'project_path/data/fastqs')
   -g, --gex_ref PATH              Path to directory with the gene expression
                                    reference index
   -v, --vdj_ref PATH              Path to directory with the VDJ reference
                                    index
   -f, --feature_ref FILE          Path to the feature reference file
   -s, --subsample_rate INTEGER
   -e, --expected_cells INTEGER
   -p, --split                     Should a separate library config be written
                                    for each sample (provided that the sample
                                    name is in the 'Sample_Project' field)?
                                    [default: True]
   -j, --job_script [SLURM|None]   Create batch script for submission to a job
                                    manager
   -b, --bypass_checks             Should the path to the references be checked
                                    to see if they actually exist?  [default:
                                    True]
   --help                          Show this message and exit.


multi_job: 
~~~~~~~~~~
.. code:: console

   Usage: cellranger-scripts multi_job [OPTIONS] MULTI_CONFIG

   Quickly create a job file to perform counting with 10X's Cellranger

   TODO: maybe just move a lot of this to a snakemake pipeline?

   Arguments:
   MULTI_CONFIG  Path to the multi config csv file  [required]

   Options:
   -i, --id TEXT                   Label to give sample and will be used by
                                    Cell Ranger to name the output directory. If
                                    not provided, the name will be extracted
                                    from the multi config csv.  [default:
                                    other_name]
   -j, --manager [SLURM|None]      Target job manager to write a submission
                                    script for  [default: JobManager.SLURM]
   -f, --job_out PATH              Path to which job files should be saved
   -n, --job_name TEXT             Name to give job (only used to identify job
                                    in the job manager)
   -l, --log TEXT                  Name to give log file. If not provided, the
                                    sample name read from the config csv.
   -m, --mem INTEGER               Amount of memory to request for the job (in
                                    GB)  [default: 32]
   -c, --cpus INTEGER              Number of CPUs to request for the job
                                    [default: 8]
   -s, --status [END|FAIL|START|NONE|BEGIN|REQUEUE|ALL|INVALID_DEPEND|STAGE_OUT|TIME_LIMIT|TIME_LIMIT_90|TIME_LIMIT_80|TIME_LIMIT_50|ARRAY_TASKS]
                                    Type of status updates to email. Pass the
                                    argument multiple times to signal for
                                    multiple statuses.  [default:
                                    StatusMessage.END, StatusMessage.FAIL]
   -e, --email TEXT                Email address to which to send status
                                    updates
   -p, --partition [serial|debug|interactive|highmem|gpu]
                                    Specify the cluster partition on which to
                                    run the job  [default: Partition.SERIAL]
   -cp, --cellranger_path TEXT     Path to the cellranger folder.
   --help                          Show this message and exit.


Contributing
------------

Contributions are very welcome.
To learn more, see the `Contributor Guide`_.


License
-------

Distributed under the terms of the `GPL 3.0 license`_,
*cellranger_scripts* is free and open source software.


Issues
------

If you encounter any problems,
please `file an issue`_ along with a detailed description.


Credits
-------

This project was generated from `@cjolowicz`_'s `Hypermodern Python Cookiecutter`_ template.

.. _@cjolowicz: https://github.com/cjolowicz
.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _GPL 3.0 license: https://opensource.org/licenses/GPL-3.0
.. _PyPI: https://pypi.org/
.. _Hypermodern Python Cookiecutter: https://github.com/cjolowicz/cookiecutter-hypermodern-python
.. _file an issue: https://github.com/milescsmith/cellranger-scripts/issues
.. _pip: https://pip.pypa.io/
.. github-only
.. _Contributor Guide: CONTRIBUTING.rst
.. _Usage: https://cellranger-scripts.readthedocs.io/en/latest/usage.html
