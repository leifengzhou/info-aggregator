"""Source adapter interfaces and shared adapter types."""

from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod


@dataclass
class FetchedItem:
    """Standardized content item returned by all adapters."""
    source_id: str           # Platform's unique ID
    source_type: str         # "youtube", "reddit", "rss", etc.
    url: str
    title: str
    author: str | None
    published_at: datetime
    content: str             # Full text content (transcript, post body, article)
    metadata: dict           # Adapter-specific extras (thumbnail, score, etc.)


class BaseAdapter(ABC):
    @abstractmethod
    def fetch(self, source_config: dict, since: datetime | None = None) -> list[FetchedItem]:
        """Fetch new content from the source since the given timestamp."""
        ...
