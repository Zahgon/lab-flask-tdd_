# Copyright 2016, 2024 John Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Models for Pet Demo Service

All of the models are stored in this module

Models
------
Pet - A Pet used in the Pet Store

Attributes:
-----------
name (string) - the name of the pet
category (string) - the category the pet belongs to (i.e., dog, cat)
available (boolean) - True for pets that are available for adoption
gender (enum) - the gender of the pet
birthday (date) - the day the pet was born

"""

import os
import logging
from datetime import date
from enum import Enum
from retry import retry
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    String,
    create_engine,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

# global variables for retry (must be int)
RETRY_COUNT = int(os.environ.get("RETRY_COUNT", 5))
RETRY_DELAY = int(os.environ.get("RETRY_DELAY", 1))
RETRY_BACKOFF = int(os.environ.get("RETRY_BACKOFF", 2))

logger = logging.getLogger("petstore")

Base = declarative_base()


class _Database:
    """Minimal SQLAlchemy holder that replaces the Flask-SQLAlchemy extension

    Flask-SQLAlchemy bound a session to the Flask application context. FastAPI
    has no such context, so a thread-local `scoped_session` is used instead and
    removed at the end of every request (see service/__init__.py).
    """

    def __init__(self):
        self.engine = None
        self.session = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, future=True)
        )

    def init_engine(self, database_uri: str) -> None:
        """Creates the engine and binds the session factory to it"""
        connect_args = {}
        if database_uri.startswith("sqlite"):
            # SQLite defaults to a single-thread guard that breaks under ASGI
            connect_args["check_same_thread"] = False
        self.engine = create_engine(
            database_uri, future=True, connect_args=connect_args
        )
        self.session.remove()
        self.session.configure(bind=self.engine)

    def create_all(self) -> None:
        """Creates all of the tables"""
        Base.metadata.create_all(self.engine)

    def drop_all(self) -> None:
        """Drops all of the tables"""
        Base.metadata.drop_all(self.engine)


# Create the database object to be initialized later in init_engine()
db = _Database()


@retry(
    Exception,
    delay=RETRY_DELAY,
    backoff=RETRY_BACKOFF,
    tries=RETRY_COUNT,
    logger=logger,
)
def init_db() -> None:
    """Initialize Tables"""
    db.create_all()


class DataValidationError(Exception):
    """Used for an data validation errors when deserializing"""


class Gender(Enum):
    """Enumeration of valid Pet Genders"""

    MALE = 0
    FEMALE = 1
    UNKNOWN = 3


class Pet(Base):
    """
    Class that represents a Pet

    This version uses a relational database for persistence which is hidden
    from us by SQLAlchemy's object relational mappings (ORM)
    """

    __tablename__ = "pet"

    ##################################################
    # Table Schema
    ##################################################
    id = Column(Integer, primary_key=True)
    name = Column(String(63), nullable=False)
    category = Column(String(63), nullable=False)
    available = Column(Boolean(), nullable=False, default=False)
    gender = Column(
        SAEnum(Gender), nullable=False, server_default=(Gender.UNKNOWN.name)
    )
    birthday = Column(Date(), nullable=False, default=date.today())
    # Database auditing fields
    # pylint: disable=not-callable
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_updated = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    # pylint: enable=not-callable

    ##################################################
    # INSTANCE METHODS
    ##################################################

    def __repr__(self):
        return f"<Pet {self.name} id=[{self.id}]>"

    def create(self) -> None:
        """
        Saves a Pet to the database
        """
        logger.info("Creating %s", self.name)
        # id must be none to generate next primary key
        self.id = None  # pylint: disable=invalid-name
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error creating record: %s", self)
            raise DataValidationError(e) from e

    def update(self) -> None:
        """
        Updates a Pet to the database
        """
        logger.info("Saving %s", self.name)
        if not self.id:
            raise DataValidationError("Update called with empty ID field")
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error updating record: %s", self)
            raise DataValidationError(e) from e

    def delete(self) -> None:
        """
        Removes a Pet from the database
        """
        logger.info("Deleting %s", self.name)
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error deleting record: %s", self)
            raise DataValidationError(e) from e

    def serialize(self) -> dict:
        """Serializes a Pet into a dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "available": self.available,
            "gender": self.gender.name,  # convert enum to string
            "birthday": self.birthday.isoformat(),
        }

    def deserialize(self, data: dict):
        """
        Deserializes a Pet from a dictionary
        Args:
            data (dict): A dictionary containing the Pet data
        """
        try:
            self.name = data["name"]
            self.category = data["category"]
            if isinstance(data["available"], bool):
                self.available = data["available"]
            else:
                raise DataValidationError(
                    "Invalid type for boolean [available]: "
                    + str(type(data["available"]))
                )
            # self.gender = getattr(Gender, data["gender"])  # create enum from string
            self.gender = Gender[data["gender"].upper()]  # create enum from string
            self.birthday = date.fromisoformat(data["birthday"])
        except AttributeError as error:
            raise DataValidationError("Invalid attribute: " + error.args[0]) from error
        except KeyError as error:
            raise DataValidationError(
                "Invalid pet: missing " + error.args[0]
            ) from error
        except TypeError as error:
            raise DataValidationError(
                "Invalid pet: body of request contained bad or no data " + str(error)
            ) from error
        return self

    ##################################################
    # CLASS METHODS
    ##################################################

    @classmethod
    def all(cls) -> list:
        """Returns all of the Pets in the database"""
        logger.info("Processing all Pets")
        return db.session.query(cls).all()

    @classmethod
    def find(cls, pet_id: int):
        """Finds a Pet by it's ID

        :param pet_id: the id of the Pet to find
        :type pet_id: int

        :return: an instance with the pet_id, or None if not found
        :rtype: Pet

        """
        logger.info("Processing lookup for id %s ...", pet_id)
        return db.session.get(cls, pet_id)
