import os
from typing import List, Optional, Dict, Any, Union, Callable
from pydantic import BaseModel, Field, field_validator, ConfigDict


import yaml
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class TransformType(Enum):
    TO_FLOAT = "to_float"
    TO_INT = "to_int"
    TO_BOOL = "to_bool"
    PARSE_VECTOR3 = "parse_vector3"
    PARSE_VECTOR2 = "parse_vector2"


@dataclass
class AttributeMapping:
    """属性映射配置"""
    source: str
    target: str
    transform: Optional[TransformType] = None
    flatten_to_root: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AttributeMapping':
        transform_str = data.get('transform')
        transform = TransformType(transform_str) if transform_str else None
        flatten_to_root = data.get('flatten_to_root', False)
        return cls(
            source=data['source'],
            target=data['target'],
            transform=transform,
            flatten_to_root=flatten_to_root
        )


@dataclass
class EntityConfig:
    """实体配置基类"""
    selector: str
    name: str
    is_array: bool
    attributes: List[AttributeMapping] = field(default_factory=list)
    children: Dict[str, 'EntityConfig'] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntityConfig':
        # 提取基本字段
        selector = data.get('selector', '')
        name = data.get('name', '')
        is_array = data.get('is_array', False)

        # 解析属性映射
        attributes = []
        for attr_data in data.get('attributes', []):
            attributes.append(AttributeMapping.from_dict(attr_data))

        # 递归解析子实体
        children = {}
        for child_name, child_data in data.get('children', {}).items():
            children[child_name] = cls.from_dict(child_data)

        return cls(
            selector=selector,
            name=name,
            is_array=is_array,
            attributes=attributes,
            children=children
        )


@dataclass
class Config:
    """解析器主配置"""
    CONFIGFILE: str
    package_path: List[str]
    output_format: str
    pretty_print: bool
    include_source: bool

    defaults: Dict[str, Any] = field(default_factory=dict)
    entities: Dict[str, EntityConfig] = field(default_factory=dict)

    def __post_init__(self):
        """Convert dictionary entities to EntityConfig objects after initialization."""
        if isinstance(self.entities, dict):
            converted_entities = {}
            for entity_name, entity_data in self.entities.items():
                if isinstance(entity_data, dict):
                    converted_entities[entity_name] = EntityConfig.from_dict(entity_data)
                elif isinstance(entity_data, EntityConfig):
                    converted_entities[entity_name] = entity_data
                else:
                    raise ValueError(f"Invalid entity configuration for {entity_name}")
            self.entities = converted_entities

    @field_validator('package_path')
    def path_must_exists(cls, v):
        for item in v:
            if not os.path.exists(item):
                raise RuntimeError(
                    f"target package path doesn't exists: {item}")
        return v

    def _entity_to_dict(self, entity: EntityConfig) -> Dict[str, Any]:
        """将EntityConfig对象转换为字典"""
        result = {
            'selector': entity.selector,
            'name': entity.name,
            'is_array': entity.is_array
        }

        # 转换属性映射
        if entity.attributes:
            result['attributes'] = []
            for attr in entity.attributes:
                attr_dict = {
                    'source': attr.source,
                    'target': attr.target
                }
                if attr.transform:
                    attr_dict['transform'] = attr.transform.value
                if attr.flatten_to_root:
                    attr_dict['flatten_to_root'] = attr.flatten_to_root
                result['attributes'].append(attr_dict)

        # 递归转换子实体
        if entity.children:
            result['children'] = {}
            for child_name, child_config in entity.children.items():
                result['children'][child_name] = self._entity_to_dict(
                    child_config)

        return result

    def get_entity_config(self, entity_name: str) -> Optional[EntityConfig]:
        """获取指定名称的实体配置"""
        return self.entities.get(entity_name)

    def get_child_config(self, parent_name: str, child_name: str) -> Optional[EntityConfig]:
        """获取指定父实体的子实体配置"""
        parent = self.get_entity_config(parent_name)
        if parent:
            return parent.children.get(child_name)
        return None


class Temp(BaseModel):
    model_config = ConfigDict(extra='forbid')
    res_file: List[str] = Field(default_factory=list)
    conf_file: List[str] = Field(default_factory=list)
    final: List[Dict[str, Any]] = Field(default_factory=list)