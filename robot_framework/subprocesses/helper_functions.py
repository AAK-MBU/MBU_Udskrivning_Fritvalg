""" Helper functions for subprocesses """
import os
import zipfile
from datetime import datetime


def cpr_to_birthdate(ssn: str) -> datetime:
    """Convert a Danish CPR number to a birthdate with the correct century."""
    if len(ssn) < 10:
        raise ValueError("CPR number must be at least 10 characters long")

    day = int(ssn[:2])
    month = int(ssn[2:4])
    year_suffix = int(ssn[4:6])
    personal_number = int(ssn[6:10])  # Last 4 digits

    # Determine the full year based on the serial number
    if 0 <= personal_number <= 4999:
        birth_year = 1900 + year_suffix  # 1900-1999
    elif 5000 <= personal_number <= 8999:
        if year_suffix >= 37:
            birth_year = 1900 + year_suffix  # 1937-1999
        else:
            birth_year = 2000 + year_suffix  # 2000-2036
    elif 9000 <= personal_number <= 9999:
        if year_suffix >= 00 and year_suffix <= 36:
            birth_year = 2000 + year_suffix  # 2000-2036
        else:
            birth_year = 1800 + year_suffix  # 1800-1899
    else:
        raise ValueError("Invalid CPR format: Personal number out of range")

    # Construct the birthdate
    return datetime(birth_year, month, day)


def future_dates(ssn: str) -> tuple:
    """Calculate the dates 16 and 22 years into the future from a CPR number."""
    birth_date = cpr_to_birthdate(ssn)
    date_16_years = birth_date.replace(year=birth_date.year + 16)
    date_22_years = birth_date.replace(year=birth_date.year + 22)
    return date_16_years, date_22_years


def is_under_16(ssn: str) -> bool:
    """Check if a person is under 16 years old."""
    birth_date = cpr_to_birthdate(ssn)
    today = datetime.now()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age < 16


def zip_folder_contents(folder_path: str, zip_filename: str) -> None:
    """
    Zips all files in the specified folder (non-recursive) into a .zip archive.

    Args:
        folder_path (str): Path to the folder containing files to zip.
        zip_filename (str): Full path (including .zip filename) for the output zip file.
    """
    try:
        with zipfile.ZipFile(zip_filename, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for filename in os.listdir(folder_path):
                full_path = os.path.join(folder_path, filename)
                if os.path.isfile(full_path):
                    zipf.write(full_path, arcname=filename)
    except Exception as e:
        print(f"Error zipping folder: {e}")
