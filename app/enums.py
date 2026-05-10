from enum import Enum


class OdooSyncStatus(str, Enum):
    pending = "pending"
    synced = "synced"
    failed = "failed"
