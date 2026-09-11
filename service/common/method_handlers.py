# Copyright 2016, 2026 John J. Rofrano. All Rights Reserved.
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
Module: method_handlers

Restores the HTTP methods that Werkzeug answered automatically. Flask served
HEAD on every GET rule and OPTIONS on every matched URL; FastAPI's APIRoute
does neither, so both are added back here to keep the service's method
surface unchanged.
"""
import re

from fastapi import FastAPI, Response
from starlette.responses import HTMLResponse
from starlette.routing import Match

DUPLICATE_SLASHES = re.compile("/{2,}")

# Werkzeug's redirect page, reproduced so the 308 body is unchanged
REDIRECT_BODY = (
    "<!doctype html>\n"
    "<html lang=en>\n"
    "<title>Redirecting...</title>\n"
    "<h1>Redirecting...</h1>\n"
    "<p>You should be redirected automatically to the target URL: "
    '<a href="{url}">{url}</a>. If not, click the link.\n'
)


def add_head_to_get_routes(app: FastAPI) -> None:
    """Serves HEAD anywhere the application serves GET"""
    for route in app.routes:
        methods = getattr(route, "methods", None)
        if methods and "GET" in methods:
            methods.add("HEAD")


def allowed_methods(app: FastAPI, scope) -> set:
    """Returns every method registered on the URL in the given scope"""
    allowed = set()
    for route in app.routes:
        match, _ = route.matches(scope)
        if match != Match.NONE:
            allowed.update(getattr(route, "methods", None) or set())
    return allowed


def init_automatic_methods(app: FastAPI) -> None:
    """Registers the automatic HEAD and OPTIONS behavior on the application"""
    add_head_to_get_routes(app)

    @app.middleware("http")
    async def automatic_options(request, call_next):
        """Answers OPTIONS the way Flask's automatic options responses did

        Flask replied 200 with an Allow header on any URL matching a rule and
        404 on one that did not. Starlette has no such default.
        """
        if request.method == "OPTIONS":
            allowed = allowed_methods(app, request.scope)
            if allowed:
                allowed.add("OPTIONS")
                return Response(
                    status_code=200,
                    headers={
                        "Allow": ", ".join(sorted(allowed)),
                        "Content-Type": "text/html; charset=utf-8",
                    },
                )
        return await call_next(request)


def init_slash_merging(app: FastAPI) -> None:
    """Collapses duplicate slashes in a URL the way Werkzeug's router did

    Werkzeug served a path whose duplicate slashes were only leading, and
    permanently redirected one whose duplicates were interior. Starlette does
    neither and would answer 404.
    """

    @app.middleware("http")
    async def merge_duplicate_slashes(request, call_next):
        """Applies the merge before the request reaches the router"""
        path = request.scope["path"]
        if "//" not in path:
            return await call_next(request)
        merged = DUPLICATE_SLASHES.sub("/", path)
        if not allowed_methods(app, dict(request.scope, path=merged)):
            return await call_next(request)  # nothing there either way: 404
        if "//" in path.lstrip("/"):
            url = str(request.url.replace(path=merged))
            return HTMLResponse(
                REDIRECT_BODY.format(url=url),
                status_code=308,
                headers={"Location": url},
            )
        request.scope["path"] = merged
        return await call_next(request)
