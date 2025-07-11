"""Perform initialization checks for the process."""

from mbu_dev_shared_components.solteqtand import SolteqTandDatabase

from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection
from OpenOrchestrator.database.queues import QueueElement

from robot_framework.exceptions import BusinessError
from robot_framework.subprocesses.db_utils import get_exceptions


class InitializationChecks:
    """
    Class to perform initialization checks for the process.
    - Check if primary clinic is set.
    - Check if extern dentist information is set.
    - Check if extern clinic has a deal with Aarhus Kommune.
    - Check if administrative note is set.
    - Check if contractor ID is valid.

    Args:
        orchestrator_connection: A connection to OpenOrchestrator.
        queue_element_data: Data from the queue element.
    """

    def __init__(
        self,
        orchestrator_connection: OrchestratorConnection,
        queue_element_data: QueueElement,
    ) -> None:
        self.orchestrator_connection = orchestrator_connection
        self.queue_element_data = queue_element_data
        self.solteq_tand_db_obj = SolteqTandDatabase(
            orchestrator_connection.get_constant("solteq_tand_db_connstr").value
        )
        self.rpa_db_conn = orchestrator_connection.get_constant("rpa_db_connstr").value

    def _get_error_message(self, exception_code: str, default: str) -> str:
        """Get the error message from the database based on the exception code."""
        try:
            excp = get_exceptions(
                self.rpa_db_conn  # self.queue_element_data["process_id"]
            )
            return next(
                (
                    d["message_text"]
                    for d in excp
                    if d["exception_code"] == exception_code
                ),
                default,
            )
        except RuntimeError as e:
            self.orchestrator_connection.log_error(
                f"Error retrieving exception message: {e}"
            )
            return default

    def check_primary_clinic_data(self) -> list:
        """Check if primary clinic is set."""
        try:
            filter_params = {
                "p.cpr": self.queue_element_data.get("patient_cpr"),
            }
            result = self.solteq_tand_db_obj.get_list_of_primary_dental_clinics(
                filters=filter_params
            )

            # Check if primary clinic is set
            self.orchestrator_connection.log_trace("Checking if primary clinic is set.")
            if not result:
                message = self._get_error_message("1A", "Primary clinic is not set.")
                raise BusinessError(message)
            self.orchestrator_connection.log_info("Primary clinic is set.")

            return result
        except BusinessError as be:
            self.orchestrator_connection.log_error(f"BusinessError: {be}")
            raise
        except Exception as e:
            self.orchestrator_connection.log_error(f"Unexpected error: {e}")
            raise

    def check_extern_clinic_data(self) -> list:
        """Check if extern dentist information is set."""
        try:
            filter_params = {
                "p.cpr": self.queue_element_data["patient_cpr"],
            }
            result = self.solteq_tand_db_obj.get_list_of_extern_dentist(
                filters=filter_params
            )

            # Check if extern dentist is set
            self.orchestrator_connection.log_trace(
                "Checking if extern dentist is set..."
            )
            if not result:
                message = self._get_error_message("1B", "Extern dentist is not set.")
                raise BusinessError(message)
            self.orchestrator_connection.log_info("Extern dentist is set.")

            # Check if contractor id is set
            self.orchestrator_connection.log_trace(
                "Checking if contractor id is set..."
            )
            if not result[0].get("contractorId"):
                message = self._get_error_message(
                    "1C", "Contractor id is not set for extern dentist."
                )
                raise BusinessError(message)
            self.orchestrator_connection.log_info("Contractor id is set.")

            # Check if phonenumber is set
            self.orchestrator_connection.log_trace("Checking if phone number is set...")
            if not result[0].get("phoneNumber"):
                message = self._get_error_message(
                    "1E", "Phone number is not set for extern dentist."
                )
                raise BusinessError(message)
            self.orchestrator_connection.log_info("Phone number is set.")

            return result
        except BusinessError as be:
            self.orchestrator_connection.log_error(f"BusinessError: {be}")
            raise
        except Exception as e:
            self.orchestrator_connection.log_error(f"Application error: {e}")
            raise

    def check_extern_clinic_deal(self, contractor_id: str) -> None:
        """Check if extern clinic has a deal with Aarhus Kommune."""
        try:
            filter_params = {
                "type": "3",
                "contractorId": contractor_id,
            }
            result = self.solteq_tand_db_obj.get_list_of_clinics(filters=filter_params)

            # Check if extern clinic has a deal with Aarhus Kommune
            self.orchestrator_connection.log_trace(
                "Checking if extern clinic has a deal with Aarhus Kommune...."
            )
            if not result:
                message = self._get_error_message("1D", "Found no no deal with Aarhus Kommune for the given extern clinic.")
                raise BusinessError(message)
            self.orchestrator_connection.log_info(
                "Extern clinic has a deal with Aarhus Kommune."
            )
        except BusinessError as be:
            self.orchestrator_connection.log_error(f"BusinessError: {be}")
            raise
        except Exception as e:
            self.orchestrator_connection.log_error(f"Application error: {e}")
            raise

    def check_administrative_note(self) -> list:
        """Check if administrative note is set and returns the note.

        Args:
            None

        Returns:
            list: A list of journal notes.

        Raises:
            BusinessError: If a business rule is broken.
        """
        try:
            filter_params = {
                "p.cpr": self.queue_element_data["patient_cpr"],
                "dn.Beskrivelse": "%Besked til privat tandlæge - Frit valg%",
            }
            result = self.solteq_tand_db_obj.get_list_of_journal_notes(
                filters=filter_params,
                order_by="ds.Dokumenteret",
                order_direction="DESC",
            )

            # Check if administrative note is set
            self.orchestrator_connection.log_trace(
                "Checking if administrative note is set..."
            )
            if not result and self.queue_element_data["tandplejeplan"] is True:
                message = self._get_error_message("1F", "Found no administrative note.")
                self.orchestrator_connection.log_error(message)
                raise BusinessError(message)
            self.orchestrator_connection.log_info("Administrative note is set.")

            return result
        except BusinessError as be:
            self.orchestrator_connection.log_error(f"BusinessError: {be}")
            raise
        except Exception as e:
            self.orchestrator_connection.log_error(f"Application error: {e}")
            raise

    def check_contractor_data(self) -> None:
        """
        Check if the contractor ID is valid.

        Raises:
            BusinessError: If a business rule is broken.
        """
        try:
            self.orchestrator_connection.solteq_tand_app.open_edi_portal()
            print("Checking contractor data...")
            result = self.orchestrator_connection.solteq_tand_app.edi_portal_check_contractor_id(
                self.orchestrator_connection.extern_clinic_data
            )

            # Check if contractor id is set
            self.orchestrator_connection.log_trace(
                "Checking if contractor id is set..."
            )

            if result["rowCount"] == 0:
                message = self._get_error_message("1G", "message_text")
                raise BusinessError(message)
            self.orchestrator_connection.log_info("Contractor id is set.")

            # Check if phonenumber is a match
            self.orchestrator_connection.log_trace(
                "Checking if phonenumber is a match..."
            )
            if result["isPhoneNumberMatch"] is False:
                message = self._get_error_message("1H", "message_text")
                raise BusinessError(message)
            self.orchestrator_connection.log_info("Phonenumber matched.")
            self.orchestrator_connection.solteq_tand_app.close_edi_portal()
        except BusinessError as be:
            self.orchestrator_connection.solteq_tand_app.close_edi_portal()
            self.orchestrator_connection.log_error(f"BusinessError: {be}")
            raise
        except Exception as error:
            self.orchestrator_connection.solteq_tand_app.close_edi_portal()
            self.orchestrator_connection.log_error(
                f"Error checking contractor data: {error}"
            )
            raise

    def check_other_documents(self) -> None:
        """Check if other documents exists if queue_element_data['regionstilsagn'] is set to true.

        Raises:
            BusinessError: If a business rule is broken.
        """
        try:
            result = self.solteq_tand_db_obj.get_list_of_documents(
                filters={
                    "p.cpr": self.queue_element_data["patient_cpr"],
                    "ds.rn": "1",
                    "ds.DocumentStoreStatusId": "1",
                    "ds.DocumentType": "Udskrivning - Frit valg!$#"
                }
            )

            # Check if other documents exists and if regionstilsagn is set
            self.orchestrator_connection.log_trace(
                "Checking if other documents exists and if regionstilsagn is set..."
            )
            if not result and self.queue_element_data["regionstilsagn"] is True:
                message = self._get_error_message("1I", "Found no other documents.")
                self.orchestrator_connection.log_error(message)
                raise BusinessError(message)
            self.orchestrator_connection.log_info("Other documents check completed.")
        except BusinessError as be:
            self.orchestrator_connection.log_error(f"BusinessError: {be}")
            raise
        except Exception as e:
            self.orchestrator_connection.log_error(f"Application error: {e}")
            raise


