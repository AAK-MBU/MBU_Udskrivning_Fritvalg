"""This module contains configuration constants used across the framework"""

# The number of times the robot retries on an error before terminating.
MAX_RETRY_COUNT = 3

# Whether the robot should be marked as failed if MAX_RETRY_COUNT is reached.
FAIL_ROBOT_ON_TOO_MANY_ERRORS = True

# Error screenshot config
SMTP_SERVER = "smtp.adm.aarhuskommune.dk"
SMTP_PORT = 25
SCREENSHOT_SENDER = "robot@friend.dk"

# Constant/Credential names
ERROR_EMAIL = "Error Email"


# Queue specific configs
# ----------------------

# The name of the job queue (if any)
QUEUE_NAME = "tan.udskrivning0-21.main"

# The limit on how many queue elements to process
MAX_TASK_COUNT = 100

# ----------------------
SOLTEQ_TAND_APP_PATH = "C:\\Program Files (x86)\\TM Care\\TM Tand\\TMTand.exe"
TMP_FOLDER = "C:\\tmp\\tmt"
ROMEXIS_ROOT_PATH = r"\\SRVAPPROMEX04\romexis_images$"
