"""Storage package for asset_core.

This package defines the abstract interfaces for data storage repositories
within the `asset_core` library. It includes interfaces for storing and
retrieving Kline data (`AbstractKlineRepository`) and general metadata
(`AbstractMetadataRepository`), allowing for flexible and interchangeable
storage backend implementations.
"""

from .kline_repo import AbstractKlineRepository
from .metadata_repo import AbstractMetadataRepository

__all__ = ["AbstractKlineRepository", "AbstractMetadataRepository"]
