# points/analog_input_point.py

import logging
from typing import Any, Dict
from .base_point import Point
from utils.unit_conversion import UnitConverter


class AnalogInputPoint(Point):
    def __init__(
        self,
        config: Dict[str, Any],
        ecy_client: Any,
        bop_client: Any,
        unit_converter: UnitConverter
    ):
        """
        Initializes an AnalogInputPoint instance.

        Args:
            config (Dict[str, Any]): Configuration dictionary for the point.
            ecy_client (Any): Instance of ECYDeviceClient to communicate with ECY devices.
            bop_client (Any): Instance of BOPTestClient to communicate with BOP devices.
            unit_converter (UnitConverter): Instance of UnitConverter for unit conversions.
        """
        super().__init__(config, ecy_client)
        self.bop_client = bop_client
        self.unit_converter = unit_converter
        self.pending_sync = False  # Initialize pending_sync status

    def process_bop_value(self, bop_value: float, metadata: Dict[str, Any]) -> None:
        """
        Processes the value received from BOPTest, performs unit conversion if needed, and stores the value.

        Args:
            bop_value (float): The raw value received from BOPTest.
            metadata (Dict[str, Any]): Additional metadata associated with the value.
        """
        logging.debug(f"Processing BOPTest value for point '{self.object_name}': {bop_value}")

        # Validate bop_value type
        if not isinstance(bop_value, (int, float)):
            logging.error(f"Invalid BOPTest value type for point '{self.object_name}': {bop_value}")
            return

        # Handle unit conversion based on configuration
        try:
            if self.convert_to_us:
                from_unit = self.unit  # e.g., 'ppm'
                to_unit = self.config.get('us_unit')  # e.g., 'ppm' (if same)
                if not to_unit:
                    logging.error(f"Point '{self.object_name}' has 'convert_to_us' set but no 'us_unit' configured.")
                    return
                # Perform conversion to US units
                converted_value = self.unit_converter.convert(bop_value, from_unit, to_unit)
                logging.debug(f"Converted BOPTest value for point '{self.object_name}': {converted_value} {to_unit}")
            else:
                # Convert to SI units if specified and different from 'unit'
                si_unit = self.config.get('si_unit')
                if si_unit and si_unit != self.unit:
                    from_unit = self.unit  # e.g., 'ppm'
                    to_unit = si_unit  # e.g., 'ppm' (if same)
                    converted_value = self.unit_converter.convert(bop_value, from_unit, to_unit)
                    logging.debug(f"Converted BOPTest value for point '{self.object_name}': {converted_value} {to_unit}")
                else:
                    # No conversion needed
                    converted_value = bop_value
                    logging.debug(f"No unit conversion needed for point '{self.object_name}'. Value: {converted_value} {self.unit}")
        except ValueError as e:
            logging.error(f"Unit conversion error for point '{self.object_name}': {e}")
            return

        # Store the converted value
        previous_value = self.value
        self.value = converted_value
        if previous_value != self.value:
            self.pending_sync = True  # Mark as pending sync
            logging.info(f"Point '{self.object_name}' value updated from {previous_value} to {self.value}. Marked for synchronization.")
        else:
            logging.debug(f"Point '{self.object_name}' value remains unchanged at {self.value}.")

    def has_pending_sync(self) -> bool:
        """
        Determines if there are pending synchronization tasks.

        Returns:
            bool: True if there's a pending sync, False otherwise.
        """
        logging.debug(f"Checking pending_sync for point '{self.object_name}': {self.pending_sync}")
        return self.pending_sync

    def prepare_batch_request(self) -> Dict[str, Any]:
        """
        Prepares the batch request payload for this AnalogInputPoint.

        Returns:
            Dict[str, Any]: A dictionary representing the batch request for this point.
        """
        if self.object_instance is None:
            logging.error(f"Object instance not assigned for point '{self.object_name}'. Cannot prepare batch request.")
            return {}

        if self.value is None:
            logging.warning(f"No value set for point '{self.object_name}', skipping in batch request.")
            return {}

        # Prepare two requests:
        # 1. Set "out-of-service" to True
        # 2. Set "present-value" to the converted value

        # Request to set "out-of-service" to True
        out_of_service_request = {
            "id": f"{self.object_name}_out_of_service",
            "method": "POST",
            "url": f"/api/rest/v2/services/bacnet/local/objects/analog-inputs/{self.object_instance}",
            "body": {
                    "out-of-service": True
            }
        }

        # Request to set "present-value"
        present_value_request = {
            "id": f"{self.object_name}_present_value",
            "method": "POST",
            "url": f"/api/rest/v2/services/bacnet/local/objects/analog-inputs/{self.object_instance}",
            "body": {
                "present-value": float(self.value)
            }
        }

        batch_request = {
            "requests": [out_of_service_request, present_value_request]
        }

        logging.debug(f"Prepared batch request for point '{self.object_name}': {batch_request}")
        return batch_request
        """
        Determines if the point has a new value to sync.

        Returns:
            bool: True if there's a new value to sync, False otherwise.
        """
        # Implement logic to determine if the point has a pending sync.
        # This could be based on a flag or timestamp of the last sync.
        # For simplicity, we'll assume every new value requires sync.
        return True