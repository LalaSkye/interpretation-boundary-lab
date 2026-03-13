"""SignalEnvelope — raw input schema for the interpretation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SignalEnvelope:
    """Raw signal intake. Stage 1 of the interpretation pipeline.

    Attributes:
        source_id: Unique identifier for the signal source.
        timestamp: ISO-8601 timestamp of signal capture.
        content: Raw signal content (text, data, etc.).
        content_type: MIME-like type descriptor.
        provenance_hash: Hash proving signal provenance chain.
    """

    source_id: str
    timestamp: str
    content: str
    content_type: str
    provenance_hash: str

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "timestamp": self.timestamp,
            "content": self.content,
            "content_type": self.content_type,
            "provenance_hash": self.provenance_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SignalEnvelope:
        return cls(
            source_id=data["source_id"],
            timestamp=data["timestamp"],
            content=data["content"],
            content_type=data["content_type"],
            provenance_hash=data.get("provenance_hash", ""),
        )
