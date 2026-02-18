import os
import re
from datetime import datetime, timezone
from typing import Optional, Union

import arrow

from sonagent.constants import DATETIME_PRINT_FORMAT


def get_timezone() -> Union[timezone, arrow.Arrow]:
    """
    Get timezone from configuration or environment variable.
    Priority: 1. Environment variable SONAGENT_TIMEZONE
              2. Config file timezone setting
              3. Default to UTC
    
    Returns:
        timezone object or arrow timezone
    """
    # Check environment variable first
    env_timezone = os.environ.get('SONAGENT_TIMEZONE')
    if env_timezone:
        try:
            # Arrow can parse timezone strings
            return arrow.now(env_timezone).tzinfo
        except Exception:
            print(f"Warning: Unknown timezone '{env_timezone}' from environment variable, falling back to UTC")
    
    # Try to load from config file
    try:
        from sonagent.configuration.load_config import load_config_file
        config_path = os.environ.get('SONAGENT_CONFIG', 'user_data/config.json')
        if os.path.exists(config_path):
            config = load_config_file(config_path)
            config_timezone = config.get('timezone')
            if config_timezone:
                try:
                    return arrow.now(config_timezone).tzinfo
                except Exception:
                    print(f"Warning: Unknown timezone '{config_timezone}' in config file, falling back to UTC")
    except Exception:
        # Silently fail if config can't be loaded
        pass
    
    # Default to UTC
    return timezone.utc


def dt_now() -> datetime:
    """Return the current datetime in configured timezone (defaults to UTC)."""
    tz = get_timezone()
    if isinstance(tz, timezone):
        return datetime.now(tz)
    else:
        # arrow timezone object
        return datetime.now(tz)


def dt_utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0,
           microsecond: int = 0) -> datetime:
    """Return a datetime in UTC."""
    return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=timezone.utc)


def dt_ts(dt: Optional[datetime] = None) -> int:
    """
    Return dt in ms as a timestamp in UTC.
    If dt is None, return the current datetime in UTC.
    """
    if dt:
        return int(dt.timestamp() * 1000)
    return int(dt_now().timestamp() * 1000)


def dt_ts_def(dt: Optional[datetime], default: int = 0) -> int:
    """
    Return dt in ms as a timestamp in UTC.
    If dt is None, return the current datetime in UTC.
    """
    if dt:
        return int(dt.timestamp() * 1000)
    return default


def dt_floor_day(dt: datetime) -> datetime:
    """Return the floor of the day for the given datetime."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def dt_from_ts(timestamp: float) -> datetime:
    """
    Return a datetime from a timestamp.
    :param timestamp: timestamp in seconds or milliseconds
    """
    if timestamp > 1e10:
        # Timezone in ms - convert to seconds
        timestamp /= 1000
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def shorten_date(_date: str) -> str:
    """
    Trim the date so it fits on small screens
    """
    new_date = re.sub('seconds?', 'sec', _date)
    new_date = re.sub('minutes?', 'min', new_date)
    new_date = re.sub('hours?', 'h', new_date)
    new_date = re.sub('days?', 'd', new_date)
    new_date = re.sub('^an?', '1', new_date)
    return new_date


def dt_humanize(dt: datetime, **kwargs) -> str:
    """
    Return a humanized string for the given datetime.
    :param dt: datetime to humanize
    :param kwargs: kwargs to pass to arrow's humanize()
    """
    return arrow.get(dt).humanize(**kwargs)


def format_date(date: Optional[datetime]) -> str:
    """
    Return a formatted date string.
    Returns an empty string if date is None.
    :param date: datetime to format
    """
    if date:
        return date.strftime(DATETIME_PRINT_FORMAT)
    return ''


def format_ms_time(date: int) -> str:
    """
    convert MS date to readable format.
    : epoch-string in ms
    """
    return datetime.fromtimestamp(date / 1000.0).strftime('%Y-%m-%dT%H:%M:%S')
