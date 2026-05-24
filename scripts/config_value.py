from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from portfolio.config import get_config_value


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts\\config_value.py server.port")
    print(get_config_value(sys.argv[1]))


if __name__ == "__main__":
    main()

