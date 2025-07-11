"""Create an event in Solteq Tand if it has not been created yet."""


def create_event_if_not_created(orchestrator_connection, queue_element_data, solteq_tand_db_object):
    """
    Check if the event 'Afgang til klinik 751' is already processed for the patient.
    If not, process the event.
    """
    orchestrator_connection.log_trace(
        "Checking if the event 'Afgang til klinik 751' is already processed for the patient."
    )
    events = solteq_tand_db_object.get_list_of_events(
        filters={
            "p.cpr": queue_element_data["patient_cpr"],
            "e.currentStateText": "Afgang til klinik 751",
            "e.archived": 1,
        }
    )
    if not events:
        orchestrator_connection.log_trace(
            "Event 'Afgang til klinik 751' not found, proceeding to create it."
        )
        orchestrator_connection.solteq_tand_app.process_event()
        orchestrator_connection.log_trace(
            "Event 'Afgang til klinik 751' created successfully."
        )
    else:
        orchestrator_connection.log_trace(
            "Event 'Afgang til klinik 751' already exists, no action needed."
        )
