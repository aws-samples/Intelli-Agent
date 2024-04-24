from enum import Enum, unique


@unique
class EtlStatus(Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RUNNING = "RUNNING"
