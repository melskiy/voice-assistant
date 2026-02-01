"""
Views package for Gateway Service API.
Provides modular viewsets for different API resources.
"""

from .base import BaseViewSet, ViewRegistry, viewset
from .health_views import HealthViewSet
from .session_views import SessionViewSet
from .audio_views import AudioViewSet
from .freeswitch_views import FreeSwitchViewSet
from .shopping_views import ShoppingViewSet
from .reminder_views import ReminderViewSet

__all__ = [
    # Base classes
    "BaseViewSet",
    "ViewRegistry",
    "viewset",
    # ViewSets
    "HealthViewSet",
    "SessionViewSet",
    "AudioViewSet",
    "FreeSwitchViewSet",
    "ShoppingViewSet",
    "ReminderViewSet",
]