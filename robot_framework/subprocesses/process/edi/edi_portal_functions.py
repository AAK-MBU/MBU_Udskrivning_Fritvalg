"""
This module contains functions to interact with the EDI portal.
These functions should be moved to mbu_dev_shared_components/solteqtand/application/edi_portal.py
"""
import locale
import re
import time
from datetime import datetime
from pathlib import Path

import pyodbc
import uiautomation as auto


def wait_for_control(
    control_type, search_params, search_depth=1, timeout=30, retry_interval=0.5
):
    """
    Waits for a given control type to become available with the specified search parameters.

    Args:
        control_type: The type of control, e.g., auto.WindowControl, auto.ButtonControl, etc.
        search_params (dict): Search parameters used to identify the control.
                            The keys must match the properties used in the control type, e.g., 'AutomationId', 'Name'.
        search_depth (int): How deep to search in the user interface.
        timeout (int): Maximum time to wait for the control, in seconds.
        retry_interval (float): Time to wait between retries, in seconds.

    Returns:
        Control: The control object if found, otherwise raises TimeoutError.

    Raises:
        TimeoutError: If the control is not found within the timeout period.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            print(f"Searching for control: {search_params} at depth {search_depth}")
            control = control_type(searchDepth=search_depth, **search_params)
            print(f"Control found: {control}")
            print(f"Control exists: {control.Exists(0, 0)}")
            if control.Exists(0, 0):
                print(f"Control found: {search_params}")
                return control
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error while searching for control: {e}")

        time.sleep(retry_interval)
        print(f"Retrying to find control: {search_params}...")

    print(f"Timeout reached while searching for control: {search_params}")
    raise TimeoutError(
        f"Control with parameters {search_params} was not found within the {timeout} second timeout."
    )


def wait_for_control_to_disappear(
    control_type, search_params, search_depth=1, timeout=30
):
    """
    Waits for a given control type to disappear with the specified search parameters.

    Args:
        control_type: The type of control, e.g., auto.WindowControl, auto.ButtonControl, etc.
        search_params (dict): Search parameters used to identify the control.
                            The keys must match the properties used in the control type, e.g., 'AutomationId', 'Name'.
        search_depth (int): How deep to search in the user interface.
        timeout (int): How long to wait, in seconds.

    Returns:
        bool: True if the control disappeared within the timeout period, otherwise False.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            control = control_type(searchDepth=search_depth, **search_params)
            if not control.Exists(0, 0):
                return True
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error while searching for control: {e}")

        time.sleep(0.5)
        print(f"Retrying to find control: {search_params}...")

    raise TimeoutError(
        f"Control with parameters {search_params} did not disappear within the timeout period."
    )


def edi_portal_check_contractor_id(extern_clinic_data: dict, sleep_time: int = 5) -> dict:
    """
    Checks if the contractor ID is valid in the EDI portal.

    Args:
        extern_clinic_data (dict): A dictionary containing the contractor ID and phone number.
        sleep_time (int): Time to wait after clicking the next button.

    Returns:
        dict: A dictionary containing the row count and whether the phone number matches.
    """
    try:
        # Handle Hasle Torv Clinic special case
        if extern_clinic_data[0]["contractorId"] == "477052" or extern_clinic_data[0]["contractorId"] == "470678":
            contractor_id = "485055"
            clinic_phone_number = "86135240"
        else:
            contractor_id = extern_clinic_data[0]["contractorId"]
            clinic_phone_number = extern_clinic_data[0]["phoneNumber"]

        edi_portal_click_next_button(sleep_time=2)

        class_options = [
            "form-control filter_search",
            "form-control filter_search valid",
        ]

        for class_name in class_options:
            try:
                search_box = wait_for_control(
                    auto.EditControl,
                    {"ClassName": class_name},
                    search_depth=22,
                    timeout=1,
                )
            except TimeoutError:
                continue
            if search_box:
                break

        search_box.SetFocus()
        search_box_value_pattern = search_box.GetPattern(auto.PatternId.ValuePattern)
        search_box_value_pattern.SetValue(contractor_id)
        search_box.SendKeys("{ENTER}")

        time.sleep(sleep_time)

        table_dentists = wait_for_control(
            auto.TableControl,
            {'AutomationId': 'table_id1'},
            search_depth=25,
        )
        grid_pattern = table_dentists.GetPattern(auto.PatternId.GridPattern)
        row_count = grid_pattern.RowCount

        is_phone_number_match = False

        if grid_pattern.GetItem(1, 0).Name == "Ingen data i tabellen":
            return {"rowCount": 0, "isPhoneNumberMatch": False}

        if row_count > 0:
            for row in range(row_count):
                phone_number = grid_pattern.GetItem(row, 4).Name
                if phone_number == clinic_phone_number:
                    is_phone_number_match = True
                    break
        return {"rowCount": row_count, "isPhoneNumberMatch": is_phone_number_match}
    except Exception as e:
        print(f"Error while checking contractor ID in EDI Portal: {e}")
        raise


