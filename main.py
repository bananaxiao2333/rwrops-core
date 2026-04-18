from ast import List
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict
from bs4 import BeautifulSoup
from tqdm import tqdm
import yaml
from util import Clogger
from util.classes import Config, Temp
from util.file_utils import file_reader, walk_dir, xml_parser_factory
from util.ops import parse_file
from util.timer import timer

Clogger.init_color_logger()
logger = logging.getLogger("ROOT")


def clean_final(temp: Temp, primarykey: str) -> Temp:
    ret: Dict[str, Dict[str, Dict]] = {}

    for item in temp.final:
        type = item.get('type')
        key = item.get(primarykey)

        if key and type:
            if not ret.get(type):
                ret[type] = {}  # 如果这个类别不存在，创建一个
            ret[type][key] = item

    # 对每个类别按照primarykey排序
    sorted_ret: Dict[str, Dict[str, Dict]] = {}

    for type_name, type_data in ret.items():
        if not type_data:
            sorted_ret[type_name] = {}
            continue

        def get_sort_key(item_key: str, item_data: Dict) -> Any:
            """尝试将键转换为数字进行比较，如果不能转换则保持原样"""
            # 使用primarykey的值进行排序
            sort_value = item_data.get(primarykey, item_key)

            try:
                # 尝试转换为整数
                return int(sort_value)
            except (ValueError, TypeError):
                try:
                    # 尝试转换为浮点数
                    return float(sort_value)
                except (ValueError, TypeError):
                    # 如果都不是，保持字符串
                    return str(sort_value)

        # 按照primarykey排序
        sorted_items = sorted(
            type_data.items(),
            key=lambda x: get_sort_key(x[0], x[1])
        )

        # 创建新的字典
        sorted_ret[type_name] = {k: v for k, v in sorted_items}

    temp.sorted_final = sorted_ret
    return temp


@timer
def main_procces(config: Config):
    temp = Temp()
    Plogger = logging.getLogger(config.CONFIGFILE)

    @timer
    def scan(config: Config, temp: Temp) -> Temp:
        for package_path in config.package_path:
            Plogger.debug(f"walking in package '{package_path}'")
            for path in walk_dir(Path(package_path)):
                try:
                    data = file_reader(path, size=5)
                    if data.startswith("<"):
                        temp.conf_file.append(str(path))
                    else:
                        raise RuntimeError
                except:
                    temp.res_file.append(str(path))
                    continue
        return temp

    temp: Temp = scan(config, temp)

    Plogger.debug(
        f"configuration: {len(temp.conf_file)} resource: {len(temp.res_file)} ")
    conf_type = {}
    for item in temp.conf_file:
        conf_type[str(os.path.basename(item)).split(".")[1]] = 0
    res_type = {}
    for item in temp.res_file:
        try:
            res_type[str(os.path.basename(item)).split(".")[1]] = 0
        except:
            pass
    Plogger.debug(
        f"configuration types: {list(conf_type.keys())} ")
    Plogger.debug(
        f"resource: {list(res_type.keys())} ")

    with tqdm(range(len(temp.conf_file)), desc="Files") as pbar:
        for item in temp.conf_file:
            data: str = file_reader(Path(item))
            xml_content: BeautifulSoup = xml_parser_factory(data)
            temp = parse_file(content=xml_content, config=config, temp=temp)
            pbar.update()

    # Export all .res files to assets folder
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)

    res_files_exported = 0
    for res_file_path in temp.res_file:
        res_path = Path(res_file_path)
        # Create the same relative directory structure under assets
        relative_path = res_path.relative_to(res_path.parent.parent) if len(
            res_path.parts) > 2 else res_path.name
        destination = assets_dir / res_path.name
        # If file already exists, add a number suffix to avoid overwriting
        counter = 1
        original_destination = destination
        while destination.exists():
            destination = assets_dir / \
                f"{original_destination.stem}_{counter}{original_destination.suffix}"
            counter += 1
        try:
            destination.write_bytes(res_path.read_bytes())
            res_files_exported += 1
        except Exception as e:
            Plogger.warning(
                f"Failed to copy {res_file_path} to {destination}: {e}")

    Plogger.info(f"Exported {res_files_exported} .res files to assets folder")

    to_dump = temp.final
    if config.sort.enable:
        temp = clean_final(temp, config.sort.primarykey)
        to_dump = temp.sorted_final
    with open('result.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(to_dump, ensure_ascii=False))


if __name__ == "__main__":
    logger.info("RWROPS requested | Fidelity Bravery Integrity")
    logger.debug(f"CWD: {os.getcwd()}")
    logger.info("reading yaml files in config folder")
    configs_path = os.listdir("config")
    configs_path = [item for item in configs_path if item.endswith(".yaml")]
    logger.debug(f"awaiting config file count: {len(configs_path)}")
    for item in configs_path:
        item_path = Path(os.path.join("config", item))

        logger.debug(f"trying to read config '{item}'")
        try:
            data = yaml.load(file_reader(
                item_path), Loader=yaml.FullLoader)
            config = Config(CONFIGFILE=item, **data)
        except Exception as e:
            logger.critical(
                f"error when reading config '{item}'", exc_info=e)
            continue
        logger.info(f"handling config '{item}'")
        main_procces(config)
