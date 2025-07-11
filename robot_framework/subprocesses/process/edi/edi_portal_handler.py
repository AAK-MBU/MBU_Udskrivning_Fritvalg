"""This module provides the EDI portal handler for processing EDI-related tasks."""

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import pyodbc
from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection

from robot_framework.subprocesses.process.edi import edi_portal_functions as edifuncs


# Context object to hold all inputs and intermediate state
@dataclass
class EdiContext:
    """
    EdiContext is a context object that holds all inputs and intermediate state
    required for processing in the EDI portal handler.

    Attributes:
        extern_clinic_data (Dict[str, Any]): External clinic data used in processing.
        queue_element (Dict[str, Any]): Queue element containing relevant information.
        journal_note (str): Note to be added to the journal.
        path_to_files_for_upload (str): Path to the files that need to be uploaded.
        subject (str): Subject of the context. Defaults to an empty string.
        receipt_path (Optional[str]): Path to the receipt file. Defaults to None.
    """

    extern_clinic_data: Dict[str, Any]
    queue_element: Dict[str, Any]
    path_to_files_for_upload: str
    subject: str = ""
    journal_note: str | None = None
    value_data: Dict[str, Any] | None = None
    receipt_path: Optional[str] | None = None


# A pipeline step is any callable that receives the context and operates on it
Step = Callable[[EdiContext], Optional[bool]]


def edi_portal_handler(
    context: EdiContext, orchestrator_connection: OrchestratorConnection
) -> Optional[str]:
    """
    Executes the end-to-end EDI portal workflow using a Context object.

    Steps are defined as functions (or lambdas) that take the shared context,
    enabling cleaner signatures and centralized state management.

    Args:
        context (EdiContext):
            Holds all input parameters and manages intermediate state such as
            computed subject lines and receipt paths.

    Returns:
        Optional[str]:
            Path to the renamed PDF receipt, or None on failure.
    """

    def get_constant(constant_name: str, conn_string: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single constant from the [RPA].[rpa].[Constants] table.

        Args:
            constant_name: Constant's [name] column value to match.
            conn_string:   ODBC connection string.

        Returns:
            A dict with ``{"name": ..., "value": ...}`` if the row exists,
            otherwise **None**.

        Raises:
            pyodbc.Error: Propagates any database errors.
        """
        query = """
            SELECT [name], [value]
            FROM   [RPA].[rpa].[Constants]
            WHERE  [name] = ?
        """

        with pyodbc.connect(conn_string) as conn:
            row = conn.cursor().execute(query, constant_name).fetchone()

        if row is None:
            return None

        return {"name": row.name, "value": row.value}

    conn_string = orchestrator_connection.get_constant("DbConnectionString").value
    constant = get_constant(
        constant_name=str("udskrivning_edi_portal_content"),
        conn_string=conn_string,
    )
    if constant is None:
        raise RuntimeError(
            "Constant 'udskrivning_edi_portal_content' not found in the database."
        )

    # Data til edi_portal_content
    context.value_data = (
        json.loads(constant["value"])
        if isinstance(constant["value"], str)
        else constant["value"]
    )

    patient_name = context.queue_element.get("patient_name")
    base_subject = context.value_data["edi_portal_content"]["subject"]

    context.subject = f"{base_subject} {patient_name}"

    # Define the ordered list of pipeline steps
    pipeline: List[Step] = [
        # Navigation
        lambda ctx: edifuncs.edi_portal_is_patient_data_sent(subject=ctx.subject),
        lambda ctx: edifuncs.edi_portal_go_to_send_journal(),
        lambda ctx: edifuncs.edi_portal_click_next_button(sleep_time=2),
        # Contractor lookup and selection
        lambda ctx: edifuncs.edi_portal_lookup_contractor_id(
            extern_clinic_data=ctx.extern_clinic_data
        ),
        lambda ctx: edifuncs.edi_portal_choose_receiver(
            extern_clinic_data=ctx.extern_clinic_data
        ),
        lambda ctx: edifuncs.edi_portal_click_next_button(sleep_time=2),
        # Add journal content
        lambda ctx: edifuncs.edi_portal_add_content(
            queue_element=ctx.queue_element,
            edi_portal_content=ctx.value_data["edi_portal_content"],
            journal_continuation_text=ctx.journal_note,
            extern_clinic_data=ctx.extern_clinic_data,
        ),
        lambda ctx: edifuncs.edi_portal_click_next_button(sleep_time=2),
        # File upload
        lambda ctx: edifuncs.edi_portal_upload_files(
            path_to_files=ctx.path_to_files_for_upload
        ),
        lambda ctx: edifuncs.edi_portal_click_next_button(sleep_time=2),
        # Priority & send
        # lambda ctx: edifuncs.edi_portal_choose_priority(),
        lambda ctx: edifuncs.edi_portal_click_next_button(sleep_time=2),
        lambda ctx: edifuncs.edi_portal_send_message(),
        # # Retrieve the sent receipt
        lambda ctx: setattr(
            ctx,
            "receipt_path",
            edifuncs.edi_portal_get_journal_sent_receip(subject=ctx.subject),
        ),
        # Rename the receipt on disk
        lambda ctx: setattr(
            ctx,
            "receipt_path",
            edifuncs.rename_file(
                file_path=ctx.receipt_path,  # type: ignore
                new_name=f"EDI Portal - {patient_name}",
                extension=".pdf",
            ),
        ),
    ]

    # Execute each step in sequence
    skip_steps = False
    for step in pipeline[:-2]:  # Exclude the last two steps from conditional skipping
        try:
            if skip_steps:
                print("Skipping step due to earlier condition.")
                continue

            if step(context):
                print(
                    "Step returned True, skipping remaining steps until the last two."
                )
                skip_steps = True
            else:
                print("Step returned False, continuing.")
        except Exception as e:
            raise RuntimeError(
                f"Step {step.__name__ if hasattr(step, '__name__') else step} failed: {e}"
            ) from e

    # Always run the last two steps
    for step in pipeline[-2:]:
        try:
            step(context)
        except Exception as e:
            raise RuntimeError(
                f"Step {step.__name__ if hasattr(step, '__name__') else step} failed: {e}"
            ) from e

    return context.receipt_path
