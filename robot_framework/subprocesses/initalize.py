from mbu_dev_shared_components.solteqtand.db_handler import SolteqTandDatabase
from robot_framework.exceptions import BusinessError


def get_exceptions(db_connection, process_id):
    import pyodbc

    conn = pyodbc.connect(db_connection)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                [exception_code]
                ,[message_text]
            FROM
                [RPA].[rpa].[BusinessExceptionMessages]
            WHERE
                [process_id] = ?
            """,
            (process_id,),
        )
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        return result
    finally:
        cursor.close()


def initalization_checks(orchestrator_connection, queue_element_data: dict) -> None:
    """
    Perform initialization checks for the process.

    Args:
        orchestrator_connection: A connection to OpenOrchestrator.

    Raises:
        BusinessError: If a business rule is broken.
    """
    solteq_tand_db_conn = orchestrator_connection.get_constant(
        "solteq_tand_db_connstr"
    ).value

    solteq_tand_db_obj = SolteqTandDatabase(solteq_tand_db_conn)

    rpa_db_conn = orchestrator_connection.get_constant(
        "rpa_db_connstr"
    ).value  # DbConnectionString

    def _check_primary_clinic_data(orchestrator_connection, queue_element_data) -> list:
        """Check if primary clinic is set."""
        orchestrator_connection.log_trace("Checking if primary clinic is set.")
        filter_params = {
            "p.cpr": queue_element_data["cpr"],
        }
        result = solteq_tand_db_obj.get_list_of_primary_dental_clinics(
            filters=filter_params
        )
        if not result:
            excp = get_exceptions(rpa_db_conn, queue_element_data["process_id"])
            message = [d for d in excp if d["exception_code"] == "1A"][0][
                "message_text"
            ]
            raise BusinessError(message)
        orchestrator_connection.log_info("Primary clinic is set.")
        return result

    def _check_extern_clinic_data(orchestrator_connection, queue_element_data) -> list:
        """Check if extern dentist information is set."""
        filter_params = {
            "p.cpr": queue_element_data["cpr"],
        }
        result = solteq_tand_db_obj.get_list_of_extern_dentist(filters=filter_params)

        # Check if extern dentist is set
        orchestrator_connection.log_trace("Checking if extern dentist is set...")
        if not result:
            excp = get_exceptions(rpa_db_conn, queue_element_data["process_id"])
            message = [d for d in excp if d["exception_code"] == "1B"][0][
                "message_text"
            ]
            raise BusinessError(message)
        orchestrator_connection.log_info("Extern dentist is set.")

        # Check if contractor id is set
        orchestrator_connection.log_trace("Checking if contractor id is set...")
        if not result[0].get("contractorId"):
            excp = get_exceptions(rpa_db_conn, queue_element_data["process_id"])
            message = [d for d in excp if d["exception_code"] == "1C"][0][
                "message_text"
            ]
            raise BusinessError(message)

        # Check if phonenumber is set
        orchestrator_connection.log_trace("Checking if phone number is set...")
        if not result[0].get("phoneNumber"):
            excp = get_exceptions(rpa_db_conn, queue_element_data["process_id"])
            message = [d for d in excp if d["exception_code"] == "1E"][0][
                "message_text"
            ]
            raise BusinessError(message)
        orchestrator_connection.log_info("Phone number is set.")
        return result

    def _check_extern_clinic_deal(orchestrator_connection, queue_element_data) -> None:
        """Check if extern clinic has a deal with Aarhus Kommune."""
        orchestrator_connection.log_trace(
            "Checking if extern clinic has a deal with Aarhus Kommune..."
        )
        filter_params = {
            "type": "3",
            "contractorId": orchestrator_connection.extern_clinic_data[0].get(
                "contractorId"
            ),
        }
        result = solteq_tand_db_obj.get_list_of_clinics(filters=filter_params)
        if not result:
            excp = get_exceptions(rpa_db_conn, queue_element_data["process_id"])
            message = [d for d in excp if d["exception_code"] == "1D"][0][
                "message_text"
            ]
            raise BusinessError(message)
        orchestrator_connection.log_info(
            "Extern clinic has a deal with Aarhus Kommune."
        )

    def _check_administrative_note(orchestrator_connection, queue_element_data) -> list:
        """Check if administrative note is set and returns the note."""
        orchestrator_connection.log_trace("Checking if administrative note is set...")
        filter_params = {
            "p.cpr": queue_element_data["cpr"],
            "dn.Beskrivelse": "%Besked til privat tandlæge - Frit valg%", #TODO: Evt. er notatet: Følgende oplysninger skal medsendes til privat tandlæge i forbindelse med udskrivning
        }
        result = solteq_tand_db_obj.get_list_of_journal_notes(
            filters=filter_params, order_by="ds.Dokumenteret", order_direction="DESC"
        )
        if not result:
            excp = get_exceptions(rpa_db_conn, queue_element_data["process_id"])
            message = [d for d in excp if d["exception_code"] == "1F"][0][
                "message_text"
            ]
            raise BusinessError(message)
        orchestrator_connection.log_info("Administrative note is set.")
        return result

    orchestrator_connection.primary_clinick_and_patient_data = (
        _check_primary_clinic_data(
            orchestrator_connection=orchestrator_connection,
            queue_element_data=queue_element_data,
        )
    )

    orchestrator_connection.extern_clinic_data = _check_extern_clinic_data(
        orchestrator_connection=orchestrator_connection,
        queue_element_data=queue_element_data,
    )

    _check_extern_clinic_deal(
        orchestrator_connection=orchestrator_connection,
        queue_element_data=queue_element_data,
    )

    orchestrator_connection.administrative_note = _check_administrative_note(
        orchestrator_connection=orchestrator_connection,
        queue_element_data=queue_element_data,
    )

    orchestrator_connection.log_info("Initialization checks completed.")



    
    # TODO: Findes ydernr. i EDI-Portalen
    # Husk Hasle torv

    # TODO: Hent:
    # - Patientinfo
    # - Privatklinikinfo
    # - Stamklinikinfo
    # - Administrationsnotat