def edi_portal_click_next_button(sleep_time: int) -> None:
    """
    Clicks the next button in the EDI portal.

    Args:
        sleep_time (int): Time to wait after clicking the next button.
    """
    try:
        edge_window = wait_for_control(
            auto.WindowControl, {"ClassName": "Chrome_WidgetWin_1"}, search_depth=3
        )

        edge_window.SetFocus()

        try:
            next_button = wait_for_control(
                edge_window.ButtonControl, {"Name": "Næste"},
                search_depth=50,
                timeout=5
            )
        except TimeoutError:
            next_button = None

        if not next_button:
            try:
                next_button = wait_for_control(
                    edge_window.ButtonControl, {"AutomationId": "patientInformationNextButton"},
                    search_depth=50,
                    timeout=5
                )
            except TimeoutError:
                next_button = None

        if not next_button:
            raise RuntimeError("Next button not found in EDI Portal")
        next_button.Click(simulateMove=False, waitTime=0)
        time.sleep(sleep_time)
    except Exception as e:
        print(f"Error while clicking next button in EDI Portal: {e}")
        raise


def edi_portal_lookup_contractor_id(extern_clinic_data: dict) -> None:
    """
    Looks up the contractor ID in the EDI portal.

    Args:
        extern_clinic_data (dict): A dictionary containing the contractor ID and phone number.
    """
    try:
        if extern_clinic_data[0]["contractorId"] == "477052" or extern_clinic_data[0]["contractorId"] == "470678":
            contractor_id = "485055"
        else:
            contractor_id = extern_clinic_data[0]["contractorId"]

        class_options = [
            "form-control filter_search",
            "form-control filter_search valid",
        ]

        for class_name in class_options:
            try:
                search_box = wait_for_control(
                    auto.EditControl,
                    {"ClassName": class_name},
                    search_depth=22,
                    timeout=1,
                )
            except TimeoutError:
                continue
            if search_box:
                break

        search_box.SetFocus()
        search_box_value_pattern = search_box.GetPattern(auto.PatternId.ValuePattern)
        search_box_value_pattern.SetValue(contractor_id)
        search_box.SendKeys("{ENTER}")
    except Exception as e:
        print(f"Error while looking up contractor ID in EDI Portal: {e}")
        raise


def edi_portal_choose_receiver(extern_clinic_data: dict) -> None:
    """
    Chooses the receiver in the EDI portal based on a matching phone number.

    Args:
        extern_clinic_data (dict): A dictionary containing the contractor ID and phone number.
    """
    try:
        if extern_clinic_data[0]["contractorId"] == "477052" or extern_clinic_data[0]["contractorId"] == "470678":
            clinic_phone_number = "86135240"
        else:
            clinic_phone_number = extern_clinic_data[0]["phoneNumber"]

        table_dentists = wait_for_control(
            auto.TableControl,
            {"AutomationId": "table_id1"},
            search_depth=25,
        )
        grid_pattern = table_dentists.GetPattern(auto.PatternId.GridPattern)
        row_count = grid_pattern.RowCount

        if row_count > 0:
            for row in range(row_count):
                phone_number = grid_pattern.GetItem(row, 4).Name
                if phone_number == clinic_phone_number:
                    grid_pattern.GetItem(row, 0).Click(simulateMove=False, waitTime=0)
                    break
    except Exception as e:
        print(f"Error while choosing receiver in EDI Portal: {e}")
        raise


