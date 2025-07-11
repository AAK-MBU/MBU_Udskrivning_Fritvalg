"""
Database handler for retrieving person and image data.
"""


def get_person_info(orchestrator_connection, db_handler, ssn: str) -> tuple | None:
    """Retrieve and validate person data from the database."""
    try:
        person_data = db_handler.get_person_data(external_id=ssn)
    except Exception as e:
        print(f"Error retrieving person data: {e}")
        raise

    if not person_data:
        orchestrator_connection.log_trace("No person data found for SSN.")
        return None

    person = person_data[0]

    if not person.get("person_id"):
        orchestrator_connection.log_trace("Person ID not found for SSN.")
        return None

    person_id = person["person_id"]

    if not person.get("first_name") and not person.get("last_name"):
        orchestrator_connection.log_trace("Person name not found for SSN.")
        return None

    person_name = " ".join(
        filter(
            None,
            [
                person.get("first_name"),
                person.get("second_name"),
                person.get("third_name"),
                person.get("last_name"),
            ],
        )
    )

    return person_id, person_name


def get_image_data(db_handler, person_id: str) -> list:
    """Retrieve image IDs and image data from the database."""
    image_ids = []
    images_data = []

    image_ids = db_handler.get_image_ids(patient_id=person_id)

    if image_ids:
        images_data = db_handler.get_image_data(image_ids=image_ids)

    return images_data
