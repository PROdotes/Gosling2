"""Identity Data Model"""
from typing import Optional
from dataclasses import dataclass


@dataclass
class Identity:
    """Represents a real person or group identity."""

    identity_id: Optional[int] = None
    identity_type: str = "person"  # 'person', 'group', or 'placeholder'
    legal_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    date_of_death: Optional[str] = None
    nationality: Optional[str] = None
    formation_date: Optional[str] = None
    disband_date: Optional[str] = None
    biography: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "identity_id": self.identity_id,
            "identity_type": self.identity_type,
            "legal_name": self.legal_name,
            "date_of_birth": self.date_of_birth,
            "date_of_death": self.date_of_death,
            "nationality": self.nationality,
            "formation_date": self.formation_date,
            "disband_date": self.disband_date,
            "biography": self.biography,
            "notes": self.notes
        }

    @classmethod
    def from_row(cls, row: tuple) -> 'Identity':
        """Create Identity from DB row."""
        if not row:
            return None
        return cls(
            identity_id=row[0],
            identity_type=row[1],
            legal_name=row[2],
            date_of_birth=row[3],
            date_of_death=row[4],
            nationality=row[5],
            formation_date=row[6],
            disband_date=row[7],
            biography=row[8],
            notes=row[9]
        )
