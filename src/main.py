"""Entry point for the SafeSite AI platform."""
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def main():
    logging.info("SafeSite AI starting up")
    logging.info("Hello from src/main.py")


if __name__ == "__main__":
    main()
