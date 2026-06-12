from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db


DbSession = Depends(get_db)
