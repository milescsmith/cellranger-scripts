"""arc.py - functions specific to cellranger arc."""
from pathlib import Path
from typing import Optional
import re

import typer

from .slurm.header import create_slurm_header
from .utils import resolve, parse_args
from .enums import JobManager, StatusMessage, Partition
import numpy as np
import pandas as pd
from typeguard import typechecked
from structlog import get_logger
from rich.traceback import install

install(show_locals=True, width=300, extra_lines=6, word_wrap=True)

log = get_logger()

app = typer.Typer()

@typechecked
def create_library_section(
    df: pd.DataFrame,
    project_path: Optional[Path] = None,
    data_subfolder: Optional[Path] = None,
    lanes: str = "",
    subsample_rate: Optional[int] = None,
    use_sample_name: Optional[bool] = False,
) -> pd.DataFrame:
    """Generate the config CSV for cellranger multi

    Parameters
    ----------
    df : pd.DataFrame
        The data from the bcl2fastq samplesheet.csv
    project_path : Optional[Path], optional
        Root directory containing the data. If not provided, assumed to be
        the directory from which this script was called. By default None
    data_subfolder : Optional[Path], optional
        Relative path to directory containing FASTQs, by default None
    lanes : str, optional
        In what flowcell lane(s) was this sample sequenced.  If
        not provided, assumed to be all lanes. By default None
    subsample_rate : Optional[int], optional
        The rate at which reads from the provided FASTQ files are sampled.
        Must be strictly greater than 0 and less than or equal to 1. By default None
    use_sample_name : Optional[bool], optional
        Are the libraries prefixed with the information from the "Sample_Name" column?
        If so, use the samplesheet "Sample_Name" column in the config "fastq_id" column
        and the samplesheet "Sample_ID" column in the config "fastqs" column; otherwise,
        use "Sample_ID" and "Sample_Project", respectively

    Returns
    -------
    pd.DataFrame
        DataFrame that can easily be translated to the format required
        by cellranger multi
    """
    # TODO: this *should* read the lane information from the samplesheet instead of asking for it

    if project_path is None:
        project_path = Path.cwd()

    if data_subfolder is not None:
        project_path = project_path.joinpath(data_subfolder)

    if use_sample_name:
        fastq_id = "Sample_Name"
        folder_name = "Sample_ID"
    else:
        fastq_id = "Sample_ID"
        folder_name = "Sample_Project"

    gex_libraries = df[df["Sample_Name"].str.contains("gex")]
    if np.any(gex_libraries):
        reformatted_gex_libs = pd.DataFrame(
            data={
                "fastq_id": gex_libraries[fastq_id],
                "fastqs": [
                    str(project_path.joinpath(_)) for _ in gex_libraries[folder_name]
                ],
                "lanes": lanes,
                "feature_types": "Gene Expression",
                "subsample_rate": "" if subsample_rate is None else subsample_rate,
            }
        )
    else:
        reformatted_gex_libs = None

    bcr_libraries = df[df["Sample_Name"].str.contains("bcr")]
    if np.any(bcr_libraries):
        reformatted_bcr_libs = pd.DataFrame(
            data={
                "fastq_id": bcr_libraries[fastq_id],
                "fastqs": [
                    str(project_path.joinpath(_)) for _ in bcr_libraries[folder_name]
                ],
                "lanes": lanes,
                "feature_types": "VDJ-B",
                "subsample_rate": "" if subsample_rate is None else subsample_rate,
            }
        )
    else:
        reformatted_bcr_libs = None

    tcr_libraries = df[df["Sample_Name"].str.contains("tcr")]
    if np.any(tcr_libraries):
        reformatted_tcr_libs = pd.DataFrame(
            data={
                "fastq_id": tcr_libraries[fastq_id],
                "fastqs": [
                    str(project_path.joinpath(_)) for _ in tcr_libraries[folder_name]
                ],
                "lanes": lanes,
                "feature_types": "VDJ-T",
                "subsample_rate": "" if subsample_rate is None else subsample_rate,
            }
        )
    else:
        reformatted_tcr_libs = None

    feature_libraries = df[
        df["Sample_Name"].str.contains("feature|antibody|totalseq|citeseq|feat", regex=True)
    ]
    if np.any(feature_libraries):
        reformatted_feature_libs = pd.DataFrame(
            data={
                "fastq_id": feature_libraries[fastq_id],
                "fastqs": [
                    str(project_path.joinpath(_)) for _ in feature_libraries[folder_name]
                ],
                "lanes": lanes,
                "feature_types": "Antibody Capture",
                "subsample_rate": "" if subsample_rate is None else subsample_rate,
            }
        )
    else:
        reformatted_feature_libs = None

    return pd.concat(
        [
            reformatted_gex_libs,
            reformatted_bcr_libs,
            reformatted_tcr_libs,
            reformatted_feature_libs,
        ]
    )


