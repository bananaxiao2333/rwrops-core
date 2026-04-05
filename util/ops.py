from bs4 import BeautifulSoup, Tag
import os
from typing import Dict, List, Any, Optional
from .classes import Config, Temp


def parse_file(content: BeautifulSoup, config: Config, temp: Temp) -> Temp:
    cache = {}

    for entity_group in config.entities:
        for root_tag_name, rules in entity_group.items():
            for root_tag in content.find_all(root_tag_name):
                entity_data = parse_entity(root_tag, rules, root_tag_name)

                if config.inherit and config.inherit.enabled:
                    base_attr = config.inherit.base_attr
                    if base_attr in entity_data:
                        base_file = entity_data[base_attr]
                        base_entity = load_base_entity(
                            base_file, config, root_tag_name, cache)
                        if base_entity:
                            for key, value in base_entity.items():
                                if key not in entity_data:
                                    entity_data[key] = value

                entity_data["type"] = root_tag_name
                temp.final.append(entity_data)

    return temp


def parse_entity(root: Tag, rules: List[Any], entity_type: str) -> Dict[str, Any]:
    entity_data = {}

    for rule in rules:
        tag = rule.tag
        target = rule.to
        multi = rule.multi
        sub_attrs = rule.sub_attrs

        if tag.startswith("@"):
            attr = tag[1:]
            value = root.get(attr)
            if value is not None:
                entity_data[target] = value

        elif "/" in tag and "/@" in tag:
            tag_parts = tag.split("/@")
            tag_name = tag_parts[0]
            attr_name = tag_parts[1]

            if multi:
                elements = root.find_all(tag_name)
                values = []
                for element in elements:
                    attr_value = element.get(attr_name)
                    if attr_value is not None:
                        values.append(attr_value)
                if values:
                    entity_data[target] = values
            else:
                element = root.find(tag_name)
                if element:
                    attr_value = element.get(attr_name)
                    if attr_value is not None:
                        entity_data[target] = attr_value

        else:
            if multi:
                elements = root.find_all(tag)
                if elements:
                    if sub_attrs:
                        structured_data = []
                        for element in elements:
                            item_data = {}
                            for sub_rule in sub_attrs:
                                sub_tag = sub_rule.tag
                                sub_target = sub_rule.to
                                if sub_tag.startswith("@"):
                                    attr = sub_tag[1:]
                                    value = element.get(attr)
                                    if value is not None:
                                        item_data[sub_target] = value
                                elif sub_tag.startswith("#"):  # 特殊标记，提取文本
                                    text_value = element.text.strip()
                                    if text_value:
                                        item_data[sub_target] = text_value
                            if item_data:
                                structured_data.append(item_data)
                        if structured_data:
                            entity_data[target] = structured_data
                    else:
                        # 没有子属性，提取所有属性
                        structured_data = []
                        for element in elements:
                            if element.attrs:
                                # 提取所有属性
                                structured_data.append(element.attrs)
                            elif element.text.strip():
                                # 如果有文本内容
                                structured_data.append(element.text.strip())
                        if structured_data:
                            entity_data[target] = structured_data
            else:
                element = root.find(tag)
                if element:
                    if sub_attrs:
                        item_data = {}
                        for sub_rule in sub_attrs:
                            sub_tag = sub_rule.tag
                            sub_target = sub_rule.to
                            if sub_tag.startswith("@"):
                                attr = sub_tag[1:]
                                value = element.get(attr)
                                if value is not None:
                                    item_data[sub_target] = value
                            elif sub_tag.startswith("#"):  # 特殊标记，提取文本
                                text_value = element.text.strip()
                                if text_value:
                                    item_data[sub_target] = text_value
                        if item_data:
                            entity_data[target] = item_data
                    else:
                        if element.attrs:
                            # 提取所有属性
                            entity_data[target] = element.attrs
                        elif element.text.strip():
                            # 提取文本
                            entity_data[target] = element.text.strip()

    return entity_data


def load_base_entity(base_file: str, config: Config, entity_type: str, cache: Dict) -> Optional[Dict[str, Any]]:
    if base_file in cache:
        return cache[base_file]

    for package_dir in config.package_path:
        base_path = os.path.join(package_dir, base_file)
        if os.path.exists(base_path):
            with open(base_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'xml')

            for entity_group in config.entities:
                if entity_type in entity_group:
                    rules = entity_group[entity_type]
                    base_root = soup.find(entity_type)
                    if base_root:
                        base_entity = parse_entity(
                            base_root, rules, entity_type)
                        cache[base_file] = base_entity
                        return base_entity
            break

    return None
