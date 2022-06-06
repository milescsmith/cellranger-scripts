"""Command-line interface."""
from enum import Enum
from pathlib import Path
from shutil import which
from typing import List, Optional

import pandas as pd
import typer

from pathlib import Path


from . import __version__, console
from .multi import create_multi_sheet
from .slurm.header import create_slurm_header
from .utils import resolve, parse_args

from rich.traceback import install
from structlog import get_logger

# from . import typer_funcs

install(show_locals=True)
log = get_logger()

def version_callback(value: bool):
    """Prints the version of the package."""
    if value:
        console.print(
            f"[yellow]cellranger_scripts[/] version: [bold blue]{__version__}[/]"
        )
        raise typer.Exit()


app = typer.Typer(
    name="cellranger_scripts",
    help=(
        "Generate some of the config and scripts necessary "
        "for processing single cell data with Cell Ranger"
    ),
)


class JobManager(str, Enum):
    """Used to enforce job manager choices."""

    SLURM = "SLURM"
    NONE = None


class Partition(str, Enum):
    """Current list of SLURM partitions of which I am aware."""

    SERIAL = "serial"
    DEBUG = "debug"
    INTERACTIVE = "interactive"
    HIGHMEM = "highmem"
    GPU = "gpu"


class StatusMessage(str, Enum):
    """Possible statuses for the job manager to send an alert for."""

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
    """Potential kit chemistry options."""

    auto = "auto"
    threeprime = "threeprime"
    fiveprime = "fiveprime"
    SC3Pv1 = "SC3Pv1"
    SC3Pv2 = "SC3Pv2"
    SC3Pv3 = "SC3Pv3"
    SC5P_PE = "SC5P-PE"
    SC5P_R2 = "SC5P-R2"
    SC_FB = "SC-FB"


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
        help=(
            "Should the path to the references "
            "be checked to see if they actually exist?"
        ),
    ),
    ctx: typer.Context = typer.Option(
        ..., help="Extra options to pass to the job script"
    ),
) -> None:
    """Generate library config csvs for Cell Ranger multi."""
    log.info("loading samplesheet...", samplesheet=str(samplesheet))
    if samplesheet.exists():
        ss = pd.read_csv(samplesheet, skiprows=8)

    if not bypass_checks:
        if gene_expression_reference:
            log.info(
                "checking for the existence of the gene expression reference\t",
                ref=str(gene_expression_reference),
                exists=gene_expression_reference.exists(),
                is_dir=gene_expression_reference.is_dir()
                )
            if (
                not gene_expression_reference.exists()
                and not gene_expression_reference.is_dir()
            ):
                raise FileNotFoundError(
                    "The path to the gene expression reference does not appear to be valid"
                )
        if vdj_reference:
            log.info(
                "checking for the existence of the vdj reference\t\t\t", 
                ref=str(vdj_reference),
                exists=vdj_reference.exists(),
                is_dir=vdj_reference.is_dir()
                )
            if not vdj_reference.exists() and not vdj_reference.is_dir():
                raise FileNotFoundError(
                    "The path to the VDJ reference does not appear to be valid"
                )
        if feature_reference:
            log.info(
                "checking for the existence of the feature reference\t\t",
                ref=str(feature_reference),
                exists=feature_reference.exists(),
                is_file=feature_reference.is_file()
                )
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
                log.info("writing config to file", outdir=str(outdir), index=i, name=per_sample_multiconfig.index[i])
                mc.writelines(j)
            if job_manager:
                log.info("writing job file", outdir=str(outdir), job_name=per_sample_multiconfig.index[i], name=per_sample_multiconfig.index[i])
                multi_job(
                    multi_config=outdir.joinpath(
                        per_sample_multiconfig.index[i]
                    ).with_suffix(".csv"),
                    job_name=per_sample_multiconfig.index[i],
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
            "Label to give sample and will be used by Cell Ranger to name the output directory. "
            "If not provided, the name will be extracted from the multi config csv."
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
    cellranger_path: Optional[Path] = typer.Option(
        None,
        "--cellranger_path",
        "-cp",
        help="Path to the cellranger folder.",
    ),
) -> None:
    """Quickly create a job file to perform counting with 10X's Cellranger"""
    # TODO: maybe just move a lot of this to a snakemake pipeline?
    cellranger_path = resolve(cellranger_path)
    if cellranger_path is None:
        cellranger_path = which("cellranger")
        if cellranger_path is None:
            raise FileNotFoundError(
                "No path to the cellranger executable was provided and it does not appear to be on the PATH."
            )
    
    cellranger_path = Path(cellranger_path)
    
    if cellranger_path.is_dir():
        cellranger_path = cellranger_path.joinpath("cellranger")

    kwargs = {
        k: v.default if isinstance(v, typer.models.OptionInfo) else v
        for (k, v) in locals().items()
    }
    kwargs["multi_config"] = multi_config
    kwargs["cellranger_path"] = cellranger_path
    return _multi_job(**kwargs)


def _multi_job(
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
    **kwargs,
):
    """Hack so that we can use the `multi_job()` function as both a typer cli function
    and a callable function
    """
    if "sample_name" not in kwargs or kwargs["sample_name"] is None:
        kwargs["sample_name"] = kwargs["multi_config"].stem

    multi_cmd = (
        f"{kwargs['cellranger_path']} multi \\\n"
        f"\t--id {kwargs['sample_name']} \\\n"
        f"\t--csv {kwargs['multi_config'].resolve()} \\\n"
        f"\t--jobinterval 2000 \\\n"
        f"\t--localcores {kwargs['cpus']} \\\n"
        f"\t--localmem {kwargs['memory']}"
    )

    if "job_name" not in kwargs or kwargs["job_name"] is None:
        kwargs["job_name"] = kwargs["multi_config"].stem

    if "log_file" not in kwargs or kwargs["log_file"] is None:
        kwargs["log_file"] = f"{kwargs['multi_config'].stem}.job"

    kwargs["status"] = ",".join([_.value for _ in kwargs["status"]])

    # Using a dictionary to store/pass values here to make
    # swapping out the job manager and associated functions easier
    # if other job managers are ever added

    header_options = {
        "job_name": kwargs["job_name"],
        "log_file": kwargs["log_file"],
        "email_address": kwargs["email"],
        "email_status": kwargs["status"],
        "mem": kwargs["memory"],
        "cpus": kwargs["cpus"],
        "partition": kwargs["partition"],
    }

    if kwargs["job_manager"] == JobManager.SLURM:
        job_header = create_slurm_header(header_options)
    else:
        job_header = ""
    # TODO: put more manager profiles here.  maybe up the required python version so
    # we can use the structural pattern matching instead of an elif tree

    job_script = job_header + "\n" + multi_cmd

    if "job_out" not in kwargs or kwargs["job_out"] is None:
        job_out = kwargs["multi_config"].stem
    else:
        job_out = kwargs["job_out"]

    output_jobscript = Path(f"{job_out}_multi.job")
    console.print(f"Writing jobscript to {output_jobscript.resolve()}")

    with output_jobscript.open("w") as f:
        f.writelines(job_script)


if __name__ == "__main__":
    app()  # pragma: no cover
