"""Create reminders for booking appointments based on patient age."""
from robot_framework.subprocesses.helper_functions import (
    future_dates
)


def create_booking_reminders(orchestrator_connection, queue_element_data, solteq_tand_db_object, is_patient_under_16):
    """
    Set booking reminders based on the patient's age.
    """
    booking_reminder_data = {
        "comboBoxBookingType": "Husk",
        "comboBoxDentist": " Frit valg",
        "comboBoxChair": "Frit valg",
        "dateTimePickerStartTime": "07:45",
        "textBoxDuration": "5",
        "comboBoxStatus": "Behovsaftale",
    }

    reminders = []
    orchestrator_connection.log_trace("Finding future dates for booking reminders.")
    future_dates_values = future_dates(queue_element_data["patient_cpr"])
    future_dates_modified = [dt.replace(hour=7, minute=45) for dt in future_dates_values]

    if is_patient_under_16:
        reminders.append(
            {
                **booking_reminder_data,
                "textBoxBookingText": "Frit valg fra 16 år",
                "futureDate": future_dates_values[0].strftime("%d-%m-%Y"),
                "futureDateTime": future_dates_modified[0]
                .strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            }
        )
        reminders.append(
            {
                **booking_reminder_data,
                "textBoxBookingText": "Arkiveres 22 år",
                "futureDate": future_dates_values[1].strftime("%d-%m-%Y"),
                "futureDateTime": future_dates_modified[1]
                .strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            }
        )
    else:
        reminders.append(
            {
                **booking_reminder_data,
                "textBoxBookingText": "Arkiveres 22 år",
                "futureDate": future_dates_values[1].strftime("%d-%m-%Y"),
                "futureDateTime": future_dates_modified[1]
                .strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            }
        )

    # Check if the booking reminder is already set, else create booking reminders.
    orchestrator_connection.log_trace("Checking for existing booking reminders.")
    for reminder in reminders:
        existing_reminders = solteq_tand_db_object.get_list_of_bookings(
            filters={
                "p.cpr": queue_element_data["patient_cpr"],
                "bt.Description": "Husk",
                "CONVERT(datetime2(0), b.StartTime)": reminder["futureDateTime"],
            }
        )
        if not existing_reminders:
            orchestrator_connection.log_trace(
                f"Creating booking reminder for {reminder['futureDate']}"
            )
            orchestrator_connection.solteq_tand_app.create_booking_reminder(reminder)
            orchestrator_connection.log_trace(
                f"Booking reminder for {reminder['futureDate']} created successfully."
            )
        else:
            orchestrator_connection.log_trace(
                f"Booking reminder for {reminder['futureDate']} already exists, skipping creation."
            )
