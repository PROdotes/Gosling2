"""
Core registries for centralized data access.

This package contains read-only registries that load configuration
and mapping data from JSON files.
"""

from .id3_registry import ID3Registry

__all__ = ['ID3Registry']
