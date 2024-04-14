import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sonagent.loggers import bufferHandler
from sonagent.utils.datetime_helpers import format_date
from sonagent.cell import BaseCell
from sonagent.nerve_system.nerve import Nerve

logger = logging.getLogger(__name__)


class ImmuneSystem:
    """
    Class for Self Immune System that allows self-monitoring and self-recovery of the system.
    """
    error_logs = []

    def __init__(self) -> None:
        self.nerve = Nerve()

    @staticmethod
    def get_logs(limit: Optional[int]) -> Dict[str, Any]:
        """Returns the last X logs"""
        if limit:
            buffer = bufferHandler.buffer[-limit:]
        else:
            buffer = bufferHandler.buffer
        records = [[format_date(datetime.fromtimestamp(r.created)),
                   r.created * 1000, r.name, r.levelname,
                   r.message + ('\n' + r.exc_text if r.exc_text else '')]
                   for r in buffer]
        return {'log_count': len(records), 'logs': records}
    
    def immune_scan(self) -> None:
        """
        Scan the system for any anomalies.
        """
        logs = ImmuneSystem.get_logs(5)

        # Check for any errors in the logs
        errors = [log for log in logs['logs'] if log[3] == 'ERROR']
        
        errors_detected = []
        for error in errors:
            if error not in ImmuneSystem.error_logs:
                ImmuneSystem.error_logs.append(error)
                errors_detected.append(error)

        if len(errors_detected) > 0:
            logger.info(f"Errors detected: {errors_detected}")
            # send alert to Nerve System
            self.nerve.stimulation(errors_detected)
            
        else:
            logger.debug("No errors detected.")

    def immune_recover(self) -> None:
        """
        Recover the system from any anomalies.
        """
        if ImmuneSystem.error_logs:
            print(f"Recovering from errors: {ImmuneSystem.error_logs}")
            logger.info(f"Recovering from errors: {ImmuneSystem.error_logs}")
            ImmuneSystem.error_logs = []
        else:
            print("No errors detected.")
            logger.info("No errors detected.")


class ImmuneCell(BaseCell):
    def __init__(self) -> None:
        super().__init__()
        self.immune = ImmuneSystem()
    
    def scan(self) -> None:
        self.immune.immune_scan()

    def recover(self) -> None:
        self.immune.immune_recover()

