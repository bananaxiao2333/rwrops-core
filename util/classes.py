import os
from typing import List

from pydantic import BaseModel, Field, field_validator


class Config(BaseModel):
    CONFIGFILE: str
    package_path: List[str] = Field()

    @field_validator('package_path')
    def path_must_exists(cls, v):
        for item in v:
            if not os.path.exists(item):
                raise RuntimeError(
                    f"target package path doesn't exsits: {item}")
        return v


class Temp(BaseModel):
    res_file: List = Field(default=[])
    conf_file: List = Field(default=[])

    final: List = Field(default=[])
