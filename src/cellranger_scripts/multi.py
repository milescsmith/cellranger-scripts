"""multi.py - functions specific to cellranger multi."""
from pathlib import Path
from typing import Optional
import re

import numpy as np
import pandas as pd
from typeguard import typechecked


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
