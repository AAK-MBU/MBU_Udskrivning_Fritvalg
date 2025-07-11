"""Check if the medical record document is already created; if not, create it."""

import datetime
from dateutil.relativedelta import relativedelta


def check_and_create_medical_record_document(
    orchestrator_connection, queue_element_data, solteq_tand_db_object
):
    """Check if the medical record document is already created; if not, create it."""
    orchestrator_connection.log_trace(
        "Checking if the medical record document is already created."
    )
    one_month_ago = datetime.datetime.now() - relativedelta(months=1)
    document_type = "Journaludskrift"
    list_of_documents_medical_record = solteq_tand_db_object.get_list_of_documents(
        filters={
            "p.cpr": queue_element_data["patient_cpr"],
            "ds.DocumentDescription": "%Printet journal%(delvis kopi)%",
            "ds.DocumentType": document_type,
            "ds.rn": "1",
            "ds.DocumentStoreStatusId": "1",
            "ds.DocumentCreatedDate": (">=", one_month_ago),
        }
    )
    orchestrator_connection.log_trace(
        f"Found {len(list_of_documents_medical_record)} medical record documents."
    )

    if not list_of_documents_medical_record:
        orchestrator_connection.log_trace(
            "Medical record document not found, proceeding to create it."
        )
        orchestrator_connection.solteq_tand_app.create_digital_printet_journal()
        orchestrator_connection.log_trace(
            "Medical record document created successfully."
        )
    else:
        orchestrator_connection.log_trace(
            "Medical record document already exists, skipping creation."
        )
