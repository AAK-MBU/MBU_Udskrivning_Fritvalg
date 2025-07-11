"""Handle the creation of discharge documents based on patient age."""
import os
import datetime
from dateutil.relativedelta import relativedelta


def handle_discharge_document(orchestrator_connection, queue_element_data, solteq_tand_db_object, is_patient_under_16):
    """
    Create a discharge document based on the patient's age.
    If the document already exists, it will not be created again.
    """
    if is_patient_under_16:
        template_name = "Følgebrev - Frit valg 0-15 år"
        discharge_document_filename = "Udskrivning til privat praksis 0-15 år"
    else:
        template_name = "Følgebrev - Frit valg fra 16 år"
        discharge_document_filename = "Udskrivning til privat praksis fra 16 år"

    one_month_ago = datetime.datetime.now() - relativedelta(months=1)
    orchestrator_connection.log_trace("Checking for existing discharge documents.")
    list_of_documents = solteq_tand_db_object.get_list_of_documents(
        filters={
            "p.cpr": queue_element_data["patient_cpr"],
            "ds.OriginalFilename": f"%{discharge_document_filename}%",
            "ds.rn": "1",
            "ds.DocumentStoreStatusId": "1",
            "ds.DocumentCreatedDate": (">=", one_month_ago),
        }
    )
    orchestrator_connection.log_trace(f"Found {len(list_of_documents)} existing discharge documents.")

    if not list_of_documents:
        folder_path = f"C:\\tmp\\tmt\\{queue_element_data['patient_cpr']}"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        orchestrator_connection.log_trace("No existing discharge documents found, creating a new one.")
        document_template_metadata = {
            "templateName": template_name,
            "destinationPath": folder_path,
            "dischargeDocumentFilename": discharge_document_filename,
        }
        orchestrator_connection.solteq_tand_app.create_document_from_template(
            metadata=document_template_metadata
        )
        orchestrator_connection.log_trace(
            "Discharge document was created successfully."
        )
    else:
        orchestrator_connection.log_trace(
            "Discharge document already exists, skipping creation."
        )
