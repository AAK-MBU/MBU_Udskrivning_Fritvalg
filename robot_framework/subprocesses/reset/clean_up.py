"""This module handles cleaning up temporary and download folders to ensure a clean slate for the robot."""

import os
import shutil
from pathlib import Path

import psutil
from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection
from psutil import AccessDenied, NoSuchProcess, ZombieProcess

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
                orchestrator_connection.log_trace(
                    f"Failed to delete {file_path}. Reason: {error}"
                )
        orchestrator_connection.log_trace(
            f"Temporary folder {config.TMP_FOLDER} cleaned up."
        )
    else:
        orchestrator_connection.log_trace(
            f"Temporary folder {config.TMP_FOLDER} does not exist."
        )


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
                orchestrator_connection.log_trace(
                    f"Failed to delete {file_path}. Reason: {error}"
                )
        orchestrator_connection.log_trace(
            f"Download folder {download_folder} cleaned up."
        )
    else:
        orchestrator_connection.log_trace(
            f"Download folder {download_folder} does not exist."
        )


def kill_application(
    application_name: str, orchestrator_connection: OrchestratorConnection
) -> None:
    """Best-effort kill of all processes matching application_name on Windows."""
    target = application_name.lower()
    orchestrator_connection.log_trace(f"Killing {application_name} processes.")

    procs = []
    for proc in psutil.process_iter(
        attrs=["pid", "name", "exe", "cmdline"], ad_value=None
    ):
        try:
            name = (proc.info.get("name") or "").lower()
            exe_base = os.path.basename(proc.info.get("exe") or "").lower()
            if target in (name, exe_base):
                procs.append(proc)
        except (NoSuchProcess, ZombieProcess):
            continue
        # pylint: disable-next = broad-exception-caught
        except Exception as e:
            orchestrator_connection.log_trace(
                f"While enumerating {application_name}, skipping PID {getattr(proc, 'pid', '?')}: {e}"
            )

    # Try graceful terminate first
    for proc in procs:
        try:
            proc.terminate()
        except (NoSuchProcess, ZombieProcess):
            continue
        except AccessDenied as e:
            orchestrator_connection.log_trace(
                f"Access denied terminating {application_name} (PID {proc.pid}): {e}"
            )
        # pylint: disable-next = broad-exception-caught
        except Exception as e:
            orchestrator_connection.log_trace(
                f"Unexpected error terminating {application_name} (PID {proc.pid}): {e}"
            )

    # Wait a moment, then force kill stragglers
    gone, alive = psutil.wait_procs(procs, timeout=5)

    for p in gone:
        orchestrator_connection.log_trace(
            f"{application_name} (PID {p.pid}) exited cleanly."
        )

    for proc in alive:
        try:
            proc.kill()
        except (NoSuchProcess, ZombieProcess):
            continue
        except AccessDenied as e:
            orchestrator_connection.log_trace(
                f"Access denied killing {application_name} (PID {proc.pid}): {e}"
            )
        # pylint: disable-next = broad-exception-caught
        except Exception as e:
            orchestrator_connection.log_trace(
                f"Unexpected error killing {application_name} (PID {proc.pid}): {e}"
            )


def release_keys(orchestrator_connection: OrchestratorConnection) -> None:
    """Release Ctrl, Alt, and Shift keys if they are stuck."""

    orchestrator_connection.log_trace("Releasing Ctrl, Alt, and Shift keys.")
    # pylint: disable-next = import-outside-toplevel
    import ctypes

    try:
        # Use Windows API to release keys
        user32 = ctypes.windll.user32

        # Key codes
        keys_to_release = [
            0x11,  # VK_CONTROL
            0x10,  # VK_SHIFT
            0x12,  # VK_MENU (Alt)
            0x5B,  # VK_LWIN
            0x5C,  # VK_RWIN
            0xA2,  # VK_LCONTROL
            0xA3,  # VK_RCONTROL
            0xA0,  # VK_LSHIFT
            0xA1,  # VK_RSHIFT
            0xA4,  # VK_LMENU
            0xA5,  # VK_RMENU
        ]

        # Send key up events (0x0002 is KEYEVENTF_KEYUP)
        for key in keys_to_release:
            user32.keybd_event(key, 0, 0x0002, 0)

    # pylint: disable-next = broad-exception-caught
    except Exception as e:
        orchestrator_connection.log_error(f"Error releasing keys: {e}")
