"""
This module contains a function to check if the contractor ID is valid.
"""

from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection

from robot_framework.exceptions import BusinessError
from robot_framework.subprocesses.db_utils import get_exceptions


def check_contractor_data(
    orchestrator_connection: OrchestratorConnection,
    app_obj,
) -> None:
    """
    Check if the contractor ID is valid.

    Args:
        orchestrator_connection: A connection to OpenOrchestrator.

    Raises:
        BusinessError: If a business rule is broken.
    """
    try:
        app_obj.open_edi_portal()
        contractor_check = app_obj.edi_portal_check_contractor_id(
            orchestrator_connection=orchestrator_connection
        )
        orchestrator_connection.log_trace("Checking if contractor id is set...")
        rpa_db_conn = orchestrator_connection.get_constant("DbConnectionString").value
        if contractor_check["rowCount"] == 0:
            excp = get_exceptions(rpa_db_conn)
            message = [d for d in excp if d["exception_code"] == "1G"][0][
                "message_text"
            ]
            raise BusinessError(message)
        if contractor_check["isPhoneNumberMatch"] is False:
            excp = get_exceptions(rpa_db_conn)
            message = [d for d in excp if d["exception_code"] == "1H"][0][
                "message_text"
            ]
            raise BusinessError(message)
    except BusinessError:
        raise
    except Exception as error:  # pylint: disable=broad-except
        print(f"Error: {error}")
