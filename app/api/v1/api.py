from fastapi import APIRouter

from app.api.v1.endpoints import games, users, catan

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(games.router, prefix="/games", tags=["games"])
api_router.include_router(catan.router, prefix="/catan", tags=["catan"])

