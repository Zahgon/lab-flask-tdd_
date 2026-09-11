"""
Global Configuration for Application
"""
import os
import logging

# Get configuration from environment
DATABASE_URI = os.getenv(
    "DATABASE_URI",
    "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
)

# Secret for session management
SECRET_KEY = os.getenv("SECRET_KEY", "sup3r-s3cr3t")
LOGGING_LEVEL = logging.INFO
