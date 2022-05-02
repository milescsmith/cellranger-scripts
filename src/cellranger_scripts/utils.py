from typing import Any
from typer.models import OptionInfo

def resolve(arg: Any) -> Any:
    if isinstance(arg, OptionInfo):
        return arg.default
    else:
        return arg