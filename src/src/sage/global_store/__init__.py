"""Global cross-project intelligence database."""

from .database import GlobalDatabase
from .sync import sync_patterns

__all__ = ["GlobalDatabase", "sync_patterns"]
