"""This module contains the main process of the robot."""

import json
from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection
from OpenOrchestrator.database.queues import QueueElement
from robot_framework.subprocesses.initalize import initalization_checks


# pylint: disable-next=unused-argument
def process(orchestrator_connection: OrchestratorConnection, queue_element: QueueElement | None = None) -> None:
    """Do the primary process of the robot."""

    orchestrator_connection.log_trace("Running process.")
    queue_element_data = json.loads(queue_element.data)

    orchestrator_connection.log_trace("Initalization checks.")
    initalization_checks(orchestrator_connection, queue_element_data)
