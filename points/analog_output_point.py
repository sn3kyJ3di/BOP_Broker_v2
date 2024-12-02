import logging
from typing import Any, Dict, Optional
from .base_point import Point

class AnalogOutputPoint(Point):
    OBJECT_TYPE_MAPPING = {
        "AnalogOutput": "analog-outputs",
        # Add other mappings as necessary
    }

    def __init__(
        self,
        config: Dict[str, Any],
        ecy_client: Any,
        bop_client: Any
    ):
        super().__init__(config, ecy_client)
        self.bop_client = bop_client

        # Extract necessary configurations
        self.bop_point = self.config.get('bop_point')
        self.bop_override_point = self.config.get('bop_override_point')
        self.ecy_point = self.config.get('ecy_point')
        self.object_type = self.config.get('object_type')
        self.object_name = self.ecy_point
        self.property_name = 'present-value'  # Added this line

        # Validate configurations
        if not self.bop_point:
            logging.error(f"AnalogOutputPoint '{self.object_name}' missing 'bop_point' in configuration.")
            raise ValueError("Missing 'bop_point' in configuration.")

        if not self.bop_override_point:
            logging.error(f"AnalogOutputPoint '{self.object_name}' missing 'bop_override_point' in configuration.")
            raise ValueError("Missing 'bop_override_point' in configuration.")

        if not self.ecy_point:
            logging.error(f"AnalogOutputPoint '{self.object_name}' missing 'ecy_point' in configuration.")
            raise ValueError("Missing 'ecy_point' in configuration.")

        if not self.object_type:
            logging.error(f"AnalogOutputPoint '{self.object_name}' missing 'object_type' in configuration.")
            raise ValueError("Missing 'object_type' in configuration.")

        # Get the object_instance number
        self.object_instance = self.ecy_client.get_instance_number(self.object_name, self.object_type)
        if self.object_instance is None:
            logging.error(f"Could not retrieve object_instance for point '{self.object_name}'.")
            raise ValueError(f"Invalid object_instance for point '{self.object_name}'.")

        self.current_value = None  # Initialize current value
        self.pending_sync = False  # Initialize pending_sync status

        logging.debug(f"Initialized AnalogOutputPoint '{self.object_name}' with bop_point '{self.bop_point}', "
                      f"bop_override_point '{self.bop_override_point}', ecy_point '{self.ecy_point}'.")

        # Initialize current value by fetching present-value from ECY
        self.current_value = self.fetch_present_value()

    def process_bop_value(self, bop_value: float, metadata: Dict[str, Any]) -> None:
        """
        Processes the BOPTest value and updates the point's value.

        Args:
            bop_value (float): The value received from BOPTest.
            metadata (Dict[str, Any]): Additional metadata (optional).
        """
        logging.debug(f"Processing BOPTest value for point '{self.object_name}': {bop_value}")

        # Update the point's value directly since no unit conversion is needed
        previous_value = self.current_value
        self.current_value = bop_value

        if previous_value != self.current_value:
            logging.info(f"Point '{self.object_name}' value updated from {previous_value} to {self.current_value}. Marked for synchronization.")
            self.pending_sync = True
        else:
            logging.debug(f"Point '{self.object_name}' value remains unchanged at {self.current_value}.")

    def fetch_present_value(self) -> Optional[float]:
        """
        Fetches the present-value from the ECY endpoint.

        Returns:
            Optional[float]: The present-value in the device's native units if available, else None.
        """
        logging.debug(f"Fetching present-value for point '{self.object_name}' from ECY.")

        # Define the property to fetch: "present-value"
        property_name = "present-value"
        present_value = self.ecy_client.get_property_value(
            object_type=self.object_type,
            object_instance=self.object_instance,
            property_name=property_name
        )
        logging.debug(f"Fetched present-value for point '{self.object_name}': {present_value}")
        return present_value  # Can be None

    def get_object_type_kebab(self) -> str:
        """
        Converts the object type to its kebab-case plural form as required by the API.

        Returns:
            str: Kebab-case plural object type.
        """
        return self.OBJECT_TYPE_MAPPING.get(self.object_type, self.object_type.lower())

    def prepare_boptest_data(self) -> Dict[str, Any]:
        """
        Prepares the data to send to BOPTest's advance call.

        Returns:
            Dict[str, Any]: A dictionary with bop_point and bop_override_point.
        """
        # Fetch present-value from ECY
        present_value = self.fetch_present_value()

        if present_value is None:
            logging.warning(f"'present-value' for '{self.object_name}' is None. Skipping synchronization.")
            return {}  # Return empty dict to skip synchronization

        try:
            # Normalize percentage value (0-100) to a decimal value (0-1)
            normalized_value = self.normalize_value(float(present_value))
        except (ValueError, TypeError) as e:
            logging.error(f"Invalid 'present-value' for '{self.object_name}': {e}. Skipping synchronization.")
            return {}  # Return empty dict to skip synchronization

        # Prepare the data for BOPTest
        boptest_data = {
            self.config['bop_point']: normalized_value,  # Normalized value (0 to 1)
            self.bop_override_point: int(1)  # Set override to 1 to indicate using normalized value
        }

        logging.debug(f"Prepared BOPTest data for AnalogOutputPoint '{self.object_name}': {boptest_data}")
        return boptest_data

    def normalize_value(self, percentage: float) -> float:
        """
        Normalizes the percentage value to a float between 0 and 1.

        Args:
            percentage (float): The percentage value (0-100).

        Returns:
            float: Normalized value between 0 and 1.
        """
        normalized = percentage / 100.0
        logging.debug(f"Normalized value for point '{self.object_name}': {normalized}")
        return normalized