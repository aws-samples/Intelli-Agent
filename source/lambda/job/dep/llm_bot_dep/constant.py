"""
Constant used in Glue job
"""

from enum import Enum, unique


@unique
class SplittingType(Enum):
    BEFORE = "before-splitting"
    SEMANTIC = "semantic-splitting"
    CHUNK = "chunk-size-splitting"
    QA_ENHANCEMENT = "qa-enhancement"


@unique
class FigureNode(Enum):
    START = "<figure>"
    END = "</figure>"
    TYPE = "type"
    DESCRIPTION = "desp"
    VALUE = "value"