@typechecked
def create_arc_sheet(
    df: pd.DataFrame,
    project_path: Optional[Path] = None,
    data_subfolder: Optional[Path] = None,
    gex_ref_path: Optional[Path] = None,
    vdj_ref_path: Optional[Path] = None,
    feature_ref_path: Optional[Path] = None,
    expected_cells: Optional[int] = None,
    lanes: str = "",
    subsample_rate: Optional[int] = None,
) -> str:
    gex_section = "[gene-expression]\ninclude-introns,true\n"
    if gex_ref_path:
        gex_section += f"reference,{gex_ref_path}\n"

    if expected_cells:
        gex_section += f"expect-cells,{expected_cells}\n"

    vdj_section = "[vdj]\n"
    if vdj_ref_path:
        vdj_section += f"reference,{vdj_ref_path}\n"

    feature_section = "[feature]\n"
    if feature_ref_path:
        feature_section += f"reference,{feature_ref_path}\n"

    library_section = (
        create_library_section(
            df,
            project_path=project_path,
            data_subfolder=data_subfolder,
            lanes=lanes,
            subsample_rate=subsample_rate,
        )
        .apply(
            lambda x: ",".join([str(_) for _ in x])
            .replace("\n", ","),
            axis=1,
        )
        .to_list()
    )

    multi_sheet = [
        gex_section,
        vdj_section,
        feature_section,
        "[libraries]\nfastq_id,fastqs,lanes,feature_types,subsample_rate",
        *library_section,
    ]

    return re.sub(pattern=r' {2,}', repl="", string="\n".join(multi_sheet))