def edi_portal_add_content(
    queue_element: dict,
    edi_portal_content: dict,
    extern_clinic_data: dict,
    journal_continuation_text: str | None = None,
) -> None:
    """
    Adds content to the EDI portal based on the provided queue element and content template.

    Args:
        queue_element (dict): The queue element containing data for the content.
        edi_portal_content (dict): The content template for the EDI portal.
        journal_continuation_text (str | None): Additional text to be added to the content.
    """

    def _get_formatted_date(data) -> str:
        """
        Helper function to format the date from the data dictionary.
        Args:
            data (dict): The data dictionary containing the date information.
        Returns:
            str: The formatted date string or an error message.
        """
        try:
            locale.setlocale(locale.LC_TIME, "da_DK.UTF-8")
        except locale.Error:
            return "Error setting locale to Danish"

        print(f"{data=}")
        if data.get("ukendt_dato") is True:
            return "Ukendt"

        try:
            date_str = data["dateOfExamination"]
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%B %Y").capitalize()
        except (ValueError, KeyError):
            return "Error parsing date"

    subject = edi_portal_content["subject"]

    if not subject:
        raise ValueError("Subject is required.")

    if extern_clinic_data[0]["contractorId"] == "477052":
        subject = subject + " på Tandklinikken Hasle Torv " + queue_element.get("patient_name")
    elif extern_clinic_data[0]["contractorId"] == "470678":
        subject = subject + " på Tandklinikken Brobjergparken " + queue_element.get("patient_name")
    else:
        subject = subject + " " + queue_element.get("patient_name")

    body = edi_portal_content["body"]
    if not body:
        raise ValueError("Body is required.")

    examination_date = _get_formatted_date(data=queue_element)
    risk_profile_map = {0: "Grøn", 1: "Gul", 2: "Rød", 3: "Ukendt"}
    risc_profile = risk_profile_map.get(
        queue_element.get("riskProfil")
    )
    dental_plan = queue_element.get("tandplejeplan", "Ukendt")

    body_modified = re.sub(r"@examinationDate", examination_date, body)
    body_modified = re.sub(r"@riscProfile", risc_profile, body_modified)
    if journal_continuation_text:
        if "Besked til privat tandlæge - Frit valg: " in journal_continuation_text:
            journal_continuation_text = journal_continuation_text.replace(
                "Besked til privat tandlæge - Frit valg: ", ""
            )
        elif (
            "Følgende oplysninger skal medsendes til privat tandlæge i forbindelse med udskrivning: "
            in journal_continuation_text
        ):
            journal_continuation_text = journal_continuation_text.replace(
                "Følgende oplysninger skal medsendes til privat tandlæge i forbindelse med udskrivning: ",
                "",
            )

    if dental_plan:
        body_modified = re.sub(
            r"@dentalPlan",
            f"Anden information: {journal_continuation_text}",
            body_modified,
        )
    else:
        body_modified = re.sub(r"@dentalPlan", "", body_modified)

    print(f"Modified body: {body_modified}")

    try:
        root_web_area = wait_for_control(
            auto.DocumentControl, {"AutomationId": "RootWebArea"}, search_depth=14
        )

        subject_field = wait_for_control(
            root_web_area.EditControl,
            {"AutomationId": "ContentTitleInput"},
            search_depth=50,
        )
        subject_field_value_pattern = subject_field.GetPattern(
            auto.PatternId.ValuePattern
        )
        subject_field_value_pattern.SetValue(subject)

        body_field = wait_for_control(
            root_web_area.EditControl, {"AutomationId": "ContentInput"}, search_depth=50
        )
        body_field_value_pattern = body_field.GetPattern(auto.PatternId.ValuePattern)
        body_field_value_pattern.SetValue(body_modified)

    except Exception as e:
        print(f"Error while adding content in EDI Portal: {e}")
        raise


