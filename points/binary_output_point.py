import logging
from typing import Any, Dict, Optional
from .base_point import Point

class BinaryOutputPoint(Point):
    OBJECT_TYPE_MAPPING = {
        "BinaryOutput": "binary-outputs",
        "BinaryInput": "binary-inputs",
        "BinaryValue": "binary-values",
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
            logging.error(f"BinaryOutputPoint '{self.object_name}' missing 'bop_point' in configuration.")
            raise ValueError("Missing 'bop_point' in configuration.")

        if not self.bop_override_point:
            logging.error(f"BinaryOutputPoint '{self.object_name}' missing 'bop_override_point' in configuration.")
            raise ValueError("Missing 'bop_override_point' in configuration.")

        if not self.ecy_point:
            logging.error(f"BinaryOutputPoint '{self.object_name}' missing 'ecy_point' in configuration.")
            raise ValueError("Missing 'ecy_point' in configuration.")

        if not self.object_type:
            logging.error(f"BinaryOutputPoint '{self.object_name}' missing 'object_type' in configuration.")
            raise ValueError("Missing 'object_type' in configuration.")

        # Get the object_instance number
        self.object_instance = self.ecy_client.get_instance_number(self.object_name, self.object_type)
        if self.object_instance is None:
            logging.error(f"Could not retrieve object_instance for point '{self.object_name}'.")
            raise ValueError(f"Invalid object_instance for point '{self.object_name}'.")

        self.value = False  # Initialize with default binary value (False)
        self.pending_sync = False  # Initialize pending_sync status

        logging.debug(f"Initialized BinaryOutputPoint '{self.object_name}' with bop_point '{self.bop_point}', "
                      f"bop_override_point '{self.bop_override_point}', ecy_point '{self.ecy_point}'.")

        # Initialize current value by fetching present-value from ECY
        self.current_value = self.fetch_present_value()

    def process_bop_value(self, bop_value: float, metadata: Dict[str, Any]) -> None:
        """
        Processes the BOPTest value and updates the point's value.

        Args:
            bop_value (float): The value received from BOPTest (expected to be 0 or 1).
            metadata (Dict[str, Any]): Additional metadata (optional).
        """
        logging.debug(f"Processing BOPTest value for point '{self.object_name}': {bop_value}")

        # Validate bop_value is binary (0 or 1)
        if bop_value not in [0, 1]:
            logging.error(f"Invalid BOPTest value for '{self.object_name}': {bop_value}. Expected 0 or 1.")
            return

        # Convert bop_value to boolean
        new_value = bool(bop_value)

        # Update the point's value
        previous_value = self.value
        self.value = new_value

        if previous_value != self.value:
            logging.info(f"Point '{self.object_name}' value updated from {previous_value} to {self.value}. Marked for synchronization.")
            self.pending_sync = True
        else:
            logging.debug(f"Point '{self.object_name}' value remains unchanged at {self.value}.")

    def has_pending_sync(self) -> bool:
        """
        Determines if there are pending synchronization tasks.

        Returns:
            bool: True if there's a pending sync, False otherwise.
        """
        logging.debug(f"Checking pending_sync for BinaryOutputPoint '{self.object_name}': {self.pending_sync}")
        return self.pending_sync
    
    def prepare_batch_request(self) -> Optional[Dict[str, Any]]:
        """
        Prepares the batch request payload for this BinaryOutputPoint.

        Returns:
            Optional[Dict[str, Any]]: The batch request payload or None if not applicable.
        """
        if not self.pending_sync or self.object_instance is None:
            logging.debug(f"No batch request needed for BinaryOutputPoint '{self.object_name}'.")
            return None

        # Construct the API endpoint URL
        object_type_kebab = self.get_object_type_kebab()
        url = f"/api/rest/v2/services/bacnet/local/objects/{object_type_kebab}/{self.object_instance}"

        # Prepare the batch request payload
        batch_request = {
            "id": f"{self.object_name}_present_value",
            "method": "POST",
            "url": url,
            "body": {
                "present-value": self.value  # True or False
            }
        }

        logging.debug(f"Prepared batch request for BinaryOutputPoint '{self.object_name}': {batch_request}")

        return {"requests": [batch_request]}
    
    def fetch_present_value(self) -> Optional[bool]:
        """
        Fetches the present-value from the ECY endpoint and maps it to a boolean.

        Returns:
            Optional[bool]: The present-value as True or False if available, else None.
        """
        logging.debug(f"Fetching present-value for BinaryOutputPoint '{self.object_name}' from ECY.")
        property_name = self.property_name  # Use the attribute
        present_value = self.ecy_client.get_property_value(
            object_type=self.object_type,
            object_instance=self.object_instance,
            property_name=property_name
        )
        logging.debug(f"Fetched present-value for '{self.object_name}': {present_value}")

        # Mapping logic
        if isinstance(present_value, bool):
            return present_value
        elif isinstance(present_value, str):
            present_value_lower = present_value.strip().lower()
            if present_value_lower == "active":
                return True
            elif present_value_lower == "inactive":
                return False
            else:
                logging.error(f"Unexpected present-value string for '{self.object_name}': '{present_value}'")
                return None
        elif isinstance(present_value, (int, float)):
            # Assuming any non-zero value is True, zero is False
            return bool(present_value)
        else:
            logging.error(f"Invalid present-value type for '{self.object_name}': {present_value}")
            return None

    def map_present_value_to_boptest(self, present_value: bool) -> int:
        """
        Maps ECY's present-value to BOPTest's expected value.

        Args:
            present_value (bool): The present-value from ECY.

        Returns:
            int: 1 if present_value is True, 0 if False.
        """
        mapped_value = 1 if present_value else 0
        logging.debug(f"Mapped present-value '{present_value}' to BOPTest value '{mapped_value}' for '{self.object_name}'.")
        return mapped_value

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
            logging.warning(f"Present-value for '{self.object_name}' is None or invalid. Skipping synchronization.")
            return {}  # Return empty dict to skip synchronization

        # Map present-value to BOPTest value (0 or 1)
        boptest_value = self.map_present_value_to_boptest(present_value)

        # Prepare the data for BOPTest, ensure both bop_point and bop_override_point are included
        boptest_data = {
            self.bop_point: boptest_value,  # Mapped value (0 or 1)
            self.bop_override_point: 1  # Always set the override to 1 to activate the override
        }

        logging.debug(f"Prepared BOPTest data for BinaryOutputPoint '{self.object_name}': {boptest_data}")
        return boptest_data

    def synchronize(self) -> Dict[str, Any]:
        """
        Performs synchronization for BinaryOutputPoint.

        Returns:
            Dict[str, Any]: Data to include in BOPTest's write call.
        """
        # Fetch and prepare data
        boptest_data = self.prepare_boptest_data()

        # If boptest_data is empty, skip synchronization
        if not boptest_data:
            logging.info(f"BinaryOutputPoint '{self.object_name}' synchronization skipped due to missing or invalid present-value.")
            return {}

        # Send data to BOPTest
        try:
            response = self.bop_client.write_values(boptest_data)
            if response.get('success'):
                logging.info(f"BinaryOutputPoint '{self.object_name}' synchronized successfully with BOPTest.")
                self.pending_sync = False  # Reset sync flag
            else:
                logging.error(f"Failed to synchronize BinaryOutputPoint '{self.object_name}' with BOPTest. Response: {response}")
        except Exception as e:
            logging.error(f"Error synchronizing BinaryOutputPoint '{self.object_name}' with BOPTest: {e}")

        return boptest_data

    def assign_object_instance(self, object_instance: int) -> None:
        """
        Assigns the object instance number to the point.

        Args:
            object_instance (int): The object instance number.
        """
        self.object_instance = object_instance
        logging.debug(f"Assigned object_instance={self.object_instance} to BinaryOutputPoint '{self.object_name}'.")