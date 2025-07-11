"""This module contains functions to close the Solteq Tand application and its patient window."""

from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection


def close_patient_window(orchestrator_connection: OrchestratorConnection) -> None:
    """Closes the patient window in the Solteq Tand application if it exists."""
    if hasattr(orchestrator_connection, "solteq_tand_app") and orchestrator_connection.solteq_tand_app:
        try:
            orchestrator_connection.log_trace("Close patient window.")
            orchestrator_connection.solteq_tand_app.close_patient_window()
        except Exception as error:  # pylint: disable=broad-except
            orchestrator_connection.log_trace("Error closing patient window." + str(error))


def close_solteq_tand(orchestrator_connection: OrchestratorConnection) -> None:
    """Closes the Solteq Tand application if it exists."""
    if hasattr(orchestrator_connection, "solteq_tand_app") and orchestrator_connection.solteq_tand_app:
        try:
            orchestrator_connection.log_trace("Close Solteq Tand.")
            orchestrator_connection.solteq_tand_app.close_solteq_tand()
            orchestrator_connection.log_trace("Solteq Tand closed.")
        except Exception as error:  # pylint: disable=broad-except
            orchestrator_connection.log_trace(f"Error closing Solteq Tand: {error}")
    else:
        orchestrator_connection.log_trace("solteq_tand_app attribute not found. Skipping close operations.")
