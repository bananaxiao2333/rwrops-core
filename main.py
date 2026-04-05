import logging
import mimetypes
import os
from pathlib import Path
import sys
import yaml
from util import Clogger
from util.classes import Config, Temp
from util.file_utils import file_reader, walk_dir, xml_parser_factory
from util.timer import timer

Clogger.init_color_logger()
logger = logging.getLogger("ROOT")


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
                        temp.conf_file.append(os.path.basename(path))
                    else:
                        raise RuntimeError
                except:
                    temp.res_file.append(os.path.basename(path))
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
