from typing import Dict, Any
from typeguard import typechecked

@typechecked
def create_slurm_header(header_options: Dict[str, Any]) -> str:

    job_header = "#! /bin/bash -l\n"

    if "job_name" in header_options:
        job_header += f"#SBATCH -J {header_options['job_name']}\n"
    if "log_file" in header_options:
        job_header += f"#SBATCH -o {header_options['log_file']}\n"
    if "email_status" in header_options:
        job_header += f"#SBATCH --mail-user={header_options['email_address']}\n"
        job_header += f"#SBATCH --mail-type={header_options['email_status']}\n"
    if "mem" in header_options:
        job_header += f"#SBATCH --mem={header_options['mem']}G\n"
    else:
        job_header += f"#SBATCH --mem=8G"
    if "partition" in header_options:
        job_header += f"#SBATCH --partition={header_options['partition']}\n"
    else:
        job_header += f"#SBATCH --partition=serial\n"
    if "nodes" in header_options:
        job_header += f"#SBATCH --nodes={header_options['nodes']}\n"
    else:
        job_header += f"#SBATCH --nodes=1\n"
    if "cpus" in header_options:
        job_header += f"#SBATCH --cpus-per-task={header_options['cpus']}\n"
    else:
        job_header += f"#SBATCH --cpus-per-task=1\n"

    job_header += f"export _JAVA_OPTIONS='-Xmx64G -Xms4G -XX:+UseParallelGC -XX:ParallelGCThreads=8'\n"

    return job_header