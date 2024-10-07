# points/binary_value_point.py

import logging
from typing import Any, Dict
from .base_point import Point

class BinaryValuePoint(Point):
    def __init__(
        self,
        config: Dict[str, Any],
        ecy_client: Any,
        bop_client: Any
    ):
        """
        Initializes a BinaryValuePoint instance.

        Args:
            config (Dict[str, Any]): Configuration dictionary for the point.
            ecy_client (Any): Instance of ECYDeviceClient to communicate with ECY devices.
            bop_client (Any): Instance of BOPTestClient to communicate with BOP devices.
        """
        super().__init__(config, ecy_client)
        self.bop_client = bop_client
        self.threshold = self.config.get('threshold')

        if self.threshold is None:
            logging.error(f"Threshold not defined for BinaryValuePoint '{self.object_name}'.")
            raise ValueError(f"Threshold not defined for BinaryValuePoint '{self.object_name}'.")

        if not isinstance(self.threshold, (int, float)):
            logging.error(f"Invalid threshold type for BinaryValuePoint '{self.object_name}': {self.threshold}")
            raise ValueError(f"Invalid threshold type for BinaryValuePoint '{self.object_name}': {self.threshold}")

        self.value = False  # Initialize with default binary value
        self.pending_sync = False  # Initialize pending_sync status

        logging.debug(f"Initialized BinaryValuePoint '{self.object_name}' with threshold {self.threshold}.")

    def process_bop_value(self, bop_value: float, metadata: Dict[str, Any]) -> None:
        """
        Processes the numerical value received from BOPTest and determines the binary status.

        Args:
            bop_value (float): The raw numerical value received from BOPTest.
            metadata (Dict[str, Any]): Additional metadata associated with the value.
        """
        logging.debug(f"Processing BOPTest value for point '{self.object_name}': {bop_value}")

        # Validate bop_value type
        if not isinstance(bop_value, (int, float)):
            logging.error(f"Invalid BOPTest value type for BinaryValuePoint '{self.object_name}': {bop_value}")
            return

        # Determine binary status based on threshold
        new_binary_value = bop_value > self.threshold
        logging.debug(f"BinaryValuePoint '{self.object_name}' evaluated to {new_binary_value} based on threshold {self.threshold}.")

        # Update the binary value if it has changed
        if self.value != new_binary_value:
            previous_value = self.value
            self.value = new_binary_value
            self.pending_sync = True  # Mark as pending sync
            logging.info(f"BinaryValuePoint '{self.object_name}' value updated from {previous_value} to {self.value}. Marked for synchronization.")
        else:
            logging.debug(f"BinaryValuePoint '{self.object_name}' value remains unchanged at {self.value}.")

    def has_pending_sync(self) -> bool:
        """
        Determines if there are pending synchronization tasks.

        Returns:
            bool: True if there's a pending sync, False otherwise.
        """
        logging.debug(f"Checking pending_sync for BinaryValuePoint '{self.object_name}': {self.pending_sync}")
        return self.pending_sync

    def prepare_batch_request(self) -> Dict[str, Any]:
        """
        Prepares the batch request payload for this BinaryValuePoint.

        Returns:
            Dict[str, Any]: A dictionary representing the batch request for this point.
        """
        if self.object_instance is None:
            logging.error(f"Object instance not assigned for BinaryValuePoint '{self.object_name}'. Cannot prepare batch request.")
            return {}

        present_value_request = {
            "id": f"{self.object_name}_present_value",
            "method": "POST",
            "url": f"/api/rest/v2/services/bacnet/local/objects/binary-values/{self.object_instance}",
            "body": {
                "present-value": self.value  # True or False
            }
        }

        batch_request = {
            "requests": [present_value_request]
        }

        logging.debug(f"Prepared batch request for BinaryvaluePoint '{self.object_name}': {batch_request}")
        return batch_request

    def reset_sync_flag(self) -> None:
        """
        Resets the pending_sync flag after successful synchronization.
        """
        logging.debug(f"Resetting pending_sync for BinaryvaluePoint '{self.object_name}'.")
        self.pending_sync = False