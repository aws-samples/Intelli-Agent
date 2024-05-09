from enum import Enum, unique


@unique
class EtlStatus(Enum):
    SUCCEEDED = "SUCCEED"
    FAILED = "FAILED"
    RUNNING = "RUNNING"
