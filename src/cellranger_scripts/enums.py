"""enums restricting the possible options for typer-based clis"""
from enum import Enum

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