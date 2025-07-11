"""Update patient information based on age and clinic preferences."""


def update_patient_info(orchestrator_connection, is_patient_under_16):
    """
    Update the patient's status, primary clinic, and primary dentist based on age.
    Returns the template name and discharge document filename.
    """
    # Set values based on the patient's age.
    if is_patient_under_16:
        status = "Frit valg 0-15 år"
        discharge_document_filename = "Udskrivning til privat praksis 0-15 år"
    else:
        status = "Frit valg fra 16 år"
        discharge_document_filename = "Udskrivning til privat praksis fra 16 år"

    # Change status if needed.
    orchestrator_connection.log_trace(
        f"Checking if the patient status needs to be updated to '{status}'."
    )
    if orchestrator_connection.primary_clinick_and_patient_data[0]["patientStatus"] != status:
        orchestrator_connection.log_trace(
            f"Patient status is '{orchestrator_connection.primary_clinick_and_patient_data[0]['patientStatus']}', updating to '{status}'."
        )
        orchestrator_connection.solteq_tand_app.change_status(status=status)
    else:
        orchestrator_connection.log_trace(
            f"Patient status is already '{status}', no update needed."
        )

    # Change primary clinic if not already set.
    orchestrator_connection.log_trace(
        "Checking if the primary clinic needs to be updated."
    )
    default_clinic_name = "Tandplejen Aarhus"
    if orchestrator_connection.primary_clinick_and_patient_data[0]["preferredDentalClinicName"] != default_clinic_name:
        orchestrator_connection.log_trace(
            f"Primary clinic is '{orchestrator_connection.primary_clinick_and_patient_data[0]['preferredDentalClinicName']}', updating to '{default_clinic_name}'."
        )
        orchestrator_connection.solteq_tand_app.change_primary_clinic(
            current_primary_clinic=orchestrator_connection.primary_clinick_and_patient_data[0]['preferredDentalClinicName'],
            is_field_locked=orchestrator_connection.primary_clinick_and_patient_data[0]["isPreferredDentalClinicLocked"],
        )
    else:
        orchestrator_connection.log_trace(
            f"Primary clinic is already '{default_clinic_name}', no update needed."
        )

    # Change primary dentist if not already set.
    orchestrator_connection.log_trace(
        "Checking if the primary dentist needs to be updated."
    )
    default_clinician_name = " Frit valg"
    if orchestrator_connection.primary_clinick_and_patient_data[0]["clinicianName"] != default_clinician_name:
        orchestrator_connection.log_trace(
            f"Primary dentist is '{orchestrator_connection.primary_clinick_and_patient_data[0]['clinicianName']}', updating to '{default_clinician_name}'."
        )
        orchestrator_connection.solteq_tand_app.change_primary_patient_dentist(new_value=default_clinician_name)
    else:
        orchestrator_connection.log_trace(
            f"Primary dentist is already '{default_clinician_name}', no update needed."
        )

    return discharge_document_filename
