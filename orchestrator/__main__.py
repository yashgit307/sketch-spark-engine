import argparse
import logging
import sys

from .config import Settings
from .pipeline import run_pipeline
from .trigger import run_scheduler, run_webhook


def main() -> int:
    parser = argparse.ArgumentParser(prog="bigpikle", description="Bigpikle automation pipeline")
    parser.add_argument("-v", "--verbose", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one pipeline pass now")
    run_parser.add_argument("--topic", help="Topic text (otherwise pops from the topics queue)")
    run_parser.add_argument(
        "--platform",
        default="youtube",
        help="Target platform (youtube, instagram, pinterest, all)",
    )
    run_parser.add_argument(
        "--no-publish", action="store_true", help="Skip the upload step entirely"
    )

    subparsers.add_parser("schedule", help="Run on the configured cron schedule")
    subparsers.add_parser("webhook", help="Listen for webhook trigger calls")

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = Settings.from_env()

    if args.command == "run":
        platforms = [] if args.no_publish else [p.strip() for p in args.platform.split(",")]
        result = run_pipeline(topic=args.topic, platforms=platforms, settings=settings)
        print(result)
    elif args.command == "schedule":
        run_scheduler(settings)
    elif args.command == "webhook":
        run_webhook(settings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
