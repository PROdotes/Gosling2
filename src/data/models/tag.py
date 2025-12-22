from dataclasses import dataclass
from typing import Optional

@dataclass
class Tag:
    tag_id: Optional[int]
    tag_name: str
    category: Optional[str] = None
    
    @classmethod
    def from_row(cls, row):
        return cls(
            tag_id=row['TagID'],
            tag_name=row['TagName'],
            category=row['Category']
        )
