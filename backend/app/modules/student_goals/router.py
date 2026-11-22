"""student_goals extra router: data corrections handled in recommendations/router; periods & goals there too.

This module-level router exists to keep the module boundary explicit.
"""
from fastapi import APIRouter

goals_extra_router = APIRouter(prefix="/goals", tags=["goals"])
