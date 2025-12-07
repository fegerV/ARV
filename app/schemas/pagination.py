from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    meta: PaginationMeta