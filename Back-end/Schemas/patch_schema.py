from pydantic import BaseModel
from typing import Optional

class PatchCreate(BaseModel):
    name: str
    description: Optional[str] = None
    file_name: str
    client_id: int
    environment_id: int
    server_id: Optional[int] = None
    patch_type: str
    component: str
    duplication_count: int
    status: str = "PENDING"
    user_id: int