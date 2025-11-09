from aiogram import Router
from .handlers.start_help import router as start_help_router
from .handlers.add_wizard import router as add_router
from .handlers.list_filter import router as list_router
from .handlers.per_task import router as per_task_router

def build_router() -> Router:
    r = Router()
    r.include_router(start_help_router)
    r.include_router(add_router)
    r.include_router(list_router)
    r.include_router(per_task_router)
    return r
