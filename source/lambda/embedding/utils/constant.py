"""
Constant used in Glue job
"""

from enum import Enum, unique


@unique
class SplittingType(Enum):
    BEFORE = "before-splitting"
    SEMANTIC = "semantic-splitting"
    CHUNK = "chunk-size-splitting"
