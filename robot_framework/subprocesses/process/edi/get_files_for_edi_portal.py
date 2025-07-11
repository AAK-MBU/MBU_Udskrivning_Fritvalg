"""Get files for EDI Portal."""
import os
import pathlib
import shutil
from robot_framework.exceptions import BusinessError
from robot_framework import config


def prepare_edi_portal_documents(
    orchestrator_connection,
    solteq_tand_db_object,
    queue_element_data: dict,
    get_other_documents: bool = True
) -> str:
    """
    Prepare documents for EDI Portal:
        - Retrieves the relevant documents.
        - Copies them into a temporary directory.
        - Returns joined file paths ready for EDI upload.
    """

    def get_list_of_documents_for_edi_portal(get_other_documents: bool) -> list:
        """Get the latest version of 'Journaludskrift' and other documents for EDI Portal."""
        try:
            print(f"{get_other_documents=}")
            if get_other_documents:
                document_types = ["Journaludskrift", "Udskrivning - Frit valg!$#"]
            else:
                document_types = ["Journaludskrift"]

            orchestrator_connection.log_trace(
                f"Getting documents for EDI Portal for patient with types: {document_types}"
            )
            list_of_documents = solteq_tand_db_object.get_list_of_documents(
                filters={
                    "ds.DocumentType": document_types,
                    "p.cpr": queue_element_data["patient_cpr"],
                    "ds.rn": "1",
                    "ds.DocumentStoreStatusId": "1",
                }
            )
            print(f"{list_of_documents=}")

            if not list_of_documents:
                orchestrator_connection.log_trace(
                    "No documents found for patient."
                )
                raise BusinessError("No documents found.")

            orchestrator_connection.log_trace(
                f"Found {len(list_of_documents)} documents for patient."
            )

            # Filter to get the latest 'Journaludskrift' based on DocumentCreatedDate
            latest_journal = None
            if "Journaludskrift" in document_types:
                journal_documents = [
                    doc for doc in list_of_documents if doc["DocumentType"] == "Journaludskrift"
                ]
                if journal_documents:
                    latest_journal = max(
                        journal_documents, key=lambda doc: doc["DocumentCreatedDate"]
                    )

            # Include the latest 'Journaludskrift' and other documents
            filtered_documents = [
                doc for doc in list_of_documents if doc["DocumentType"] != "Journaludskrift"
            ]
            if latest_journal:
                filtered_documents.append(latest_journal)

            # Change filename for Journaludskrift documents to include patient name
            for doc in filtered_documents:
                if doc["DocumentType"] == "Journaludskrift":
                    doc["OriginalFilename"] = f"Journaludskrift - {queue_element_data['patient_name']}.pdf"

            return filtered_documents
        except Exception as e:
            orchestrator_connection.log_error(
                f"Error getting documents for EDI Portal: {e}"
            )
            raise

    def copy_documents_for_edi_portal(documents: list) -> str:
        """Copy documents for EDI Portal."""
        try:
            orchestrator_connection.log_trace(
                "Copying documents for EDI Portal."
            )
            temp_dir = os.path.join(config.TMP_FOLDER, queue_element_data["patient_cpr"], "edi_portal")

            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)

            for document in documents:
                source_path = document["fileSourcePath"]
                destination_path = os.path.join(temp_dir, document["OriginalFilename"])
                shutil.copy2(source_path, destination_path)
                orchestrator_connection.log_trace(
                    f"Copied {source_path} to {destination_path}"
                )

            return temp_dir
        except Exception as e:
            orchestrator_connection.log_error(
                f"Error copying documents for EDI Portal: {e}"
            )
            raise

    # Retrieve and filter the documents
    list_of_documents = get_list_of_documents_for_edi_portal(get_other_documents)
    if not list_of_documents:
        raise ValueError("No documents found for EDI Portal.")

    # Copy the documents to a temporary folder for the EDI Portal
    path_to_documents = copy_documents_for_edi_portal(list_of_documents)
    files_to_edi_portal = [f for f in pathlib.Path(path_to_documents).iterdir() if f.is_file()]
    joined_file_paths = " ".join(f'"{str(f)}"' for f in files_to_edi_portal)
    orchestrator_connection.log_trace(
        f"Prepared documents for EDI Portal: {joined_file_paths}"
    )
    return joined_file_paths
