import sys
import asyncio
from src.cli.colors import CLR_RED, CLR_RESET, CLR_CYAN
from src.cli.commands.create_user import CreateUserCommand
from src.cli.commands.seed import SeedCommand

COMMANDS = {
    "create-user": CreateUserCommand(),
    "seed": SeedCommand(),
}


def print_help():
    print(f"{CLR_CYAN}Available commands:{CLR_RESET}")
    for name, cmd in COMMANDS.items():
        print(f"  {name:<15} - {cmd.description}")


async def main():
    if len(sys.argv) < 2:
        print(f"{CLR_RED}Error: Command not specified.{CLR_RESET}\n")
        print_help()
        sys.exit(1)

    cmd_name = sys.argv[1]
    if cmd_name not in COMMANDS:
        print(f"{CLR_RED}Error: Unknown command '{cmd_name}'.{CLR_RESET}\n")
        print_help()
        sys.exit(1)

    cmd = COMMANDS[cmd_name]
    await cmd.execute(sys.argv[2:])


if __name__ == "__main__":
    asyncio.run(main())
