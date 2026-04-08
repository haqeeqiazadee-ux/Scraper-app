"""Abstract base for vendor-specific ingest adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence

from sqlalchemy.orm import Session

from core.matcher import ProductMatcher, VendorProductInput


class BaseVendorAdapter(ABC):
    """Load vendor-specific rows, then bulk persist via :class:`~core.matcher.ProductMatcher`."""

    @abstractmethod
    def vendor_name(self) -> str:
        """Stable label stored on ``vendor_offers.vendor_name``."""

    @abstractmethod
    def load_items(self) -> Sequence[VendorProductInput | Mapping[str, Any]]:
        """Return rows consumable by :meth:`ProductMatcher.ingest_vendor_catalog`."""

    def ingest(self, session: Session, *, chunk_size: int = 500) -> int:
        matcher = ProductMatcher(session)
        return matcher.ingest_vendor_catalog(
            self.vendor_name(),
            self.load_items(),
            chunk_size=chunk_size,
        )