def edi_portal_upload_files(path_to_files: str) -> None:
    """
    Uploads files to the EDI portal.
    """
    upload_field = wait_for_control(
        auto.GroupControl, {"AutomationId": "createNewUpload"}, search_depth=50
    )
    upload_field.Click(simulateMove=False, waitTime=0)

    upload_dialog = wait_for_control(
        auto.WindowControl, {"Name": "Åbn"}, search_depth=5
    )

    upload_dialog_path_field = wait_for_control(
        upload_dialog.EditControl, {"ClassName": "Edit"}, search_depth=5
    )
    upload_dialog_value_pattern = upload_dialog_path_field.GetPattern(
        auto.PatternId.ValuePattern
    )
    upload_dialog_value_pattern.SetValue(path_to_files)
    upload_dialog.SendKeys("{ENTER}")

    root_web_area = wait_for_control(
        auto.DocumentControl, {"AutomationId": "RootWebArea"}, search_depth=14
    )

    element_gone = False
    timeout = 180  # Set a timeout for the upload progress check
    while not element_gone and timeout > 0:
        try:
            upload_progress = wait_for_control(
                root_web_area.TextControl,
                {
                    "Name": "En eller flere filer er under behandling. Du kan fortsætte til næste trin, når arbejdet er færdigt."
                },
                search_depth=20,
                timeout=5,
            )
            if upload_progress:
                time.sleep(5)
                timeout -= 5
                print(f"{timeout=}")
                print("Waiting for upload to finish...")
            else:
                element_gone = True
                print("Upload finished.")
        except TimeoutError:
            element_gone = True
            print("Upload progress element not found, assuming upload finished.")


def edi_portal_choose_priority(priority: str = "Rutine") -> None:
    """
    Chooses the priority in the EDI portal.

    Args:
        priority (str): The priority to be set.
    """
    try:
        priority_field = wait_for_control(
            auto.RadioButtonControl,
            {"Name": f"{priority}"},
            search_depth=21,
        )
        priority_field.Click(simulateMove=False, waitTime=0)
    except Exception as e:
        print(f"Error while choosing priority in EDI Portal: {e}")
        raise


def edi_portal_send_message() -> None:
    """
    Sends a message in the EDI portal.
    """
    try:
        root_web_area = wait_for_control(
            auto.DocumentControl, {"AutomationId": "RootWebArea"}, search_depth=14
        )

        send_message_button = wait_for_control(
            root_web_area.ButtonControl,
            {"AutomationId": "submitButton"},
            search_depth=4,
        )
        send_message_button.Click(simulateMove=False, waitTime=0)
        print("Message sent successfully.")
    except Exception as e:
        print(f"Error while sending message in EDI Portal: {e}")
        raise


def edi_portal_get_journal_sent_receip(subject: str) -> str:
    """
    Checks if the message was sent successfully in the EDI portal,
    and downloads the receipt.

    Args:
        subject (str): The subject of the message to check.

    Raises:
        RuntimeError: If the message was not sent successfully.
    """
    try:
        root_web_area = wait_for_control(
            auto.DocumentControl, {"AutomationId": "RootWebArea"}, search_depth=14
        )

        table_post_messages = wait_for_control(
            auto.TableControl,
            {"AutomationId": "table_id1"},
            search_depth=50
        )
        grid_pattern = table_post_messages.GetPattern(auto.PatternId.GridPattern)
        row_count = grid_pattern.RowCount
        success_message = False
        if row_count > 0:
            for row in range(1, row_count):
                message = grid_pattern.GetItem(row, 5).Name
                print(f"Message: {message}")
                print(f"Message check: {subject == message}")
                if subject == message:
                    success_message = True
                    menu_button = grid_pattern.GetItem(row, 10)
                    break

        if success_message:
            print("Message sent successfully.")
        else:
            print("Message not sent.")
            raise RuntimeError("Message not sent.")

        menu_button.Click(simulateMove=False, waitTime=0)
        menu_popup = wait_for_control(
            root_web_area.ListControl,
            {"ClassName": "dropdown-menu show"},
            search_depth=14,
        )
        menu_popup_item = wait_for_control(
            menu_popup.ListItemControl,
            {"Name": " Gem"},
            search_depth=50,
        )
        menu_popup_item.SetFocus()
        pos = menu_popup_item.GetClickablePoint()
        auto.MoveTo(
            pos[0], pos[1], moveSpeed=0.5, waitTime=0
        )
        menu_popup_item_save = wait_for_control(
            menu_popup.HyperlinkControl,
            {"Name": "Gem som PDF"},
            search_depth=50,
        )
        menu_popup_item_save.Click(simulateMove=False, waitTime=0)

        download_path = Path.home() / "Downloads"
        timeout = 60  # Timeout period in seconds
        start_time = time.time()

        while time.time() - start_time < timeout:
            receipt = next(download_path.glob("Meddelelse*.pdf"), None)
            if receipt is not None:
                print(f"Receipt downloaded: {receipt}")
                return receipt
            print("Waiting for receipt to download...")
            time.sleep(1)

        raise FileNotFoundError("No file starting with 'Meddelelse' and ending with '.pdf' was found within the timeout period.")

    except Exception as e:
        print(f"Error while downloading the receipt from EDI Portal: {e}")
        raise