@app.callback(invoke_without_command=True)
@app.command(
    name="arc_config",
    no_args_is_help=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def arc_config(
    rna_samplesheet: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the samplesheet.csv used by bcl2fastq/bclconvert for the snRNA-seq libraries",
    ),
    atac_samplesheet: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the samplesheet.csv used by bcl2fastq/bclconvert for the scATAC-seq libraries",
    ),
    project_path: Path = typer.Argument(
        ...,
        exists=False,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Path to the project root",
    ),
    outdir: Path = typer.Argument(
        ...,
        writable=True,
        resolve_path=True,
        help=(
            "Location to which the library config CSVs should be saved."
            "Each file will be named according to "
            "The 'Sample_Project' column value in the samplesheet"
        ),
    ),
    data_subfolder: Optional[Path] = typer.Option(
        None,
        "--data_subfolder",
        "-d",
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=False,
        help=(
            "If the FASTQs are located in a subfolder, what is the relative "
            "path to the data?, (e.g., use if FASTQs are located somewhere "
            "like 'project_path/data/fastqs')"
        ),
    ),
    reference: Optional[Path] = typer.Option(
        None,
        "--ref",
        "-r",
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Path to directory with the gene expression reference index",
    ),
    subsample_rate: Optional[int] = typer.Option(
        None,
        "--subsample_rate",
        "-s",
        help="",
    ),
    expected_number_of_cells: Optional[int] = typer.Option(
        None,
        "--expected_cells",
        "-e",
        help="",
    ),
    split_by_sample_name: bool = typer.Option(
        True,
        "--split",
        "-p",
        help=(
            "Should a separate library config be written for each sample "
            "(provided that the sample name is in the 'Sample_Project' field)?"
        ),
    ),
    job_manager: Optional[JobManager] = typer.Option(
        None,
        "--job_script",
        "-j",
        help="Create batch script for submission to a job manager",
    ),
    bypass_checks: Optional[bool] = typer.Option(
        True,
        "--bypass_checks",
        "-b",
        help=(
            "Should the path to the references "
            "be checked to see if they actually exist?"
        ),
    ),
    ctx: typer.Context = typer.Option(
        ..., help="Extra options to pass to the job script"
    ),
):
    """Generate library config csvs for Cell Ranger arc."""
    log.info("loading snRNA-seq samplesheet...", rna_samplesheet=str(rna_samplesheet))
    try:
        skiprows = [_.rstrip(",") for _ in rna_samplesheet.read_text().split("\n")].index('[Data]')
        rss = pd.read_csv(rna_samplesheet, skiprows=skiprows + 1)
        log.info(f"found {rss.shape[0]} rows")
    except FileNotFoundError as e:
        log.error(f"The file {rna_samplesheet} was not found")
        exit()
    
    log.info("loading scATAC-seq samplesheet...", atac_samplesheet=str(atac_samplesheet))
    try:
        skiprows = [_.rstrip(",") for _ in atac_samplesheet.read_text().split("\n")].index('[Data]')
        ass = pd.read_csv(atac_samplesheet, skiprows=skiprows + 1)
        log.info(f"found {ass.shape[0]} rows")
    except FileNotFoundError as e:
        log.error(f"The file {atac_samplesheet} was not found")
    
    if not bypass_checks:
        log.info("Performing checks...")
        log.info(
            "checking for the existence of the expression/genomic reference\t",
            ref=str(reference),
            exists=reference.exists(),
            is_dir=reference.is_dir()
        )
        if (
            not reference.exists()
            and not reference.is_dir()
        ):
            raise FileNotFoundError(
                "The path to the expression/genomic reference does not appear to be valid"
            )
    log.info("Creating config sheets...", split=split_by_sample_name)
    if split_by_sample_name:
        per_sample_multiconfig = ss.groupby("Sample_Project").apply(
            create_arc_sheet,
            project_path=project_path,
            data_subfolder=data_subfolder,  # I think we need to check if this exists and adjust accordingly?
            ref_path=reference,
            expected_cells=expected_number_of_cells,
            subsample_rate=subsample_rate,
        )
        for i, j in enumerate(per_sample_multiconfig):
            with outdir.joinpath(per_sample_multiconfig.index[i]).with_suffix(
                ".csv"
            ).open(mode="w+") as mc:
                log.info("writing config to file", outdir=str(outdir), index=i, name=per_sample_multiconfig.index[i])
                mc.writelines(j)
            if job_manager:
                log.info("writing job file", outdir=str(outdir), job_name=per_sample_multiconfig.index[i], name=per_sample_multiconfig.index[i])
                arc_job(
                    arc_config=outdir.joinpath(
                        per_sample_multiconfig.index[i]
                    ).with_suffix(".csv"),
                    job_name=per_sample_multiconfig.index[i],
                    **parse_args(ctx.args),
                )
    else:
        arcconfig_str: str = create_arc_sheet(
            df=ss,
            project_path=project_path,
            data_subfolder=data_subfolder,  # I think we need to check if this exists and adjust accordingly?
            ref_path=reference,
            expected_cells=expected_number_of_cells,
            subsample_rate=subsample_rate,
        )
        proj_name = ss["Sample_Project"][0]
        log.info("writing job file", outdir=str(outdir))
        with outdir.joinpath(proj_name).with_suffix(".csv").open("w") as of:
            of.writelines(arcconfig_str)

@app.callback(invoke_without_command=True)
@app.command(
    name="arc_job",
    no_args_is_help=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def arc_job():
    pass