# Copyright 2016, 2021 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Package: service
Package for the application models and service routes
This module creates and configures the FastAPI app and sets up the logging
and SQL database
"""

import logging
import sys

from fastapi import FastAPI

from service import config
from service.common import log_handlers

logger = logging.getLogger("petstore")


############################################################
# Initialize the FastAPI instance
############################################################
def create_app() -> FastAPI:
    """Initialize the core application."""
    # Create FastAPI application
    # The interactive docs are switched off: /docs, /redoc, /openapi.json and
    # /docs/oauth2-redirect all returned 404 on the original service, and the
    # migration must not widen the URL surface.
    app = FastAPI(
        title="Pet Demo REST API Service",
        version="1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    # Werkzeug 404s on a trailing slash for routes declared without one;
    # Starlette would redirect instead, so the redirect is turned off.
    app.router.redirect_slashes = False

    # Initialize Plugins
    # pylint: disable=import-outside-toplevel
    from service.models import db

    db.init_engine(config.DATABASE_URI)

    # Dependencies require we import the routes AFTER the app is created
    # pylint: disable=wrong-import-position, wrong-import-order, unused-import
    from service import models  # noqa: F401 E402
    from service.routes import router  # noqa: F401 E402
    from service.common import error_handlers, method_handlers  # noqa: F401, E402

    app.include_router(router)
    error_handlers.init_error_handlers(app)

    method_handlers.init_automatic_methods(app)
    method_handlers.init_slash_merging(app)

    try:
        models.init_db()  # make our sqlalchemy tables
    except Exception as error:  # pylint: disable=broad-except # pragma: no cover
        logger.critical("%s: Cannot continue", error)
        # the process manager requires a non-zero exit code to stop respawning
        sys.exit(4)

    # Set up logging for production
    log_handlers.init_logging(logger, "uvicorn.error")

    logger.info("╔%s╗", (60 * "═"))
    logger.info("║%s║", "  P E T   S T O R E   S E R V I C E  ".center(60, " "))
    logger.info("╚%s╝", (60 * "═"))

    logger.info("Service initialized!")

    return app
