"""This module contains the main process of the robot."""

import datetime
import json
import time

from dateutil.relativedelta import relativedelta
from mbu_dev_shared_components.solteqtand import SolteqTandDatabase
from OpenOrchestrator.database.queues import QueueElement
from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection

from robot_framework.exceptions import BusinessError
from robot_framework.subprocesses.helper_functions import is_under_16
from robot_framework.subprocesses.initalization.initalize import initalization_checks
from robot_framework.subprocesses.process.document.create_medical_record import (
    check_and_create_medical_record_document,
)
from robot_framework.subprocesses.process.document.handle_discharge_document import (
    handle_discharge_document,
)
from robot_framework.subprocesses.process.document.send_discharge_document import (
    check_and_send_discharge_document,
)
from robot_framework.subprocesses.process.edi.edi_portal_handler import (
    EdiContext,
    edi_portal_handler,
)
from robot_framework.subprocesses.process.edi.get_files_for_edi_portal import (
    prepare_edi_portal_documents,
)
from robot_framework.subprocesses.process.patient.create_booking_reminders import (
    create_booking_reminders,
)
from robot_framework.subprocesses.process.patient.create_event import (
    create_event_if_not_created,
)
from robot_framework.subprocesses.process.patient.update_patient_info import (
    update_patient_info,
)
from robot_framework.subprocesses.process.romexis.romexis_images_handler import (
    get_images_from_romexis,
)
from robot_framework.subprocesses.reset.clean_up import kill_application, release_keys
from robot_framework.subprocesses.reset.close_applications import close_patient_window


