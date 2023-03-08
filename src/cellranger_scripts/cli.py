"""Command-line interface."""
import typer

from . import __version__, console
from . import multi
from . import arc

from rich.traceback import install
from structlog import get_logger

# from . import typer_funcs

install(show_locals=True, width=300, extra_lines=6, word_wrap=True)
log = get_logger()


def version_callback(value: bool):
    """Prints the version of the package."""
    if value:
        console.print(
            f"[yellow]cellranger_scripts[/] version: [bold blue]{__version__}[/]"
        )
        raise typer.Exit()


cs = typer.Typer(
    name="cellranger_scripts",
    help=(
        "Generate some of the config and scripts necessary "
        "for processing single cell data with Cell Ranger"
    ),
    add_completion=False,
    rich_markup_mode="markdown",
)

cs.add_typer(multi.app, name="multi")
cs.add_typer(arc.app, name="arc")

# if __name__ == "__main__":
#     app()  # pragma: no cover
