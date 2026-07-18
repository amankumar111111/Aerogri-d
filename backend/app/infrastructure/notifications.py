"""Notification Service — Production adapter.

Sends email and in-app notifications for signal escalations.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.domain.entities import Notification, Signal
from app.domain.ports import NotificationService, EventBus
from app.domain.value_objects import SignalState

logger = logging.getLogger("aerogrid.notifications")

SIGNAL_STATE_LABELS = {
    SignalState.WATCH: "Watch",
    SignalState.PROBABLE_HOTSPOT: "Probable Hotspot",
    SignalState.HIGH_CONFIDENCE: "High Confidence",
    SignalState.ARCHIVED: "Archived",
}

SIGNAL_STATE_COLORS = {
    SignalState.WATCH: "#3b82f6",
    SignalState.PROBABLE_HOTSPOT: "#f59e0b",
    SignalState.HIGH_CONFIDENCE: "#ef4444",
    SignalState.ARCHIVED: "#6b7280",
}


class EmailNotificationService(NotificationService):
    """Email notification adapter.

    In production, integrate with SendGrid, Mailgun, or Cloud Mailgun.
    For now, logs emails for verification.
    """

    def __init__(self, smtp_host: str = "", smtp_port: int = 587, smtp_user: str = "", smtp_pass: str = ""):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass

    async def send(self, notification: Notification) -> None:
        if not self.smtp_host:
            logger.info(
                f"EMAIL (dry run): to={notification.recipients} "
                f"subject={notification.subject}"
            )
            notification.sent_at = datetime.now(timezone.utc)
            return

        # In production, use aiosmtplib or SendGrid
        logger.info(
            f"EMAIL sent: to={notification.recipients} "
            f"subject={notification.subject}"
        )
        notification.sent_at = datetime.now(timezone.utc)


class InAppNotificationService:
    """In-app notifications via event bus."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    async def notify(self, notification: Notification) -> None:
        await self.event_bus.publish(
            "Notification",
            {
                "notification_id": notification.id,
                "signal_id": notification.signal_id,
                "channel": notification.channel,
                "subject": notification.subject,
                "body": notification.body,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


class NotificationOrchestrator:
    """Coordinates notifications across channels."""

    def __init__(
        self,
        email_service: EmailNotificationService,
        in_app_service: InAppNotificationService,
    ) -> None:
        self.email = email_service
        self.in_app = in_app_service

    async def on_signal_escalated(self, signal: Signal, previous_state: SignalState) -> None:
        """Send notifications when a signal escalates."""
        state_label = SIGNAL_STATE_LABELS.get(signal.state, "Unknown")
        prev_label = SIGNAL_STATE_LABELS.get(previous_state, "Unknown")

        subject = f"AEROGRID: {signal.category.replace('_', ' ').title()} — {state_label}"
        body = (
            f"Signal {signal.id[:8]}... has escalated from {prev_label} to {state_label}.\n\n"
            f"Category: {signal.category}\n"
            f"Confidence: {signal.confidence.value:.0%}\n"
            f"Observations: {len(signal.contributing_observation_ids)}\n"
            f"Location: {signal.location.latitude:.4f}, {signal.location.longitude:.4f}\n"
        )

        notification = Notification(
            signal_id=signal.id,
            channel="email",
            recipients=["municipal@aerogrid.dev"],
            subject=subject,
            body=body,
        )

        await self.email.send(notification)
        await self.in_app.notify(notification)

        logger.info(
            f"Notification sent for signal {signal.id[:8]}: "
            f"{prev_label} → {state_label}"
        )

    async def on_signal_archived(self, signal: Signal) -> None:
        """Send notification when a signal is archived."""
        notification = Notification(
            signal_id=signal.id,
            channel="email",
            recipients=["municipal@aerogrid.dev"],
            subject=f"AEROGRID: Signal {signal.id[:8]}... archived",
            body=f"Signal {signal.id[:8]}... has been archived.\nCategory: {signal.category}",
        )
        await self.email.send(notification)
