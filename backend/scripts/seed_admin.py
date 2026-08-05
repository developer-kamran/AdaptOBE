import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.user import UserRole  # noqa: E402
from app.schemas.user import UserCreate  # noqa: E402
from app.services import auth_service  # noqa: E402
from app.services.exceptions import ConflictError  # noqa: E402


async def seed_admin(email: str, password: str, full_name: str) -> None:
    async with AsyncSessionLocal() as db:
        data = UserCreate(email=email, password=password, full_name=full_name, role=UserRole.admin)
        try:
            user = await auth_service.register_user(db, data)
        except ConflictError as exc:
            print(f"Skipped: {exc}")
            return
        print(f"Created admin user: {user.email} (id={user.id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap the first admin user for AdaptOBE.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", required=True, dest="full_name")
    args = parser.parse_args()

    asyncio.run(seed_admin(args.email, args.password, args.full_name))


if __name__ == "__main__":
    main()
