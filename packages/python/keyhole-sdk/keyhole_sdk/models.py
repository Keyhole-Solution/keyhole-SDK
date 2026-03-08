from pydantic import BaseModel
from typing import Any


class RealizationPackage(BaseModel):
    package_id: str
    promotion_id: str
    payload: dict[str, Any] = {}


class RealizationReceipt(BaseModel):
    package_id: str
    status: str
    message: str = ""
