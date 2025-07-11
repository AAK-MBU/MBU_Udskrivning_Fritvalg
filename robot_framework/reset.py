"""This module handles resetting the state of the computer so the robot can work with a clean slate."""

import psutil

from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection

from mbu_dev_shared_components.solteqtand import SolteqTandApp

from robot_framework import config

from robot_framework.subprocesses.reset.close_applications import (
    close_patient_window,
    close_solteq_tand,
)
from robot_framework.subprocesses.reset.clean_up import (
    clean_up_tmp_folder,
    clean_up_download_folder,
)


def reset(orchestrator_connection: OrchestratorConnection) -> None:
    """Clean up, close/kill all programs and start them again."""
    orchestrator_connection.log_trace("Resetting.")
    clean_up(orchestrator_connection)
    close_all(orchestrator_connection)
    kill_all(orchestrator_connection)
    open_all(orchestrator_connection)


def clean_up(orchestrator_connection: OrchestratorConnection) -> None:
    """Do any cleanup needed to leave a blank slate."""
    orchestrator_connection.log_trace("Doing cleanup.")

    orchestrator_connection.log_trace("Cleaning up temporary folder.")
    clean_up_tmp_folder(orchestrator_connection=orchestrator_connection)

    orchestrator_connection.log_trace("Cleaning up download folder.")
    clean_up_download_folder(orchestrator_connection=orchestrator_connection)


def close_all(orchestrator_connection: OrchestratorConnection) -> None:
    """Gracefully close all applications used by the robot."""
    orchestrator_connection.log_trace("Closing all applications.")

    orchestrator_connection.log_trace("Closing Solteq Tand patient window.")
    close_patient_window(orchestrator_connection=orchestrator_connection)

    orchestrator_connection.log_trace("Closing Solteq Tand application.")
    close_solteq_tand(orchestrator_connection=orchestrator_connection)


def kill_all(orchestrator_connection: OrchestratorConnection) -> None:
    """Forcefully close all applications used by the robot."""
    orchestrator_connection.log_trace("Killing all applications.")

    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == "TMTand.exe":
            orchestrator_connection.log_trace(f"Killing TMTand.exe process (PID {proc.pid}).")
            try:
                proc.kill()
            # pylint: disable-next = broad-exception-caught
            except Exception as e:
                orchestrator_connection.log_trace(f"Failed to kill TMTand.exe process (PID {proc.pid}): {e}")


def open_all(orchestrator_connection: OrchestratorConnection) -> None:
    """Open all programs used by the robot."""
    orchestrator_connection.log_trace("Opening all applications.")

    # Get credentials from orchestrator database
    credentials = orchestrator_connection.get_credential("solteq_tand_svcrpambu001")
    if not credentials:
        orchestrator_connection.log_trace("No credentials found.")
        raise ValueError("No credentials found.")

    # Initialize Solteq Tand application
    app_obj = SolteqTandApp(
        config.SOLTEQ_TAND_APP_PATH, credentials.username, credentials.password
    )
    orchestrator_connection.solteq_tand_app = app_obj

    orchestrator_connection.log_trace("Opening Solteq Tand.")
    # Start the application and login
    try:
        orchestrator_connection.solteq_tand_app.start_application()
        orchestrator_connection.solteq_tand_app.login()
    except Exception as error:
        orchestrator_connection.log_trace(f"Error starting Solteq Tand: {error}")
        raise RuntimeError("Error starting Solteq Tand.") from error
