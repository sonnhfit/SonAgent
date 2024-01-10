from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class Ping(BaseModel):
    status: str


class AccessToken(BaseModel):
    access_token: str


class AccessAndRefreshToken(AccessToken):
    refresh_token: str


class Version(BaseModel):
    version: str