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
Pet API Service Test Suite
"""

import os
import logging
from unittest import TestCase
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

# from unittest.mock import MagicMock, patch
from asgi import app

# from service import create_app
from service.common import status
from service.models import Pet, db
from tests.factories import PetFactory

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)
BASE_URL = "/pets"


######################################################################
#  T E S T   P E T   S E R V I C E
######################################################################
class TestPetService(TestCase):
    """Pet Server Tests"""

    # pylint: disable=duplicate-code
    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        # Set up the test database
        db.init_engine(DATABASE_URI)
        db.create_all()
        logging.getLogger("petstore").setLevel(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = TestClient(app, raise_server_exceptions=False)
        db.session.query(Pet).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create pets
    ############################################################
    def _create_pets(self, count: int = 1) -> list:
        """Factory method to create pets in bulk"""
        pets = []
        for _ in range(count):
            test_pet = PetFactory()
            response = self.client.post(BASE_URL, json=test_pet.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test pet",
            )
            new_pet = response.json()
            test_pet.id = new_pet["id"]
            pets.append(test_pet)
        return pets

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should call the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["name"], "Pet Demo REST API Service")

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], 200)
        self.assertEqual(data["message"], "Healthy")

    # ----------------------------------------------------------
    # TEST LIST
    # ----------------------------------------------------------
    def test_get_pet_list(self):
        """It should Get a list of Pets"""
        self._create_pets(5)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 5)

    # ----------------------------------------------------------
    # TEST READ
    # ----------------------------------------------------------
    def test_get_pet(self):
        """It should Get a single Pet"""
        # get the id of a pet
        test_pet = self._create_pets(1)[0]
        response = self.client.get(f"{BASE_URL}/{test_pet.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["name"], test_pet.name)

    def test_get_pet_not_found(self):
        """It should not Get a Pet thats not found"""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        logging.debug("Response data = %s", data)
        self.assertIn("was not found", data["message"])

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_pet(self):
        """It should Create a new Pet"""
        test_pet = PetFactory()
        logging.debug("Test Pet: %s", test_pet.serialize())
        response = self.client.post(BASE_URL, json=test_pet.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_pet = response.json()
        self.assertEqual(new_pet["name"], test_pet.name)
        self.assertEqual(new_pet["category"], test_pet.category)
        self.assertEqual(new_pet["available"], test_pet.available)
        self.assertEqual(new_pet["gender"], test_pet.gender.name)

        # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_pet = response.json()
        self.assertEqual(new_pet["name"], test_pet.name)
        self.assertEqual(new_pet["category"], test_pet.category)
        self.assertEqual(new_pet["available"], test_pet.available)
        self.assertEqual(new_pet["gender"], test_pet.gender.name)

    # ----------------------------------------------------------
    # TEST UPDATE
    # ----------------------------------------------------------
    def test_update_pet(self):
        """It should Update an existing Pet"""
        # create a pet to update
        test_pet = PetFactory()
        response = self.client.post(BASE_URL, json=test_pet.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # update the pet
        new_pet = response.json()
        logging.debug(new_pet)
        new_pet["category"] = "unknown"
        response = self.client.put(f"{BASE_URL}/{new_pet['id']}", json=new_pet)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_pet = response.json()
        self.assertEqual(updated_pet["category"], "unknown")

    # ----------------------------------------------------------
    # TEST DELETE
    # ----------------------------------------------------------
    def test_delete_pet(self):
        """It should Delete a Pet"""
        test_pet = self._create_pets(1)[0]
        response = self.client.delete(f"{BASE_URL}/{test_pet.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response.content), 0)
        # make sure they are deleted
        response = self.client.get(f"{BASE_URL}/{test_pet.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_non_existing_pet(self):
        """It should Delete a Pet even if it doesn't exist"""
        response = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response.content), 0)


