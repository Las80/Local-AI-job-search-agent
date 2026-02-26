"""
Notifications package for the Local AI Job Search Agent.
Exposes Telegram instant alert and daily digest sending.
"""

from notifications.telegram import send_instant_alert, send_digest

__all__ = ["send_instant_alert", "send_digest"]
