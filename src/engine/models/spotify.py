from typing import List, Optional
from pydantic import BaseModel


class SpotifyCredit(BaseModel):
    name: str
    role: str
    identity_id: Optional[int] = None


class SpotifyParseRequest(BaseModel):
    raw_text: str
    reference_title: str


class SpotifyParseResult(BaseModel):
    parsed_title: str
    title_match: bool
    credits: List[SpotifyCredit]
    publishers: List[str]


class SpotifyImportRequest(BaseModel):
    song_id: int
    credits: List[SpotifyCredit]
    publishers: List[str]
