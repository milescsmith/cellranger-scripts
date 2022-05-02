"""Command-line interface."""
from enum import Enum
from pathlib import Path
from typing import List, Optional
from shutil import which
from rich import print as rprint
import inspect

import numpy as np
import pandas as pd
import typer
import click
from typeguard import typechecked

from . import __version__, console
from .slurm.header import create_slurm_header
from .utils import resolve
# from . import typer_funcs

def version_callback(value: bool):
    """Prints the version of the package."""
    if value:
        console.print(
            f"[yellow]cellranger_scripts[/] version: [bold blue]{__version__}[/]"
        )
        raise typer.Exit()


app = typer.Typer(
    # name="cellranger_scripts",
    # help="Generate some of the config and scripts necessary for processing single cell data with Cell Ranger",
)


class JobManager(str, Enum):
    SLURM = "SLURM"
    NONE = None


class Partition(str, Enum):
    SERIAL = "serial"
    DEBUG = "debug"
    INTERACTIVE = "interactive"
    HIGHMEM = "highmem"
    GPU = "gpu"


class StatusMessage(str, Enum):
    END = "END"
    FAIL = "FAIL"
    START = "START"
    NONE = "NONE"
    BEGIN = "BEGIN"
    REQUEUE = "REQUEUE"
    ALL = "ALL"
    INVALID_DEPEND = "INVALID_DEPEND"
    STAGE_OUT = "STAGE_OUT"
    TIME_LIMIT = "TIME_LIMIT"
    TIME_LIMIT_90 = "TIME_LIMIT_90"
    TIME_LIMIT_80 = "TIME_LIMIT_80"
    TIME_LIMIT_50 = "TIME_LIMIT_50"
    ARRAY_TASKS = "ARRAY_TASKS"


class Chemistry(str, Enum):
    auto = "auto"
    threeprime = "threeprime"
    fiveprime = "fiveprime"
    SC3Pv1 = "SC3Pv1"
    SC3Pv2 = "SC3Pv2"
    SC3Pv3 = "SC3Pv3"
    SC5P_PE = "SC5P-PE"
    SC5P_R2 = "SC5P-R2"
    SC_FB = "SC-FB"


