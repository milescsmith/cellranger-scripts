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

    gex_libraries = df[df["Sample_Name"].str.contains("gex")]
    if np.any(gex_libraries):
        reformatted_gex_libs = pd.DataFrame(
            data={
                "fastq_id": gex_libraries["Sample_Name"],
                "fastqs": [
                    project_path.joinpath(_) for _ in gex_libraries["Sample_ID"]
                ],
                "lanes": lanes,
                "feature_types": "gene expression",
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