######################################################################
#  T E S T   S A D   P A T H S
######################################################################
class TestSadPaths(TestCase):
    """Test REST Exception Handling"""

    def setUp(self):
        """Runs before each test"""
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_method_not_allowed(self):
        """It should not allow update without a pet id"""
        response = self.client.put(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_pet_no_data(self):
        """It should not Create a Pet with missing data"""
        response = self.client.post(BASE_URL, json={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_pet_no_content_type(self):
        """It should not Create a Pet with no content type"""
        response = self.client.post(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_pet_wrong_content_type(self):
        """It should not Create a Pet with the wrong content type"""
        response = self.client.post(BASE_URL, content="hello", headers={"Content-Type": "text/html"})
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_pet_bad_available(self):
        """It should not Create a Pet with bad available data"""
        test_pet = PetFactory()
        logging.debug(test_pet)
        # change available to a string
        test_pet.available = "true"
        response = self.client.post(BASE_URL, json=test_pet.serialize())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_pet_bad_gender(self):
        """It should not Create a Pet with bad gender data"""
        pet = PetFactory()
        logging.debug(pet)
        # change gender to a bad string
        test_pet = pet.serialize()
        test_pet["gender"] = "XXX"  # invalid gender
        response = self.client.post(BASE_URL, json=test_pet)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    ######################################################################
    #  T E S T   M O C K S
    ######################################################################

    def test_update_pet_not_found(self):
        """It should not Update a Pet thats not found"""
        test_pet = PetFactory()
        response = self.client.put(f"{BASE_URL}/0", json=test_pet.serialize())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("was not found", response.json()["message"])

    def test_create_pet_bad_json(self):
        """It should not Create a Pet from a body that is not JSON"""
        response = self.client.post(
            BASE_URL, content="not json", headers={"Content-Type": "application/json"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_integer_pet_id(self):
        """It should not route a pet id that is not an integer"""
        response = self.client.get(f"{BASE_URL}/abc")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("was not found on the server", response.json()["message"])

    def test_negative_pet_id(self):
        """It should not route a negative pet id"""
        response = self.client.get(f"{BASE_URL}/-1")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_trailing_slash_not_found(self):
        """It should not redirect a trailing slash"""
        response = self.client.get(f"{BASE_URL}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_pet_bad_birthday(self):
        """It should report a server error for an unparsable birthday"""
        test_pet = PetFactory().serialize()
        test_pet["birthday"] = "not-a-date"
        response = self.client.post(BASE_URL, json=test_pet)
        self.assertEqual(
            response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    @patch("service.routes.Pet.find")
    def test_mock_search_data(self, pet_find_mock):
        """It should showing how to mock data"""
        pet_find_mock.return_value = MagicMock(serialize=lambda: {"name": "fido"})
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


######################################################################
#  T E S T   H T T P   C O N V E N T I O N S
######################################################################
class TestHttpConventions(TestCase):
    """Method and URL behavior the web framework supplies on its own

    Note: the leading-duplicate-slash cases ("//pets") cannot be exercised
    here because the HTTP client collapses a leading "//" to "/" before the
    request is sent. They are covered against a live server instead.
    """

    def setUp(self):
        """Runs before each test"""
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_head_on_get_routes(self):
        """It should answer HEAD wherever it answers GET"""
        for path in ("/health", "/", BASE_URL):
            response = self.client.head(path)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.content), 0)

    def test_head_unknown_route(self):
        """It should not answer HEAD on a route that does not exist"""
        response = self.client.head("/nope")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_options_lists_allowed_methods(self):
        """It should report the allowed methods for a known URL"""
        response = self.client.options(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        allowed = {m.strip() for m in response.headers["Allow"].split(",")}
        self.assertEqual(allowed, {"GET", "HEAD", "POST", "OPTIONS"})

    def test_options_on_item_url(self):
        """It should report the allowed methods for a single pet URL"""
        response = self.client.options(f"{BASE_URL}/1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        allowed = {m.strip() for m in response.headers["Allow"].split(",")}
        self.assertEqual(allowed, {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"})

    def test_options_unknown_route(self):
        """It should not answer OPTIONS on a route that does not exist"""
        response = self.client.options("/nope")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_interior_duplicate_slashes_redirect(self):
        """It should permanently redirect a URL with interior duplicate slashes"""
        response = self.client.get("/pets//1", follow_redirects=False)
        self.assertEqual(response.status_code, 308)
        self.assertTrue(response.headers["Location"].endswith("/pets/1"))

    def test_trailing_duplicate_slashes_not_found(self):
        """It should not serve a URL with trailing duplicate slashes"""
        response = self.client.get("/pets/1//")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_generated_documentation_routes(self):
        """It should not expose URLs the original service did not have"""
        for path in ("/docs", "/redoc", "/openapi.json"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
