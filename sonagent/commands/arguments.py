import argparse
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional

from sonagent.commands.cli_options import AVAILABLE_CLI_OPTIONS
from sonagent.constants import DEFAULT_CONFIG


ARGS_COMMON = ["verbosity", "logfile", "version", "config", "datadir", "user_data_dir"]
ARGS_BUILD_CONFIG = ["config"]
ARGS_RUN = ["sd_notify", "dry_run_wallet"]
NO_CONF_REQURIED = []


class Arguments:

    """
    Arguments Class. Manage the arguments received by the cli
    """

    def __init__(self, args: Optional[List[str]]) -> None:
        self.args = args
        self._parsed_arg: Optional[argparse.Namespace] = None

    def get_parsed_arg(self) -> Dict[str, Any]:
        """
        Return the list of arguments
        :return: List[str] List of arguments
        """
        if self._parsed_arg is None:
            self._build_subcommands()
            self._parsed_arg = self._parse_args()

        return vars(self._parsed_arg)

    def _parse_args(self) -> argparse.Namespace:
        """
        Parses given arguments and returns an argparse Namespace instance.
        """
        parsed_arg = self.parser.parse_args(self.args)

        # Workaround issue in argparse with action='append' and default value
        # (see https://bugs.python.org/issue16399)
        # Allow no-config for certain commands (like downloading / plotting)
        # print("------------")
        # print(parsed_arg.config)

        if ('config' in parsed_arg and parsed_arg.config is None):
            print("go here ")
            conf_required = ('command' in parsed_arg and parsed_arg.command in NO_CONF_REQURIED)

            if 'user_data_dir' in parsed_arg and parsed_arg.user_data_dir is not None:
                user_dir = parsed_arg.user_data_dir
            else:
                # Default case
                user_dir = 'user_data'
                # Try loading from "user_data/config.json"
            cfgfile = Path(user_dir) / DEFAULT_CONFIG
            if cfgfile.is_file():
                parsed_arg.config = [str(cfgfile)]
            else:
                # Else use "config.json".
                cfgfile = Path.cwd() / DEFAULT_CONFIG
                if cfgfile.is_file() or not conf_required:
                    parsed_arg.config = [DEFAULT_CONFIG]

        return parsed_arg

    def _build_args(self, optionlist, parser):

        for val in optionlist:

            opt = AVAILABLE_CLI_OPTIONS[val]
            parser.add_argument(*opt.cli, dest=val, **opt.kwargs)


    def _build_subcommands(self) -> None:
        """
        Builds and attaches all subcommands.
        :return: None
        """

        # Build shared arguments (as group Common Options)
        _common_parser = argparse.ArgumentParser(add_help=False)
        group = _common_parser.add_argument_group("Common arguments")
        self._build_args(optionlist=ARGS_COMMON, parser=group)

        self.parser = argparse.ArgumentParser(description='SonAgent')
        self._build_args(optionlist=['version'], parser=self.parser)

        from sonagent.commands import (start_sonagent)

        subparsers = self.parser.add_subparsers(dest='command',
                                        # Use custom message when no subhandler is added
                                        # shown from `main.py`
                                        # required=True
                                        )
        
        # Add trade subcommand
        start_cmd = subparsers.add_parser('run', help='SonAgent run.',
                                          parents=[_common_parser])
        start_cmd.set_defaults(func=start_sonagent)
        self._build_args(optionlist=ARGS_RUN, parser=start_cmd)
