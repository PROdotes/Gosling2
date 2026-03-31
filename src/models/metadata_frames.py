from typing import Dict, Optional, Union
from pydantic import BaseModel


class ID3FrameConfig(BaseModel):
    """
    Formal domain model for an ID3 frame definition.
    Used for both tag extraction (field/type) and UI presentation (icon/color).
    """

    description: Optional[str] = None
    field: Optional[str] = None
    type: str = "text"
    tag_category: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    internal_only: bool = False


# Root config: ID -> Union[LabelString, ConfigObject]
# This mirrors the dual-format of the 'id3_frames.json' exactly.
ID3FrameMapping = Dict[str, Union[str, ID3FrameConfig]]
