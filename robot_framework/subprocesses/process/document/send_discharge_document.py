"""Check if the discharge document is already sent to DigitalPost; if not, send it."""

import datetime

from dateutil.relativedelta import relativedelta


def check_and_send_discharge_document(
    orchestrator_connection,
    queue_element_data,
    solteq_tand_db_object,
    discharge_document_filename,
):
    """
    Check if the discharge document is already sent to DigitalPost; if not, send it.
    This function checks for the existence of a discharge document within the last month
    and sends it to DigitalPost if it has not been sent yet.
    """
    one_month_ago = datetime.datetime.now() - relativedelta(months=1)

    # Check if the discharge document is already sent to DigitalPost; if not, send it.
    orchestrator_connection.log_trace(
        "Checking if the discharge document is already sent to DigitalPost."
    )
    list_of_documents_send_document = solteq_tand_db_object.get_list_of_documents(
        filters={
            "p.cpr": queue_element_data["patient_cpr"],
            "ds.OriginalFilename": f"%{discharge_document_filename}%",
            "ds.rn": "1",
            "ds.DocumentStoreStatusId": "1",
            "ds.DocumentCreatedDate": (">=", one_month_ago),
        }
    )

    if (
        list_of_documents_send_document
        and not list_of_documents_send_document[0]["SentToNemSMS"]
    ):
        orchestrator_connection.log_trace(
            "Discharge document not sent to DigitalPost, proceeding to send."
        )
        discharge_document_metadata = {
            "documentTitle": discharge_document_filename + ".pdf",
            "digitalPostSubject": "Orientering om udskrivning til privat tandlæge",
        }
        orchestrator_connection.solteq_tand_app.send_discharge_document_digitalpost(
            metadata=discharge_document_metadata
        )
        orchestrator_connection.log_trace(
            "Discharge document sent to DigitalPost successfully."
        )
    else:
        orchestrator_connection.log_trace(
            "Discharge document already sent to DigitalPost or not found, skipping sending."
        )
