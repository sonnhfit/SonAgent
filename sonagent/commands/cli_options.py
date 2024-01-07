from argparse import SUPPRESS, ArgumentTypeError
from sonagent import __version__
from sonagent import constants


def check_int_positive(value: str) -> int:
    try:
        uint = int(value)
        if uint <= 0:
            raise ValueError
    except ValueError:
        raise ArgumentTypeError(
            f"{value} is invalid for this parameter, should be a positive integer value"
        )
    return uint


def check_int_nonzero(value: str) -> int:
    try:
        uint = int(value)
        if uint == 0:
            raise ValueError
    except ValueError:
        raise ArgumentTypeError(
            f"{value} is invalid for this parameter, should be a non-zero integer value"
        )
    return uint


class Arg:
    # Optional CLI arguments
    def __init__(self, *args, **kwargs):
        self.cli = args
        self.kwargs = kwargs


# List of available command line options
AVAILABLE_CLI_OPTIONS = {
    # Common options
    "verbosity": Arg(
        '-v', '--verbose',
        help='Verbose mode (-vv for more, -vvv to get all messages).',
        action='count',
        default=0,
    ),
    "logfile": Arg(
        '--logfile', '--log-file',
        help="Log to the file specified. Special values are: 'syslog', 'journald'. "
             "See the documentation for more details.",
        metavar='FILE',
    ),
    "version": Arg(
        '-V', '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    ),
    "config": Arg(
        '-c', '--config',
        help=f'Specify configuration file (default: `userdir/{constants.DEFAULT_CONFIG}` '
        f'or `config.json` whichever exists). '
        f'Multiple --config options may be used. '
        f'Can be set to `-` to read config from stdin.',
        action='append',
        metavar='PATH',
    ),
    "datadir": Arg(
        '-d', '--datadir', '--data-dir',
        help='Path to directory with historical backtesting data.',
        metavar='PATH',
    ),
    "user_data_dir": Arg(
        '--userdir', '--user-data-dir',
        help='Path to userdata directory.',
        metavar='PATH',
    ),
    "sd_notify": Arg(
        '--sd-notify',
        help='Notify systemd service manager.',
        action='store_true',
    ),
    "dry_run": Arg(
        '--dry-run',
        help='Enforce dry-run for trading (removes Exchange secrets and simulates trades).',
        action='store_true',
    ),
    "dry_run_wallet": Arg(
        '--dry-run-wallet', '--starting-balance',
        help='Starting balance, used for backtesting / hyperopt and dry-runs.',
        type=float,
    ),
    "freqaimodel": Arg(
        '--freqaimodel',
        help='Specify a custom freqaimodels.',
        metavar='NAME',
    ),
    "freqaimodel_path": Arg(
        '--freqaimodel-path',
        help='Specify additional lookup path for freqaimodels.',
        metavar='PATH',
    ),
}