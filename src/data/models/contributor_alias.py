"""Contributor Alias Data Model"""
from typing import Optional
from dataclasses import dataclass


@dataclass
class ContributorAlias:
    """Represents an alternative name for a contributor"""

    alias_id: Optional[int] = None
    contributor_id: int = 0
    alias_name: str = ""
