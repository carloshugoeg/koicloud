from app.modules.ponds.console_role import (
    CONSOLE_ROLE,
    console_role_password,
    ensure_console_role,
)
from app.modules.ponds.service import PondService

__all__ = [
    "CONSOLE_ROLE",
    "PondService",
    "console_role_password",
    "ensure_console_role",
]
