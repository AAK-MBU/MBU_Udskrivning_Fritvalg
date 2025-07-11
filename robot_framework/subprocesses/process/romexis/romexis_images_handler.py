"""This module handles the retrieval of images from Romexis."""

import os
from mbu_dev_shared_components.romexis.db_handler import RomexisDbHandler
from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection
from robot_framework.subprocesses.process.romexis.db_handler import (
    get_person_info,
    get_image_data,
)
from robot_framework.subprocesses.process.romexis.image_handler import (
    process_images_threaded,
    clear_img_files_in_folder,
)
from robot_framework.subprocesses.process.romexis.zip_handler import (
    create_zip_from_images,
)
from robot_framework import config
from robot_framework.exceptions import BusinessError


def get_images_from_romexis(
    orchestrator_connection: OrchestratorConnection, queue_element_data
) -> tuple[str, str] | None:
    """
    Fetches images from the Romexis database.

    Returns:
        list: A list of dictionaries containing image data.
    """
    try:
        orchestrator_connection.log_trace("Fetching images from Romexis database.")
        romexis_db_conn = orchestrator_connection.get_constant(
            "romexis_db_connstr"
        ).value
        romexis_db_handler = RomexisDbHandler(conn_str=romexis_db_conn)
        ssn = queue_element_data.get("patient_cpr")
        destination_path = os.path.join(config.TMP_FOLDER, ssn, "img")

        person_info = get_person_info(orchestrator_connection, romexis_db_handler, ssn)
        if person_info is None:
            orchestrator_connection.log_error("No person info retrieved.")
            return None
        person_id, person_name = person_info

        images_data = get_image_data(romexis_db_handler, person_id)
        if not images_data:
            orchestrator_connection.log_trace("No images found for the patient.")
            return None

        process_images_threaded(
            images_data, destination_path, ssn, person_name, romexis_db_handler
        )

        orchestrator_connection.log_trace("Removing .img-files from temp folder.")
        clear_img_files_in_folder(folder_path=destination_path)

        orchestrator_connection.log_trace("Zipping images.")
        zip_full_path, zip_filename = create_zip_from_images(
            ssn=ssn, person_name=person_name, source_folder=destination_path
        )

        return zip_full_path, zip_filename
    except BusinessError as be:
        orchestrator_connection.log_error(f"Business error: {be}")
        raise be
    except Exception as e:
        # pylint: disable=W0719
        raise Exception(f"Failed to fetch images from Romexis: {e}") from e
