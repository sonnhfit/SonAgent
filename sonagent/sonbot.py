import logging
import traceback
from copy import deepcopy
from datetime import datetime, time, timedelta, timezone
from math import isclose
from threading import Lock
from time import sleep
from typing import Any, Dict, List, Optional, Tuple

from sonagent.mixins import LoggingMixin
from sonagent.enums import State
                             

logger = logging.getLogger(__name__)


class SonBot(LoggingMixin):
    def __init__(self, config: dict) -> None:
        self.state = State.STOPPED

        self.config = config

        