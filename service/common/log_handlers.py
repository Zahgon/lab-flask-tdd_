######################################################################
# Copyright 2016, 2022 John J. Rofrano. All Rights Reserved.
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
######################################################################

"""
Log Handlers

This module contains utility functions to set up logging
consistently
"""
import logging


def init_logging(app_logger: logging.Logger, logger_name: str):
    """Set up logging for production"""
    app_logger.propagate = False
    server_logger = logging.getLogger(logger_name)
    if server_logger.handlers:
        app_logger.handlers = server_logger.handlers
        app_logger.setLevel(server_logger.level)
    else:  # pragma: no cover
        handler = logging.StreamHandler()
        app_logger.handlers = [handler]
        app_logger.setLevel(logging.INFO)
    # Make all log formats consistent
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s", "%Y-%m-%d %H:%M:%S %z")
    for handler in app_logger.handlers:
        handler.setFormatter(formatter)
    app_logger.info("Logging handler established")
