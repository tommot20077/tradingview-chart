"""Providers package for asset_core.

This package defines the abstract interface for data providers, which are
responsible for fetching and streaming financial market data from various
sources. Concrete implementations of data providers should adhere to this
interface.
"""

from .base import AbstractDataProvider

__all__ = ["AbstractDataProvider"]