def rename_file(file_path: str, new_name: str, extension: str) -> str:
    """
    Renames a file and returns its new path.

    Args:
        file_path (str): Full path to the file to rename.
        new_name   (str): New filename without extension.
        extension  (str): New extension (e.g. '.pdf').

    Returns:
        str: Absolute path to the renamed file.

    Raises:
        FileNotFoundError: If the source file does not exist.
        OSError:           If the rename operation fails.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    new_file_path = path.parent / f"{new_name}{extension}"
    path.rename(new_file_path)
    return str(new_file_path)


def get_constants(conn_string: str, name: str) -> list:
    """Retrieve the constants from the database."""
    try:
        query = """
            SELECT
                *
            FROM
                [RPA].[rpa].[Constants]
            WHERE
                [name] = ?
        """
        params = (name,)

        with pyodbc.connect(conn_string) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                columns = [column[0] for column in cursor.description]
                constant_value = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return constant_value
    except pyodbc.Error as e:
        print(f"Database error: {e}")
        raise
    except Exception as e:
        print(f"Error retrieving constants: {e}")
        raise


def edi_portal_is_patient_data_sent(subject: str) -> bool:
    """
    Checks if the patient data has been sent in the EDI portal.

    Returns:
        bool: True if the patient data has been sent, False otherwise.
    """
    try:
        url_field = wait_for_control(
            auto.EditControl,
            {"Name": "Adresse- og søgelinje"},
            search_depth=25
        )
        url_field_value_pattern = url_field.GetPattern(auto.PatternId.ValuePattern)
        url_field_value_pattern.SetValue("https://ediportalen.dk/Messages/Sent")
        url_field.SendKeys("{ENTER}")

        time.sleep(5)

        test = wait_for_control(
            auto.WindowControl,
            {"ClassName": "Chrome_WidgetWin_1"},
            search_depth=3
        )

        test.SetFocus()
        next_test = wait_for_control(
            test.PaneControl,
            {"ClassName": "BrowserRootView"},
            search_depth=4
        )

        table_post_messages = wait_for_control(
            next_test.TableControl,
            {"AutomationId": "table_id1"},
            search_depth=23
        )
        grid_pattern = table_post_messages.GetPattern(auto.PatternId.GridPattern)
        row_count = grid_pattern.RowCount
        success_message = False

        if row_count > 0:
            for row in range(1, row_count):
                message = grid_pattern.GetItem(row, 5).Name
                print(f"{subject=}, {message=}")
                if subject == message:
                    success_message = True
                    break

        print(f"{success_message=}")
        if success_message:
            print("Message has already been sent.")
            return True

        return False
    except TimeoutError:
        return False
    except Exception as e:
        print(f"Error while checking if patient data is sent in EDI Portal: {e}")
        raise


def edi_portal_go_to_send_journal() -> None:
    """
    Navigates to the 'Opret ny journalforsendelse' section in the EDI portal.
    """
    try:
        url_field = wait_for_control(
            auto.EditControl,
            {"Name": "Adresse- og søgelinje"},
            search_depth=25
        )
        url_field_value_pattern = url_field.GetPattern(auto.PatternId.ValuePattern)
        url_field_value_pattern.SetValue("https://ediportalen.dk/Journal/Create")
        url_field.SendKeys("{ENTER}")
    except Exception as e:
        print(f"Error while navigating to 'Send journal' in EDI Portal: {e}")
        raise
