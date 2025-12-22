from dataclasses import dataclass
from typing import Optional

@dataclass
class Publisher:
    publisher_id: Optional[int]
    publisher_name: str
    parent_publisher_id: Optional[int] = None

    @classmethod
    def from_row(cls, row):
        return cls(
            publisher_id=row['PublisherID'],
            publisher_name=row['PublisherName'],
            parent_publisher_id=row['ParentPublisherID']
        )
