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
Pet Store Service

This service implements a REST API that allows you to Create, Read, Update
and Delete Pets from the inventory of pets in the PetShop
"""

import json
import logging

from fastapi import APIRouter, Request

from service.models import Pet
from service.common import status  # HTTP Status Codes
from service.common.error_handlers import SortedJSONResponse, abort

logger = logging.getLogger("petstore")

router = APIRouter()


######################################################################
# GET HEALTH CHECK
######################################################################
@router.get("/health")
async def health_check():
    """Let them know our heart is still beating"""
    return SortedJSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Healthy"},
    )


######################################################################
# GET INDEX
######################################################################
@router.get("/")
async def index(request: Request):
    """Root URL response"""
    logger.info("Request for Root URL")
    return SortedJSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "name": "Pet Demo REST API Service",
            "version": "1.0",
            "paths": str(request.url_for("list_pets")),
        },
    )


######################################################################
# LIST ALL PETS
######################################################################
@router.get("/pets")
async def list_pets():
    """Returns all of the Pets"""
    logger.info("Request for pet list")

    # Return all of the Pets
    pets = Pet.all()

    results = [pet.serialize() for pet in pets]
    logger.info("Returning %d pets", len(results))
    return SortedJSONResponse(status_code=status.HTTP_200_OK, content=results)


######################################################################
# READ A PET
######################################################################
@router.get("/pets/{pet_id:int}")
async def get_pets(pet_id: int):
    """
    Retrieve a single Pet

    This endpoint will return a Pet based on it's id
    """
    logger.info("Request to Retrieve a pet with id [%s]", pet_id)

    # Attempt to find the Pet and abort if not found
    pet = Pet.find(pet_id)
    if not pet:
        abort(status.HTTP_404_NOT_FOUND, f"Pet with id '{pet_id}' was not found.")

    logger.info("Returning pet: %s", pet.name)
    return SortedJSONResponse(
        status_code=status.HTTP_200_OK, content=pet.serialize()
    )


######################################################################
# CREATE A NEW PET
######################################################################
@router.post("/pets")
async def create_pets(request: Request):
    """
    Create a Pet
    This endpoint will create a Pet based the data in the body that is posted
    """
    logger.info("Request to Create a Pet...")
    check_content_type(request, "application/json")

    pet = Pet()
    # Get the data from the request and deserialize it
    data = await get_json(request)
    logger.info("Processing: %s", data)
    pet.deserialize(data)

    # Save the new Pet to the database
    pet.create()
    logger.info("Pet with new id [%s] saved!", pet.id)

    # Return the location of the new Pet
    location_url = str(request.url_for("get_pets", pet_id=pet.id))
    return SortedJSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=pet.serialize(),
        headers={"Location": location_url},
    )


######################################################################
# UPDATE AN EXISTING PET
######################################################################
@router.put("/pets/{pet_id:int}")
async def update_pets(pet_id: int, request: Request):
    """
    Update a Pet

    This endpoint will update a Pet based the body that is posted
    """
    logger.info("Request to Update a pet with id [%s]", pet_id)
    check_content_type(request, "application/json")

    # Attempt to find the Pet and abort if not found
    pet = Pet.find(pet_id)
    if not pet:
        abort(status.HTTP_404_NOT_FOUND, f"Pet with id '{pet_id}' was not found.")

    # Update the Pet with the new data
    data = await get_json(request)
    logger.info("Processing: %s", data)
    pet.deserialize(data)

    # Save the updates to the database
    pet.update()

    logger.info("Pet with ID: %d updated.", pet.id)
    return SortedJSONResponse(
        status_code=status.HTTP_200_OK, content=pet.serialize()
    )


######################################################################
# DELETE A PET
######################################################################
@router.delete("/pets/{pet_id:int}")
async def delete_pets(pet_id: int):
    """
    Delete a Pet

    This endpoint will delete a Pet based the id specified in the path
    """
    logger.info("Request to Delete a pet with id [%s]", pet_id)

    # Delete the Pet if it exists
    pet = Pet.find(pet_id)
    if pet:
        logger.info("Pet with ID: %d found.", pet.id)
        pet.delete()

    logger.info("Pet with ID: %d delete complete.", pet_id)
    return SortedJSONResponse(
        status_code=status.HTTP_204_NO_CONTENT, content=None
    )


######################################################################
######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################
######################################################################


######################################################################
# Reads and decodes the JSON body of a request
######################################################################
async def get_json(request: Request) -> dict:
    """Returns the decoded JSON body, aborting with 400 when it is not JSON"""
    body = await request.body()
    try:
        return json.loads(body)
    except ValueError as error:
        logger.error("Failed to decode JSON object: %s", error)
        abort(status.HTTP_400_BAD_REQUEST)


######################################################################
# Checks the ContentType of a request
######################################################################
def check_content_type(request: Request, content_type) -> None:
    """Checks that the media type is correct"""
    if "Content-Type" not in request.headers:
        logger.error("No Content-Type specified.")
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )

    if request.headers["Content-Type"] == content_type:
        return

    logger.error("Invalid Content-Type: %s", request.headers["Content-Type"])
    abort(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        f"Content-Type must be {content_type}",
    )
