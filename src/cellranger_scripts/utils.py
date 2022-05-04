from typing import Any, Dict

from typer.models import OptionInfo


def resolve(arg: Any) -> Any:
    if isinstance(arg, OptionInfo):
        return arg.default
    else:
        return arg


def parse_args(args: str) -> Dict[str, str]:
    """parse a string such as '--setting_one thing --setting_two other_thing --setting_three
    into a dictionary like {'setting_one': 'thing', 'setting_two': 'other_thing', 'setting_three': True}
    """
    args_dict = dict()
    for i, x in enumerate(args):
        if x.startswith("--"):
            if i + 1 < len(args):
                if not args[i + 1].startswith("--"):
                    args_dict[x.replace("--", "")] = args[i + 1]
                elif args[i + 1].startswith("--"):
                    args_dict[x] = True
    return args_dict