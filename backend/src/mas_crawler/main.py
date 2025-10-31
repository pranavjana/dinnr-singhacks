"""Main entry point for FastAPI development server.

Run with: python -m mas_crawler.main or python main.py
"""

import argparse
import logging
import sys

import uvicorn

from .api import create_app
from .config import Config
from .logger import setup_logging


def main():
    """Run FastAPI development server."""
    parser = argparse.ArgumentParser(
        description="Run MAS Crawler FastAPI server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Run on default localhost:8000
  python main.py --host 0.0.0.0 --port 8080  # Run on 0.0.0.0:8080
  python main.py --reload                # Run with auto-reload on code changes
        """,
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code changes (development mode)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Logging level (default: info)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)",
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = Config.from_env()
        config.log_level = args.log_level.upper()
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Create app
    try:
        app = create_app(config)
    except Exception as e:
        print(f"Error creating FastAPI app: {e}", file=sys.stderr)
        sys.exit(1)

    # Print startup information
    protocol = "http"
    print(f"\nStarting MAS Crawler API server")
    print(f"Listening on: {protocol}://{args.host}:{args.port}")
    print(f"API Documentation: {protocol}://{args.host}:{args.port}/docs")
    print(f"Alternative docs: {protocol}://{args.host}:{args.port}/redoc")
    print(f"Log level: {args.log_level}")
    print(f"Reload: {'enabled' if args.reload else 'disabled'}")
    print()

    # Run server
    try:
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level=args.log_level,
            reload=args.reload,
            workers=args.workers if not args.reload else 1,
        )
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