@typechecked
def create_library_section(
    df: pd.DataFrame,
    project_path: Optional[Path] = None,
    data_subfolder: Optional[Path] = None,
    lanes: str = "",
    subsample_rate: Optional[int] = None,
) -> pd.DataFrame:

    # TODO: this *should* read the lane information from the samplesheet instead of asking for it

    if project_path is None:
        project_path = Path.cwd()

    if data_subfolder is not None:
        data_subfolder = project_path.joinpath(data_subfolder)

    gex_libraries = df[df["Sample_Name"].str.contains("gex")]
    if np.any(gex_libraries):
        reformatted_gex_libs = pd.DataFrame(
            data={
                "fastq_id": gex_libraries["Sample_Name"],
                "fastqs": [
                    project_path.joinpath(_) for _ in gex_libraries["Sample_ID"]
                ],
                "lanes": lanes,
                "feature_types": "gene_expression",
                "subsample_rate": "" if subsample_rate is None else subsample_rate,
            }
        )
    else:
        reformatted_gex_libs = None

    bcr_libraries = df[df["Sample_Name"].str.contains("bcr")]
    if np.any(bcr_libraries):
        reformatted_bcr_libs = pd.DataFrame(
            data={
                "fastq_id": gex_libraries["Sample_Name"],
                "fastqs": [
                    project_path.joinpath(_) for _ in bcr_libraries["Sample_ID"]
                ],
                "lanes": lanes,
                "feature_types": "vdj-b",
                "subsample_rate": "" if subsample_rate is None else subsample_rate,
            }
        )
    else:
        reformatted_bcr_libs = None

    tcr_libraries = df[df["Sample_Name"].str.contains("tcr")]
    if np.any(tcr_libraries):
        reformatted_tcr_libs = pd.DataFrame(
            data={
                "fastq_id": gex_libraries["Sample_Name"],
                "fastqs": [
                    project_path.joinpath(_) for _ in tcr_libraries["Sample_ID"]
                ],
                "lanes": lanes,
                "feature_types": "vdj-t",
                "subsample_rate": "" if subsample_rate is None else subsample_rate,
            }
        )
    else:
        reformatted_tcr_libs = None

    feature_libraries = df[
        df["Sample_Name"].str.contains("feature|antibody|totalseq|citeseq", regex=True)
    ]
    if np.any(feature_libraries):
        reformatted_feature_libs = pd.DataFrame(
            data={
                "fastq_id": feature_libraries["Sample_Name"],
                "fastqs": [
                    project_path.joinpath(_) for _ in feature_libraries["Sample_ID"]
                ],
                "lanes": lanes,
                "feature_types": "antibody capture",
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
def create_multi_sheet(
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
            lambda x: x.to_string(header=False, index=False)
            .replace(r" ", "")
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

    return "\n".join(multi_sheet)


@app.command(
    name="multi_config",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def multi_config(
    samplesheet: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Path to the samplesheet.csv used by bcl2fastq",
    ),
    project_path: Path = typer.Argument(
        ...,
        exists=True,
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
        help=f"Location to which the library config CSVs should be saved. Each file will be named according to "
        f"The 'Sample_Project' column value in the samplesheet",
    ),
    data_subfolder: Optional[Path] = typer.Option(
        None,
        "--data_subfolder",
        "-d",
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=False,
        help=f"If the FASTQs are located in a subfolder, what is the relative path to the data?, (e.g., use if"
        f"FASTQs are located somewhere like 'project_path/data/fastqs')",
    ),
    gene_expression_reference: Optional[Path] = typer.Option(
        None,
        "--gex_ref",
        "-g",
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Path to directory with the gene expression reference index",
    ),
    vdj_reference: Optional[Path] = typer.Option(
        None,
        "--vdj_ref",
        "-v",
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Path to directory with the VDJ reference index",
    ),
    feature_reference: Optional[Path] = typer.Option(
        None,
        "--feature_ref",
        "-f",
        dir_okay=False,
        file_okay=True,
        readable=True,
        resolve_path=True,
        help="Path to the feature reference file",
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
        help=f"Should a separate library config be written for each sample "
        f"(provided that the sample name is in the 'Sample_Project' field)?",
    ),
    job_manager: Optional[JobManager] = typer.Option(
        None,
        "--job_script",
        "-j",
        help="Create batch script for submission to a job manager",
    ),
    # TODO: add these options to their respective sections
    # gex_target_panel
    # gex_no_target_umi_filter
    # gex_r1_length
    # gex_r2_length
    # gex_chemistry
    # gex_force_cells
    # gex_include_introns
    # gex_no_secondary
    # gex_no_bam
    # feature_r1_length
    # feature_r2_length
    # inner_enrichment_primers
    # vdj_r1_length
    # vdj_r2_length
    bypass_checks: Optional[bool] = typer.Option(
        True,
        "--bypass_checks",
        "-b",
        help="Should the path to the references be checked to see if they actually exist?",
    ),
    ctx: typer.Context = typer.Option(
        ..., help="Extra options to pass to the job script"
    ),
) -> None:
    """Generate library config csvs for Cell Ranger multi."""
    
    if samplesheet.exists():
        ss = pd.read_csv(samplesheet, skiprows=8)

    if not bypass_checks:
        if gene_expression_reference:
            if (
                not gene_expression_reference.exists()
                and not gene_expression_reference.is_dir()
            ):
                raise FileNotFoundError(
                    "The path to the gene expression reference does not appear to be valid"
                )
        if vdj_reference:
            if not vdj_reference.exists() and not vdj_reference.is_dir():
                raise FileNotFoundError(
                    "The path to the VDJ reference does not appear to be valid"
                )
        if feature_reference:
            if not feature_reference.exists() and not feature_reference.is_file():
                raise FileNotFoundError(
                    "The path to the feature reference does not appear to be valid"
                )

    # TODO: check that the FASTQs are where we say they are
    # TODO: make adding each library optional?
    if split_by_sample_name:
        per_sample_multiconfig = ss.groupby("Sample_Project").apply(
            create_multi_sheet,
            project_path=project_path,
            data_subfolder=data_subfolder,  # I think we need to check if this exists and adjust accordingly?
            gex_ref_path=gene_expression_reference,
            vdj_ref_path=vdj_reference,
            feature_ref_path=feature_reference,
            expected_cells=expected_number_of_cells,
            subsample_rate=subsample_rate,
        )
        for i, j in enumerate(per_sample_multiconfig):
            with outdir.joinpath(per_sample_multiconfig.index[i]).with_suffix(
                ".csv"
            ).open(mode="w+") as mc:
                mc.writelines(j)
            if job_manager:
                multi_job(
                    multi_config=outdir.joinpath(
                        per_sample_multiconfig.index[i]
                    ).with_suffix(".csv"),
                    job_name = per_sample_multiconfig.index[i],
                    **parse_args(ctx.args),
                )
    else:
        multiconfig_str: str = create_multi_sheet(
            df=ss,
            project_path=project_path,
            data_subfolder=data_subfolder,  # I think we need to check if this exists and adjust accordingly?
            gex_ref_path=gene_expression_reference,
            vdj_ref_path=vdj_reference,
            feature_ref_path=feature_reference,
            expected_cells=expected_number_of_cells,
            subsample_rate=subsample_rate,
        )
        proj_name = ss["Sample_Project"][0]
        with outdir.joinpath(proj_name).with_suffix(".csv").open("w") as of:
            of.writelines(multiconfig_str)


@app.command(name="multi_job")
def multi_job(
    multi_config: Path = typer.Argument(
        ...,
        help="Path to the multi config csv file",
    ),
    sample_name: Optional[str] = typer.Option(
        "other_name",
        "--id",
        "-i",
        help=(
            f"Label to give sample and will be used by Cell Ranger to name the output directory. "
            f"If not provided, the name will be extracted from the multi config csv."
        ),
    ),
    job_manager: JobManager = typer.Option(
        JobManager.SLURM,
        "--manager",
        "-j",
        help="Target job manager to write a submission script for",
    ),
    job_out: Optional[Path] = typer.Option(
        None,
        "--job_out",
        "-f",
        help="Path to which job files should be saved",
    ),
    job_name: Optional[str] = typer.Option(
        None,
        "--job_name",
        "-n",
        help="Name to give job (only used to identify job in the job manager)",
    ),
    log_file: Optional[str] = typer.Option(
        None,
        "--log",
        "-l",
        help="Name to give log file. If not provided, the sample name read from the config csv.",
    ),
    memory: int = typer.Option(
        32, "--mem", "-m", help="Amount of memory to request for the job (in GB)"
    ),
    cpus: int = typer.Option(
        8, "--cpus", "-c", help="Number of CPUs to request for the job"
    ),
    status: List[StatusMessage] = typer.Option(
        [StatusMessage.END, StatusMessage.FAIL],
        "--status",
        "-s",
        help="Type of status updates to email. Pass the argument multiple times to signal for multiple statuses.",
    ),
    email: Optional[str] = typer.Option(
        None,
        "--email",
        "-e",
        help="Email address to which to send status updates",
    ),
    partition: Optional[Partition] = typer.Option(
        Partition.SERIAL,
        "--partition",
        "-p",
        help="Specify the cluster partition on which to run the job",
    ),
    # Can we just change to using shutil.which() to find this?
    cellranger_path: Optional[str] = typer.Option(
        None,
        "--cellranger_path",
        "-cp",
        help="Path to the cellranger folder.",
    ),
) -> None:
    """Quickly create a job file to perform counting with 10X's Cellranger

    TODO: maybe just move a lot of this to a snakemake pipeline?
    """
    
    cellranger_path = resolve(cellranger_path) 
    if cellranger_path is None:
        cellranger_path = which("cellranger")
        if cellranger_path is None:
            raise FileNotFoundError(
                "No path to the cellranger executable was provided and it does not appear to be on the PATH."
                )
    
    kwargs = {k:v.default if isinstance(v, typer.models.OptionInfo) else v for (k,v) in locals().items()}
    kwargs['multi_config'] = multi_config
    kwargs['cellranger_path'] = cellranger_path
    return multi_job_internal(
        **kwargs
    )

def multi_job_internal(
    # multi_config: Path,
    # sample_name: Optional[str] = None,
    # job_manager: Optional[JobManager] = JobManager.SLURM,
    # job_out: Optional[Path] = None,
    # job_name: Optional[str] = None,
    # log_file: Optional[str] = None,
    # memory: int = 32,
    # cpus: int = 8,
    # status: List[StatusMessage] = [StatusMessage.END, StatusMessage.FAIL],
    # email: Optional[str] = None,
    # partition: Optional[Partition] = Partition.SERIAL,
    # # Can we just change to using shutil.which() to find this?
    # cellranger_path: Optional[str] = None,
    **kwargs
):
    """Hack so that we can use the `multi_job()` function as both a typer cli function
    and a callable function
    """
    
    if "sample_name" not in kwargs or kwargs['sample_name'] is None:
        kwargs['sample_name'] = kwargs['multi_config'].stem

    multi_cmd = (
        f"{kwargs['cellranger_path']}/cellranger multi "
        f"--id {kwargs['sample_name']} "
        f"--csv {kwargs['multi_config'].resolve()} "
        f"--jobinterval 2000 "
        f"--localcores {kwargs['cpus']} "
        f"--localmem {kwargs['memory']}"
    )

    if "job_name" not in kwargs or kwargs['job_name'] is None:
        kwargs['job_name'] = kwargs['multi_config'].stem

    if "log_file" not in kwargs or kwargs['log_file'] is None:
        kwargs['log_file'] = f"{kwargs['multi_config'].stem}.job"

    # Using a dictionary to store/pass values here to make
    # swapping out the job manager and associated functions easier
    # if other job managers are ever added

    kwargs['status'] = ",".join([_.value for _ in kwargs['status']])

    header_options = {
        "job_name": kwargs['job_name'],
        "log_file": kwargs['log_file'],
        "email_address": kwargs['email'],
        "email_status": kwargs['status'],
        "mem": kwargs['memory'],
        "cpus": kwargs['cpus'],
        "partition": kwargs['partition'],
    }

    if kwargs['job_manager'] == JobManager.SLURM:
        job_header = create_slurm_header(header_options)
    else:
        job_header = ""
    # TODO: put more manager profiles here.  maybe up the required python version so
    # we can use the structural pattern matching instead of an elif tree

    job_script = job_header + "\n" + multi_cmd

    if "job_out" not in kwargs or kwargs['job_out'] is None:
        job_out = kwargs['multi_config'].stem
    else:
        job_out = kwargs['job_out']

    output_jobscript = Path(f"{job_out}_multi.job")
    console.print(f"Writing jobscript to {output_jobscript.resolve()}")

    with output_jobscript.open("w") as f:
        f.writelines(job_script)


def parse_args(args):
    args_dict = dict()
    for i, x in enumerate(args):
        if x.startswith("--"):
            if i+1 < len(args):
                if not args[i+1].startswith("--"):
                    args_dict[x.strip("--")] = args[i+1]
                elif args[i+1].startswith("--"):
                    args_dict[x] = True
    return args_dict

if __name__ == "__main__":
    app()  # pragma: no cover
