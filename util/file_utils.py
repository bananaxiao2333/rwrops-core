import logging
import os
from pathlib import Path
import chardet
from bs4 import BeautifulSoup
from tqdm import tqdm

logger = logging.getLogger("File")


def file_reader(path: Path, size: int = -1) -> str:
    with open(path, 'rb') as file:
        r = file.read(size)
        f_charinfo = chardet.detect(r)
        encoding = f_charinfo['encoding']
    # logger.debug(f"reading '{path}' in '{encoding}'")
    with open(path, 'r', encoding=encoding, errors="ignore") as file:
        return file.read(size)


def xml_parser_factory(content: str) -> BeautifulSoup:
    soup = BeautifulSoup(content, "xml")
    return soup


def walk_dir(path: Path):
    total = 0
    for root, dirs, files in os.walk(path, topdown=True):
        total += len(files)

    with tqdm(range(total), desc='walk progress') as tbar:
        for root, dirs, files in os.walk(path, topdown=True):
            for file in files:
                yield Path(os.path.join(root, file))
                tbar.set_description_str(root.replace(str(path), ""))
                tbar.update()