def initalization_checks(
    orchestrator_connection: OrchestratorConnection, queue_element_data: QueueElement
) -> None:
    """
    Perform initialization checks for the process.
    - Check if primary clinic is set and get primary clinic data.
    - Check if extern dentist information is set and get extern clinic data.
    - Check if extern clinic has a deal with Aarhus Kommune.
    - Check if administrative note is set and get administrative note.
    - Check if other documents exists if queue_element_data['regionstilsagn'] is set to true.
    - Check if contractor ID is valid.

    Args:
        orchestrator_connection: A connection to OpenOrchestrator.

    Raises:
        BusinessError: If a business rule is broken.
    """
    solteq_tand_db_conn = orchestrator_connection.get_constant(
        "solteq_tand_db_connstr"
    ).value

    if not solteq_tand_db_conn:
        raise ValueError("solteq_tand_db_connstr is not set.")

    rpa_db_conn = orchestrator_connection.get_constant("rpa_db_connstr").value
    if not rpa_db_conn:
        raise ValueError("rpa_db_connstr is not set.")

    # Creates an instance of the initializationChecks class
    init_checks_obj = InitializationChecks(
        orchestrator_connection=orchestrator_connection,
        queue_element_data=queue_element_data,
    )

    orchestrator_connection.log_info("Performing initialization checks...")

    # Check if primary clinic is set and get primary clinic data
    orchestrator_connection.primary_clinick_and_patient_data = (
        init_checks_obj.check_primary_clinic_data()
    )

    # Check if extern dentist information is set and get extern clinic data
    orchestrator_connection.extern_clinic_data = (
        init_checks_obj.check_extern_clinic_data()
    )

    # Check if extern clinic has a deal with Aarhus Kommune
    init_checks_obj.check_extern_clinic_deal(
        contractor_id=orchestrator_connection.extern_clinic_data[0].get("contractorId"),
    )

    # Check if administrative note is set and get administrative note
    orchestrator_connection.administrative_note = (
        init_checks_obj.check_administrative_note()
    )

    # Check if other documents exists if queue_element_data['regionstilsagn'] is set to true
    init_checks_obj.check_other_documents()

    # Check if contractor ID is valid
    init_checks_obj.check_contractor_data()

    orchestrator_connection.log_info("Initialization checks completed.")
