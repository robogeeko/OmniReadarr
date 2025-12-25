from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QueueItem:
    nzo_id: str
    filename: str
    status: str
    mbleft: float
    mb: float
    timeleft: str
    percentage: float

    @classmethod
    def from_dict(cls, data: dict) -> QueueItem:
        return cls(
            nzo_id=data["nzo_id"],
            filename=data.get("filename", ""),
            status=data.get("status", ""),
            mbleft=float(data.get("mbleft", 0)),
            mb=float(data.get("mb", 0)),
            timeleft=data.get("timeleft", ""),
            percentage=float(data.get("percentage", 0)),
        )


@dataclass
class HistoryItem:
    nzo_id: str
    name: str
    status: str
    size: float
    category: str
    storage: str
    path: str
    completed: str

    @classmethod
    def from_dict(cls, data: dict) -> HistoryItem:
        return cls(
            nzo_id=data.get("nzo_id", ""),
            name=data.get("name", ""),
            status=data.get("status", ""),
            size=float(data.get("size", 0)),
            category=data.get("category", ""),
            storage=data.get("storage", ""),
            path=data.get("path", ""),
            completed=data.get("completed", ""),
        )


@dataclass
class JobStatus:
    nzo_id: str
    filename: str
    status: str
    progress: float
    mbleft: float
    mb: float
    timeleft: str
    path: str | None = None

    @classmethod
    def from_queue_item(cls, item: QueueItem) -> JobStatus:
        return cls(
            nzo_id=item.nzo_id,
            filename=item.filename,
            status=item.status,
            progress=item.percentage,
            mbleft=item.mbleft,
            mb=item.mb,
            timeleft=item.timeleft,
        )

    @classmethod
    def from_history_item(cls, item: HistoryItem) -> JobStatus:
        return cls(
            nzo_id=item.nzo_id,
            filename=item.name,
            status=item.status,
            progress=100.0 if item.status == "Completed" else 0.0,
            mbleft=0.0,
            mb=item.size,
            timeleft="",
            path=item.path,
        )
