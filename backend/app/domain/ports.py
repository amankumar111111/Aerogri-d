"""Domain ports — interfaces for infrastructure adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from app.domain.entities import (
    AuditEvent,
    Interpretation,
    Media,
    Notification,
    Observation,
    PolicyVersion,
    ProviderRecord,
    Signal,
    SignalEvent,
)


class ObservationStore(ABC):
    @abstractmethod
    async def save(self, observation: Observation) -> None: ...

    @abstractmethod
    async def get(self, observation_id: str) -> Observation | None: ...

    @abstractmethod
    async def list_(self, *, offset: int = 0, limit: int = 20) -> list[Observation]: ...

    @abstractmethod
    async def count(self) -> int: ...


class InterpretationStore(ABC):
    @abstractmethod
    async def save(self, interpretation: Interpretation) -> None: ...

    @abstractmethod
    async def get_by_observation(self, observation_id: str) -> Interpretation | None: ...


class SignalStore(ABC):
    @abstractmethod
    async def save(self, signal: Signal) -> None: ...

    @abstractmethod
    async def get(self, signal_id: str) -> Signal | None: ...

    @abstractmethod
    async def list_(
        self, *, state: str | None = None, offset: int = 0, limit: int = 20
    ) -> list[Signal]: ...

    @abstractmethod
    async def count(self, *, state: str | None = None) -> int: ...


class SignalEventStore(ABC):
    @abstractmethod
    async def save(self, event: SignalEvent) -> None: ...

    @abstractmethod
    async def list_by_signal(self, signal_id: str) -> list[SignalEvent]: ...

    @abstractmethod
    async def next_sequence(self, signal_id: str) -> int: ...


class AuditLog(ABC):
    @abstractmethod
    async def append(self, event: AuditEvent) -> None: ...

    @abstractmethod
    async def list_by_signal(self, signal_id: str) -> list[AuditEvent]: ...


class MediaStore(ABC):
    @abstractmethod
    async def save(self, media: Media, content: bytes) -> str: ...

    @abstractmethod
    async def get(self, media_id: str) -> bytes | None: ...


class ProviderRecordStore(ABC):
    @abstractmethod
    async def save(self, record: ProviderRecord) -> None: ...

    @abstractmethod
    async def get_latest(self, provider_type: str) -> ProviderRecord | None: ...


class EventBus(ABC):
    @abstractmethod
    async def publish(self, event_type: str, payload: dict) -> None: ...

    @abstractmethod
    async def subscribe(self, event_type: str) -> AsyncIterator[dict]: ...


class ObservationInterpreter(ABC):
    @abstractmethod
    async def interpret(
        self,
        image_bytes: bytes | None,
        voice_bytes: bytes | None,
        text: str,
        citizen_category: str,
    ) -> dict: ...


class DataProvider(ABC):
    @abstractmethod
    async def fetch(
        self, *, latitude: float, longitude: float, time_range: str | None = None
    ) -> ProviderRecord: ...

    @abstractmethod
    async def health_check(self) -> dict: ...


class NotificationService(ABC):
    @abstractmethod
    async def send(self, notification: Notification) -> None: ...


class RateLimiter(ABC):
    @abstractmethod
    async def check(self, key: str, limit: int, window_seconds: int) -> bool: ...


class IdempotencyStore(ABC):
    @abstractmethod
    async def check_and_set(self, key: str, response: str, ttl_seconds: int = 300) -> str | None: ...
