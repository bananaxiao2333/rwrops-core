from bs4 import BeautifulSoup, Tag
import os
import logging
from typing import Dict, List, Any, Optional
from .classes import Config, Temp, TransformType, EntityConfig


def parse_file(content: BeautifulSoup, config: Config, temp: Temp) -> Temp:
    """Parse XML content according to configuration and extract structured data."""
    cache = {}
    logger = logging.getLogger(config.CONFIGFILE)

    # Process each entity type defined in the config
    for entity_name, entity_config in config.entities.items():
        # Handle both dictionary and EntityConfig objects
        if isinstance(entity_config, dict):
            # Convert dictionary to EntityConfig object
            entity_config_obj = EntityConfig.from_dict(entity_config)
        else:
            entity_config_obj = entity_config
        
        # Find all root elements matching the selector
        root_elements = content.find_all(entity_config_obj.selector)
        
        for root_element in root_elements:
            # Parse the entity with its configuration
            entity_data, root_level_attrs = parse_entity(root_element, entity_config_obj, config, cache)
            
            # Merge root-level flattened attributes
            for key, value in root_level_attrs.items():
                entity_data[key] = value
            
            # Handle inheritance if enabled
            if config.defaults.get('inherit_enabled', False):
                # Look for the inherit_from field (which comes from @file attribute)
                if "inherit_from" in entity_data:
                    base_file = entity_data["inherit_from"]
                    base_entity = load_base_entity(base_file, config, entity_config_obj.selector, cache)
                    if base_entity:
                        # Merge base entity data (only for keys not already present)
                        for key, value in base_entity.items():
                            if key not in entity_data:
                                entity_data[key] = value
                    else:
                        # Log warning when inherit_from file is not found
                        logger.warning(f"inherit_from file '{base_file}' not found for {entity_name} entity")
            
            # Add type information
            entity_data["type"] = entity_name
            temp.final.append(entity_data)

    return temp


def parse_entity(element: Tag, entity_config: EntityConfig, config: Config, cache: Dict) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Parse a single XML element according to entity configuration.
    Returns: (entity_data, root_level_attrs) where root_level_attrs contains attributes marked for root level"""
    entity_data = {}
    root_level_attrs = {}
    
    # Process attributes
    for attr_mapping in entity_config.attributes:
        source = attr_mapping.source
        target = attr_mapping.target
        transform = attr_mapping.transform
        flatten_to_root = attr_mapping.flatten_to_root
        
        if source.startswith("@"):
            # Attribute extraction (e.g., "@name" -> element.get("name"))
            attr_name = source[1:]
            value = element.get(attr_name)
            if value is not None:
                # Convert to string to handle various attribute value types
                str_value = str(value) if value is not None else ""
                processed_value = apply_transform(str_value, transform)
                if flatten_to_root:
                    root_level_attrs[target] = processed_value
                else:
                    entity_data[target] = processed_value
        elif source == "#text":
            # Text content extraction
            text_value = element.get_text(strip=True)
            if text_value:
                processed_value = apply_transform(text_value, transform)
                if flatten_to_root:
                    root_level_attrs[target] = processed_value
                else:
                    entity_data[target] = processed_value
    
    # Process children
    for child_name, child_config in entity_config.children.items():
        child_elements = element.find_all(child_config.selector)
        
        if child_config.is_array:
            # Multiple children - create array
            child_data_list = []
            for child_element in child_elements:
                child_data, child_root_attrs = parse_entity(child_element, child_config, config, cache)
                # Merge child's root-level attributes into current root_level_attrs
                for key, value in child_root_attrs.items():
                    root_level_attrs[key] = value
                if child_data:  # Only add non-empty children
                    child_data_list.append(child_data)
            if child_data_list:
                entity_data[child_config.name] = child_data_list
        else:
            # Single child - take first match
            if child_elements:
                child_data, child_root_attrs = parse_entity(child_elements[0], child_config, config, cache)
                # Merge child's root-level attributes into current root_level_attrs
                for key, value in child_root_attrs.items():
                    root_level_attrs[key] = value
                if child_data:
                    entity_data[child_config.name] = child_data
    
    return entity_data, root_level_attrs


def apply_transform(value: str, transform: Optional[TransformType]) -> Any:
    """Apply transformation to a value based on transform type."""
    if transform is None:
        return value
    
    try:
        if transform == TransformType.TO_FLOAT:
            return float(value)
        elif transform == TransformType.TO_INT:
            return int(value)
        elif transform == TransformType.TO_BOOL:
            # Handle various boolean representations
            return value.lower() in ('true', '1', 'yes', 'on')
        elif transform == TransformType.PARSE_VECTOR3:
            # Parse "x y z" format to [x, y, z]
            parts = value.strip().split()
            if len(parts) == 3:
                return [float(part) for part in parts]
            else:
                return value  # Return original if format doesn't match
        elif transform == TransformType.PARSE_VECTOR2:
            # Parse "x y" format to [x, y]
            parts = value.strip().split()
            if len(parts) == 2:
                return [float(part) for part in parts]
            else:
                return value  # Return original if format doesn't match
    except (ValueError, AttributeError):
        # If transformation fails, return original value
        return value
    
    return value


def load_base_entity(base_file: str, config: Config, entity_selector: str, cache: Dict) -> Optional[Dict[str, Any]]:
    """Load and parse a base entity from file for inheritance."""
    if base_file in cache:
        return cache[base_file]

    for package_dir in config.package_path:
        base_path = os.path.join(package_dir, base_file)
        if os.path.exists(base_path):
            try:
                with open(base_path, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), 'xml')
                
                # Find the entity configuration that matches this selector
                for entity_name, entity_config in config.entities.items():
                    # Handle both dictionary and EntityConfig objects
                    if isinstance(entity_config, dict):
                        current_selector = entity_config.get('selector', '')
                    else:
                        current_selector = entity_config.selector
                    
                    if current_selector == entity_selector:
                        base_root = soup.find(entity_selector)
                        if base_root:
                            # Use the same conversion logic as in parse_file
                            if isinstance(entity_config, dict):
                                entity_config_obj = EntityConfig.from_dict(entity_config)
                            else:
                                entity_config_obj = entity_config
                            
                            base_entity, _ = parse_entity(base_root, entity_config_obj, config, cache)
                            cache[base_file] = base_entity
                            return base_entity
            except Exception:
                # If file can't be read or parsed, continue to next package path
                continue
    
    # File not found in any package path
    cache[base_file] = None
    return None