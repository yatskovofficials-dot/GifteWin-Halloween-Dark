from aiogram import Router

from .start import router as start_router
from .giveaway import router as giveaway_router
from .profile import router as profile_router
from .admin import router as admin_router


def get_all_routers() -> list[Router]:
    return [
        start_router,
        giveaway_router,
        profile_router,
        admin_router,
    ]
