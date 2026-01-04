from dataclasses import dataclass
from typing import Optional

@dataclass
class Tag:
    tag_id: Optional[int]
    tag_name: str
    category: Optional[str] = None
    
    @classmethod
    def from_row(cls, row):
        # Support both tuple/index and dictionary/Row access
        if hasattr(row, 'keys'):
            # Convert keys to a set for fast lookup
            keys = set(row.keys())
            category = None
            if 'TagCategory' in keys:
                category = row['TagCategory']
            elif 'Category' in keys:
                category = row['Category']
                
            return cls(
                tag_id=row['TagID'],
                tag_name=row['TagName'],
                category=category
            )
        else:
            return cls(
                tag_id=row[0],
                tag_name=row[1],
                category=row[2] if len(row) > 2 else None
            )

    def to_dict(self):
        return {
            "tag_id": self.tag_id,
            "tag_name": self.tag_name,
            "category": self.category
        }
