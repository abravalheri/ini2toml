from configparser import ConfigParser
from typing import Mapping

from ..types import EMPTY, IntermediateRepr


def parse(text: str, opts: Mapping = EMPTY) -> IntermediateRepr:
    cfg = ConfigParser(**opts)
    cfg.read_string(text)
    irepr = IntermediateRepr()
    for name, section in cfg.items():
        if name == "DEFAULT":
            continue
        irepr.append(name, translate_section(section))
    return irepr


def translate_section(section: Mapping):
    irepr = IntermediateRepr()
    for name, value in section.items():
        irepr.append(name, value)
    return irepr