def process(
    orchestrator_connection: OrchestratorConnection,
    queue_element: QueueElement | None = None,
) -> None:
    """Do the primary process of the robot."""
    # Ensure no modifier keys are stuck. VM sometimes causes keys to get
    # stuck, so we release them at the start of each process.
    release_keys(orchestrator_connection)

    try:
        orchestrator_connection.log_trace("Running process.")

        kill_application("AcroRd32.exe", orchestrator_connection)

        if queue_element is None or queue_element.data is None:
            orchestrator_connection.log_error(
                "Queue element or data is None, exiting process."
            )
            return
        queue_element_data = json.loads(queue_element.data)

        queue_element_data["patient_cpr"] = queue_element_data["patient_cpr"].replace(
            "-", ""
        )

        orchestrator_connection.log_trace(
            f"Handling queue element: {queue_element_data['requestNumberServiceNow']}"
        )

        # Initialize the Solteq Tand database instance
        solteq_tand_db_object = SolteqTandDatabase(
            orchestrator_connection.get_constant("solteq_tand_db_connstr").value
        )

        orchestrator_connection.solteq_tand_app.open_patient(
            queue_element_data.get("patient_cpr")
        )

        orchestrator_connection.log_trace("Initalization checks.")
        initalization_checks(orchestrator_connection, queue_element_data)

        # Check if the patient is under 16 years old.
        orchestrator_connection.log_trace("Checking if patient is under 16 years old.")
        is_patient_under_16 = is_under_16(queue_element_data["patient_cpr"])
        orchestrator_connection.log_trace(
            f"Is patient under 16 years old: {is_patient_under_16}"
        )

        # Update patient information.
        orchestrator_connection.log_trace("Updating patient information.")
        discharge_document_filename = update_patient_info(
            orchestrator_connection, is_patient_under_16
        )

        # Check if the patient has a specific event; if so, process it.
        orchestrator_connection.log_trace("Processing event.")
        create_event_if_not_created(
            orchestrator_connection, queue_element_data, solteq_tand_db_object
        )

        # Check if booking reminders are already created; if not, create them.
        orchestrator_connection.log_trace(
            "Creating booking reminders if not already created."
        )
        create_booking_reminders(
            orchestrator_connection,
            queue_element_data,
            solteq_tand_db_object,
            is_patient_under_16,
        )

        # Check if the discharge document is already created; if not, create it.
        orchestrator_connection.log_trace(
            "Creating discharge document if not already created."
        )
        handle_discharge_document(
            orchestrator_connection,
            queue_element_data,
            solteq_tand_db_object,
            is_patient_under_16,
        )

        # Check if the discharge document is already sent to DigitalPost; if not, send it.
        orchestrator_connection.log_trace(
            "Checking and sending discharge document if not already sent."
        )
        check_and_send_discharge_document(
            orchestrator_connection,
            queue_element_data,
            solteq_tand_db_object,
            discharge_document_filename,
        )

        # Get images from Romexis and create a zip file.
        orchestrator_connection.log_trace("Fetching images from Romexis.")
        images_result = get_images_from_romexis(
            orchestrator_connection, queue_element_data
        )
        if images_result is not None:
            zip_path, zip_filename = images_result
            orchestrator_connection.log_trace(
                f"Zip file created: {zip_path} with filename: {zip_filename}"
            )

        # Call the function to check and create the digital printed journal if needed.
        orchestrator_connection.log_trace(
            "Checking and creating medical record document if not already created."
        )
        check_and_create_medical_record_document(
            orchestrator_connection, queue_element_data, solteq_tand_db_object
        )

        # Get other documents if the regionstilsagn checkbox is checked.
        if queue_element_data["regionstilsagn"]:
            get_other_documents = True
            orchestrator_connection.log_trace(
                "Regionstilsagn checkbox is checked, getting other documents."
            )
        else:
            get_other_documents = False
            orchestrator_connection.log_trace(
                "Regionstilsagn checkbox is not checked, skipping other documents."
            )

        # Get all documents needed for EDI Portal upload.
        orchestrator_connection.log_trace("Preparing EDI Portal documents for upload.")
        joined_file_paths = prepare_edi_portal_documents(
            orchestrator_connection,
            solteq_tand_db_object,
            queue_element_data,
            get_other_documents=get_other_documents,
        )

        # EDI PORTAL
        orchestrator_connection.solteq_tand_app.open_edi_portal()
        time.sleep(5)

        administrative_note = (
            orchestrator_connection.administrative_note[0].get("Beskrivelse")
            if orchestrator_connection.administrative_note
            and len(orchestrator_connection.administrative_note) > 0
            else None
        )

        # Send the documents trough the EDI Portal to the new dentist.
        try:
            ctx = EdiContext(
                extern_clinic_data=orchestrator_connection.extern_clinic_data,
                queue_element=queue_element_data,
                path_to_files_for_upload=joined_file_paths,
                journal_note=administrative_note,
            )
            receipt_pdf = edi_portal_handler(
                ctx, orchestrator_connection=orchestrator_connection
            )
            orchestrator_connection.solteq_tand_app.close_edi_portal()
        except Exception as e:
            orchestrator_connection.solteq_tand_app.close_edi_portal()
            raise e

        # Check if the receipt PDF was created successfully and upload it to Solteq Tand.
        orchestrator_connection.log_trace("Checking for existing EDI Portal documents.")
        edi_receipt_date_one_month_ago = datetime.datetime.now() - relativedelta(
            months=1
        )
        list_of_documents = solteq_tand_db_object.get_list_of_documents(
            filters={
                "p.cpr": queue_element_data["patient_cpr"],
                "ds.OriginalFilename": f"%EDI Portal - {queue_element_data['patient_name']}%",
                "ds.rn": "1",
                "ds.DocumentStoreStatusId": "1",
                "ds.DocumentCreatedDate": (">=", edi_receipt_date_one_month_ago),
            }
        )
        orchestrator_connection.log_trace(
            f"Found {len(list_of_documents)} existing EDI Portal document."
        )

        if not list_of_documents:
            orchestrator_connection.log_trace(
                "No existing EDI Portal document found, creating a new one."
            )
            orchestrator_connection.solteq_tand_app.create_document(
                document_full_path=receipt_pdf
            )
            orchestrator_connection.log_trace(
                "EDI Portal document was created successfully."
            )
        else:
            orchestrator_connection.log_trace(
                "EDI Portal document already exists, skipping creation."
            )

        # Check if administrative note exists if not create it.
        orchestrator_connection.log_trace("Checking if administrative note exists.")
        journal_note_date_one_month_ago = datetime.datetime.now() - relativedelta(
            months=1
        )
        journal_note = "Administrativt notat 'Udskrivning til frit valg gennemført af robot. Sendt information til pt. og sendt journal og billedmateriale til privat tandlæge via EDI-portal. Se dokumentskab. Journal flyttet til Tandplejen Aarhus'"
        filter_params = {
            "p.cpr": queue_element_data["patient_cpr"],
            "dn.Beskrivelse": f"%{journal_note}%",
            "ds.Dokumenteret": (">=", journal_note_date_one_month_ago),
        }
        result = solteq_tand_db_object.get_list_of_journal_notes(
            filters=filter_params, order_by="ds.Dokumenteret", order_direction="DESC"
        )

        if not result:
            orchestrator_connection.log_info("Creating administrative note.")
            orchestrator_connection.solteq_tand_app.create_journal_note(
                note_message=journal_note, checkmark_in_complete=True
            )
            orchestrator_connection.log_info(
                "Administrative note created successfully."
            )
        orchestrator_connection.log_info("Administrative note allready exists.")
    except BusinessError as be:
        orchestrator_connection.log_error(f"{be}")
        raise be
    except Exception as e:
        orchestrator_connection.log_error(f"{e}")
        raise e
    finally:
        close_patient_window(orchestrator_connection=orchestrator_connection)
