import argparse
import asyncio
import sys
from pathlib import Path

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.models.user import UserRole  # noqa: E402
from app.schemas.user import UserCreate  # noqa: E402
from app.services import auth_service  # noqa: E402
from app.services.exceptions import ConflictError  # noqa: E402

# DEBUG=true builds the engine with echo=True, which would bury this script's
# output in SQL. Echo ignores logger levels, so switch it off directly.
engine.echo = False


async def seed_admin(email: str, password: str, full_name: str) -> int:
    """Returns a process exit code: 0 on success or benign skip, 1 on bad input."""
    try:
        data = UserCreate(email=email, password=password, full_name=full_name, role=UserRole.admin)
    except ValidationError as exc:
        # A raw pydantic traceback is poor UX for a command people run by hand.
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"])
            print(f"Invalid --{field.replace('_', '-')}: {error['msg']}", file=sys.stderr)
        return 1

    async with AsyncSessionLocal() as db:
        try:
            user = await auth_service.register_user(db, data)
        except ConflictError as exc:
            print(f"Skipped: {exc}")
            return 0
        print(f"Created admin user: {user.email} (id={user.id})")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap the first admin user for AdaptOBE.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", required=True, dest="full_name")
    args = parser.parse_args()

    raise SystemExit(asyncio.run(seed_admin(args.email, args.password, args.full_name)))


if __name__ == "__main__":
    main()
