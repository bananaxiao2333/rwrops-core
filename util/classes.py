import os
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class SubAttrRule(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tag: str
    to: str


class EntityRule(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tag: str
    abbr: Optional[str] = None
    to: str
    multi: Optional[bool] = False
    sub_attrs: Optional[List[SubAttrRule]] = None


class EntityConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    vehicle: List[EntityRule]


class InheritConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool
    base_attr: str


class Config(BaseModel):
    CONFIGFILE: str
    model_config = ConfigDict(extra='forbid')
    package_path: List[str]
    inherit: Optional[InheritConfig] = None
    entities: Optional[List[EntityConfig]] = None

    @field_validator('package_path')
    def path_must_exists(cls, v):
        for item in v:
            if not os.path.exists(item):
                raise RuntimeError(
                    f"target package path doesn't exists: {item}")
        return v


class Temp(BaseModel):
    model_config = ConfigDict(extra='forbid')
    res_file: List[str] = Field(default_factory=list)
    conf_file: List[str] = Field(default_factory=list)
    final: List[Dict[str, Any]] = Field(default_factory=list)
