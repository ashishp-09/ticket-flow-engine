from src.cli.base import BaseCommand
from src.core.security.passwords import PasswordManager
from src.core.settings import get_settings
from src.modules.user.models import UserRole


class CreateUserCommand(BaseCommand):
    name = "create-user"
    description = "Create a new user with a specific role"

    def parse_args(self, args: list[str]) -> dict:
        if len(args) != 3:
            raise ValueError("Usage: python -m src.cli.entrypoint create-user <email> <password> <role>")

        email = args[0]
        password = args[1]
        role_str = args[2]

        try:
            role = UserRole(role_str)
        except ValueError:
            available_roles = ", ".join([r for r in UserRole])
            raise ValueError(f"Role '{role_str}' does not exist. Available: {available_roles}")

        return {"email": email, "password": password, "role": role}

    async def handle(self, uow, **options) -> None:
        email = options["email"]
        password = options["password"]
        role = options["role"]

        self.set_pipeline([
            ("check", "Checking user existence"),
            ("hash", "Hashing password"),
            ("create", "Saving user to database cache")
        ])

        self.start_step("check")
        existing_user = await uow.user.get(email=email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")

        self.start_step("hash")
        config = get_settings()
        pwd_manager = PasswordManager(
            algorithm=config.password_algorithm,
            iterations=config.password_iterations
        )
        hashed_password = await pwd_manager.hash_password(password)

        self.start_step("create")
        self.update_sub(f"Writing row for {email}...")
        await uow.user.create(email=email, password=hashed_password, role=role, is_active=True)
        await uow.commit()
