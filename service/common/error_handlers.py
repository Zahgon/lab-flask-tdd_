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
Module: error_handlers
"""
import json
import logging
import typing

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from service.models import DataValidationError
from . import status

logger = logging.getLogger("petstore")


class SortedJSONResponse(JSONResponse):
    """JSON response that matches the wire format Flask's jsonify() produced

    Flask sorts object keys and uses compact separators by default. Starlette
    does not sort, so the ordering is restored here to keep responses
    byte-identical with the original service.
    """

    def render(self, content: typing.Any) -> bytes:
        if content is None:
            return b""
        return (
            json.dumps(
                content,
                ensure_ascii=False,
                allow_nan=False,
                indent=None,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")


######################################################################
# Default descriptions, matching Werkzeug's built-in exception text so
# that error payloads are unchanged from the Flask implementation.
######################################################################
ERROR_NAMES = {
    status.HTTP_400_BAD_REQUEST: "Bad Request",
    status.HTTP_404_NOT_FOUND: "Not Found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Method Not Allowed",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "Unsupported Media Type",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "Internal Server Error",
}

DEFAULT_DESCRIPTIONS = {
    status.HTTP_400_BAD_REQUEST: (
        "The browser (or proxy) sent a request that this server could not "
        "understand."
    ),
    status.HTTP_404_NOT_FOUND: (
        "The requested URL was not found on the server. If you entered the URL "
        "manually please check your spelling and try again."
    ),
    status.HTTP_405_METHOD_NOT_ALLOWED: (
        "The method is not allowed for the requested URL."
    ),
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: (
        "The server does not support the media type transmitted in the request."
    ),
    status.HTTP_500_INTERNAL_SERVER_ERROR: (
        "The server encountered an internal error and was unable to complete "
        "your request. Either the server is overloaded or there is an error in "
        "the application."
    ),
}

# The "error" field of the payload, exactly as the Flask handlers spelled it
PAYLOAD_ERRORS = {
    status.HTTP_400_BAD_REQUEST: "Bad Request",
    status.HTTP_404_NOT_FOUND: "Not Found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Method not Allowed",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "Unsupported media type",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "Internal Server Error",
}


def abort(code: int, description: str = None) -> typing.NoReturn:
    """Raises an HTTP error the way Flask's abort() did

    :param code: the HTTP status code to return
    :param description: optional detail appended after the status name
    """
    raise HTTPException(
        status_code=code,
        detail=description or DEFAULT_DESCRIPTIONS.get(code, ""),
    )


def _error_payload(code: int, message: str) -> dict:
    """Builds the response body shared by every error handler"""
    return {
        "status": code,
        "error": PAYLOAD_ERRORS.get(code, ERROR_NAMES.get(code, "Error")),
        "message": message,
    }


def _flask_style_message(code: int, description: str) -> str:
    """Reproduces str(werkzeug.exceptions.HTTPException): '<code> <name>: <desc>'"""
    name = ERROR_NAMES.get(code, "Error")
    return f"{code} {name}: {description}"


######################################################################
# Error Handlers
######################################################################
def init_error_handlers(app: FastAPI) -> None:
    """Registers the error handlers on the FastAPI application"""

    @app.exception_handler(DataValidationError)
    async def request_validation_error(_request, error: DataValidationError):
        """Handles Value Errors from bad data"""
        return bad_request(error)

    def bad_request(error):
        """Handles bad requests with 400_BAD_REQUEST"""
        message = str(error)
        logger.warning(message)
        return SortedJSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_payload(status.HTTP_400_BAD_REQUEST, message),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request, error: StarletteHTTPException):
        """Handles every aborted request with the original payload shape"""
        code = error.status_code
        description = error.detail
        # Starlette's own routing failures carry terse detail text; swap in the
        # Werkzeug wording so the payload is identical to the Flask version.
        if description in (None, "", ERROR_NAMES.get(code)):
            description = DEFAULT_DESCRIPTIONS.get(code, str(description))
        message = _flask_style_message(code, description)
        if code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            logger.error(message)
        else:
            logger.warning(message)
        return SortedJSONResponse(
            status_code=code, content=_error_payload(code, message)
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(  # pragma: no cover
        _request, error: RequestValidationError
    ):
        """Bad path/query values were a routing miss in Flask, so 404 here too

        Unreachable while every path id uses the ":int" convertor, which makes
        a bad id fail to match the route at all. Kept as a safety net.
        """
        logger.warning("Request validation failed: %s", error)
        message = _flask_style_message(
            status.HTTP_404_NOT_FOUND,
            DEFAULT_DESCRIPTIONS[status.HTTP_404_NOT_FOUND],
        )
        return SortedJSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error_payload(status.HTTP_404_NOT_FOUND, message),
        )

    @app.exception_handler(Exception)
    async def internal_server_error(_request, error: Exception):
        """Handles unexpected server error with 500_SERVER_ERROR"""
        message = _flask_style_message(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            DEFAULT_DESCRIPTIONS[status.HTTP_500_INTERNAL_SERVER_ERROR],
        )
        logger.error("%s: %s", message, error)
        return SortedJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload(
                status.HTTP_500_INTERNAL_SERVER_ERROR, message
            ),
        )
