"""This module handles cleaning up temporary and download folders to ensure a clean slate for the robot."""

import os
import shutil
from pathlib import Path

from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection

from robot_framework import config


def clean_up_tmp_folder(orchestrator_connection: OrchestratorConnection) -> None:
    """Clean up the temporary folder."""
    orchestrator_connection.log_trace("Cleaning up temporary folder.")
    if os.path.exists(config.TMP_FOLDER):
        for filename in os.listdir(config.TMP_FOLDER):
            file_path = os.path.join(config.TMP_FOLDER, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as error:  # pylint: disable=broad-except
                orchestrator_connection.log_trace(f"Failed to delete {file_path}. Reason: {error}")
        orchestrator_connection.log_trace(f"Temporary folder {config.TMP_FOLDER} cleaned up.")
    else:
        orchestrator_connection.log_trace(f"Temporary folder {config.TMP_FOLDER} does not exist.")


def clean_up_download_folder(orchestrator_connection: OrchestratorConnection) -> None:
    """Clean up the download folder."""
    download_folder = str(Path.home() / "Downloads")

    orchestrator_connection.log_trace("Cleaning up download folder.")
    if os.path.exists(download_folder):
        for filename in os.listdir(download_folder):
            file_path = os.path.join(download_folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as error:  # pylint: disable=broad-except
                orchestrator_connection.log_trace(f"Failed to delete {file_path}. Reason: {error}")
        orchestrator_connection.log_trace(f"Download folder {download_folder} cleaned up.")
    else:
        orchestrator_connection.log_trace(f"Download folder {download_folder} does not exist.")
