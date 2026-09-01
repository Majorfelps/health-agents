"""
router.py — agrega todos os routers v1.
"""
from fastapi import APIRouter
from app.api.v1 import chat, meals, workouts, plans, checkins, dashboard

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(chat.router)
api_router.include_router(meals.router)
api_router.include_router(workouts.router)
api_router.include_router(plans.router)
api_router.include_router(checkins.router)
api_router.include_router(dashboard.router)
