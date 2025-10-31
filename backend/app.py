"""FastAPI app entry point in project root.

This file can be used directly with uvicorn:
  uvicorn app:app --reload
  uvicorn app:app --host 0.0.0.0 --port 8000
"""

from src.mas_crawler.api import create_app
from src.mas_crawler.config import Config

# Create app with configuration from environment
config = Config.from_env()
app = create_app(config)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level=config.log_level.lower(),
    )
