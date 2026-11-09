from dataclasses import dataclass

from fastapi import Header, HTTPException

from app.core.config import settings

DEV_GROUPS = ["tax", "banking", "finance", "compliance"]


@dataclass
class User:
    user_id: str
    groups: list[str]


def current_user(
    x_api_key: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_groups: str | None = Header(default=None),
) -> User:
    if settings.auth_mode == "apikey":
        entry = settings.api_keys.get(x_api_key or "")
        if not entry:
            raise HTTPException(status_code=401, detail="Missing or invalid API key")
        return User(user_id=entry["user_id"], groups=list(entry.get("groups", [])))

    if x_user_groups is None:
        groups = DEV_GROUPS
    else:
        groups = [g.strip() for g in x_user_groups.split(",") if g.strip()]
    return User(user_id=x_user_id or "dev-user", groups=groups)