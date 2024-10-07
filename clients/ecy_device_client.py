# ecy_device_client.py

import requests
import logging
import threading
import urllib3
import base64
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import pytz

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ECYDeviceClient:
    # Mapping from object_type to its kebab-case plural form used in URLs
    OBJECT_TYPE_MAPPING = {
        "AnalogOutput": "analog-outputs",
        "AnalogInput": "analog-inputs",
        "AnalogValue": "analog-values",
        "BinaryOutput": "binary-outputs",
        "BinaryInput": "binary-inputs",
        "BinaryValue": "binary-values",
        # Add other mappings as necessary
    }

    def __init__(self, device_ip_address: str, device_username: str, device_password: str):
        self.device_ip_address = device_ip_address
        self.device_username = device_username
        self.device_password = device_password
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification; enable in production
        self.session.auth = (self.device_username, self.device_password)
        self.device_cookies: Dict[str, str] = {}
        self.lock = threading.Lock()
        self.endpoints_by_name: Dict[str, Any] = {}
        self.get_existing_endpoints()  # Fetch endpoints during initialization

    def disable_ntp(self) -> bool:
        """
        Disables NTP on the ECY device.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        url = f"https://{self.device_ip_address}/api/rest/v2/services/platform/time/ntp"
        headers = {"Content-Type": "application/json"}
        payload = {"enabled": False}
        logging.debug(f"Attempt Sending request to {url} with payload: {payload}")
        with self.lock:
            try:
                response = self.session.post(url, headers=headers, json=payload, verify=self.session.verify)
                response.raise_for_status()
                logging.info(f"NTP Disable successful for device {self.device_ip_address}. Status Code: {response.status_code}")
                return True
            except requests.RequestException as e:
                logging.error(f"NTP Disable failed for device {self.device_ip_address}")
                if hasattr(e, 'response') and e.response is not None:
                    logging.error(f"Response status code: {e.response.status_code}")
                    logging.error(f"Response content: {e.response.content}")
                return False

    def set_time_and_timezone(self, timezone: str, unix_time: int) -> bool:
        """
        Sets the timezone and date-time on the ECY device.
        
        Args:
            timezone (str): Desired timezone (e.g., "America/New_York").
            unix_time (int): Start time in Unix time.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        # Convert Unix time to datetime in specified timezone
        tz = pytz.timezone(timezone)
        dt = datetime.fromtimestamp(unix_time, tz)
        # Format datetime as "YYYY-MM-DDTHH:MM:SS"
        date_time_str = dt.strftime("%Y-%m-%dT%H:%M:%S")
            
        url = f"https://{self.device_ip_address}/api/rest/v2/services/platform/time"
        headers = {"Content-Type": "application/json"}
        payload = {"time-zone": timezone,
        "date-time": date_time_str}

        logging.debug(f"Attempt Sending request to {url} with payload: {payload}")

        with self.lock:
            try:
                response = self.session.post(url, headers=headers, json=payload, verify=self.session.verify)
                response.raise_for_status()
                logging.info(f"Time and timezone set on ECY device {self.device_ip_address}.")
                return True
            except requests.RequestException as e:
                logging.error(f"Failed to set time and timezone on ECY device {self.device_ip_address}: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logging.error(f"Response status code: {e.response.status_code}")
                    logging.error(f"Response content: {e.response.content}")
                return False
                
    def get_existing_endpoints(self) -> None:
        query_params = (
            "?$select="
            "analog-values($select=*($select=object-name,object-identifier)),"
            "binary-values($select=*($select=object-name,object-identifier)),"
            "analog-inputs($select=*($select=object-name,object-identifier)),"
            "binary-inputs($select=*($select=object-name,object-identifier)),"
            "analog-outputs($select=*($select=object-name,object-identifier)),"
            "binary-outputs($select=*($select=object-name,object-identifier))"
        )

        url = f"https://{self.device_ip_address}/api/rest/v2/services/bacnet/local/objects{query_params}"
        headers = {"Content-Type": "application/json"}

        with self.lock:
            if self.device_ip_address in self.device_cookies:
                logging.debug("Using stored cookie for authentication.")
                headers["Cookie"] = self.device_cookies[self.device_ip_address]
            else:
                logging.debug("Using basic authentication.")
                credentials = f"{self.device_username}:{self.device_password}"
                base64_credentials = base64.b64encode(credentials.encode()).decode()
                headers["Authorization"] = f"Basic {base64_credentials}"

        try:
            response = self.session.get(url, headers=headers, verify=self.session.verify)
            response.raise_for_status()

            # Store the cookie from the response if available
            with self.lock:
                if 'Set-Cookie' in response.headers:
                    cookie_value = response.headers['Set-Cookie']
                    self.device_cookies[self.device_ip_address] = cookie_value
                    logging.debug(f"Stored cookie for {self.device_ip_address}: {cookie_value}")

            # The response will be a nested JSON with the selected objects
            data = response.json()
            logging.debug(f"Received response from {self.device_ip_address}: {data}")

            # Initialize an empty list to store all endpoints
            endpoints = []

            # Iterate over each object type in the response
            for object_type_key, object_type_data in data.items():
                # object_type_data is a dictionary where keys are instance numbers
                for instance_data in object_type_data.values():
                    # Extract the object name and identifier
                    if 'object-name' in instance_data and 'object-identifier' in instance_data:
                        endpoints.append(instance_data)

            # Process endpoints to create a mapping of point names to their details
            self.endpoints_by_name = {
                endpoint["object-name"]: endpoint for endpoint in endpoints
            }
            logging.info(
                f"Fetched {len(self.endpoints_by_name)} endpoints from {self.device_ip_address} using a single API call."
            )

        except requests.RequestException as e:
            logging.error(f"Error fetching endpoints from {self.device_ip_address}: {e}")
            if e.response is not None:
                logging.error(f"Response status code: {e.response.status_code}")
                logging.error(f"Response content: {e.response.content}")
                # If unauthorized, remove stored cookie so that next time Basic Auth is used
                if e.response.status_code == 401:
                    with self.lock:
                        if self.device_ip_address in self.device_cookies:
                            del self.device_cookies[self.device_ip_address]
                            logging.info(f"Removed stored cookie for {self.device_ip_address} due to unauthorized access.")
            logging.debug("Completed fetching existing endpoints.")

    def get_instance_number(self, object_name: str, object_type: str) -> Optional[int]:
        """
        Retrieves the instance number for a given object name and type.

        Args:
            object_name (str): Name of the ECY object.
            object_type (str): Type of the ECY object (e.g., "AnalogInput").

        Returns:
            Optional[int]: Instance number if found, else None.
        """
        endpoint = self.endpoints_by_name.get(object_name)
        if endpoint:
            # Access 'object-type' within 'object-identifier'
            object_type_in_endpoint = endpoint.get("object-identifier", {}).get("object-type", "").lower()
            if object_type_in_endpoint == object_type.lower():
                object_identifier = endpoint.get("object-identifier", {})
                instance_number = object_identifier.get("object-instance")
                if instance_number is not None:
                    logging.debug(f"Found instance number {instance_number} for '{object_name}' of type '{object_type}'.")
                    return instance_number
                else:
                    logging.error(f"No 'object-instance' found for '{object_name}' of type '{object_type}'.")
            else:
                actual_type = endpoint.get("object-identifier", {}).get("object-type", "")
                logging.error(f"Object type mismatch for '{object_name}': expected '{object_type}', found '{actual_type}'.")
        else:
            logging.error(f"Object '{object_name}' not found in endpoints.")

        return None

    def get_property_value(self, object_type: str, object_instance: int, property_name: str) -> Optional[Any]:
        """
        Retrieves the value of a specific property from the ECY device.

        Args:
            object_type (str): The type of the object (e.g., 'AnalogInput').
            object_instance (int): The instance number of the object.
            property_name (str): The property to retrieve (e.g., 'present-value').

        Returns:
            Optional[Any]: The value of the property, or None if not found or on failure.
        """
        # Convert object_type to kebab-case plural as required by the API
        object_type_kebab = self.OBJECT_TYPE_MAPPING.get(object_type)
        if not object_type_kebab:
            logging.error(f"Unknown object type: {object_type}. Cannot construct URL for property retrieval.")
            return None

        url = f"https://{self.device_ip_address}/api/rest/v2/services/bacnet/local/objects/{object_type_kebab}/{object_instance}/{property_name}"
        headers = {"Content-Type": "application/json"}

        logging.debug(f"Fetching property '{property_name}' for {object_type} instance {object_instance} from ECY.")
        logging.debug(f"Constructed URL: {url}")

        with self.lock:
            if self.device_ip_address in self.device_cookies:
                logging.debug("Using stored cookie for property retrieval.")
                headers["Cookie"] = self.device_cookies[self.device_ip_address]
            else:
                logging.debug("Using basic authentication for property retrieval.")
                credentials = f"{self.device_username}:{self.device_password}"
                base64_credentials = base64.b64encode(credentials.encode()).decode()
                headers["Authorization"] = f"Basic {base64_credentials}"

        try:
            response = self.session.get(url, headers=headers, verify=self.session.verify)
            response.raise_for_status()
            json_response = response.json()
            
            # Fetch the value using '$value' key
            property_value = json_response.get('$value') if '$value' in json_response else json_response.get('value')
            logging.debug(f"Retrieved '{property_name}' for {object_type} {object_instance}: {property_value}")
            return property_value
        except requests.RequestException as e:
            logging.error(f"Failed to retrieve '{property_name}' for {object_type} {object_instance}: {e}")
            if e.response is not None:
                logging.error(f"Response status code: {e.response.status_code}")
                logging.error(f"Response content: {e.response.content}")
                # If unauthorized, remove stored cookie so that next time Basic Auth is used
                if e.response.status_code == 401:
                    with self.lock:
                        if self.device_ip_address in self.device_cookies:
                            del self.device_cookies[self.device_ip_address]
                            logging.info(f"Removed stored cookie for {self.device_ip_address} due to unauthorized access.")
            return None

    def read_values_from_endpoints(self, points: List[Any]) -> Dict[str, Any]:
        """
        Reads the current values of specified points from the ECY device.

        Args:
            points (List[Any]): List of point instances to read.

        Returns:
            Dict[str, Any]: Dictionary mapping point names to their current values.
        """
        results = {}
        for point in points:
            object_type = point.object_type  # Assuming each point has an 'object_type' attribute
            object_name = point.object_name  # Assuming each point has an 'object_name' attribute
            property_name = point.property_name  # Assuming each point has a 'property_name' attribute

            instance_number = self.get_instance_number(object_name, object_type)
            if instance_number is not None:
                value = self.get_property_value(object_type, instance_number, property_name)
                if value is not None:
                    results[object_name] = value
                else:
                    logging.error(f"Failed to retrieve value for point '{object_name}'.")
            else:
                logging.error(f"Cannot retrieve instance number for point '{object_name}'. Skipping value retrieval.")
        return results

    def write_values_to_endpoints(self, points: List[Any], max_retries: int = 3, backoff_factor: float = 0.5) -> bool:
        """
        Writes multiple point values to the ECY device using batch requests.

        Args:
            points (List[Any]): List of point instances to write.
            max_retries (int): Maximum number of retry attempts.
            backoff_factor (float): Factor for exponential backoff between retries.

        Returns:
            bool: True if all writes are successful, False otherwise.
        """
        if not points:
            logging.warning("No points provided for batch synchronization.")
            return False

        batch_payload = {"requests": []}

        for point in points:
            # Each point prepares its own batch request
            point_payload = point.prepare_batch_request()
            if point_payload and "requests" in point_payload:
                batch_payload["requests"].extend(point_payload["requests"])
            else:
                logging.warning(f"Point '{point.object_name}' did not provide a valid batch request.")

        if not batch_payload["requests"]:
            logging.warning("No valid batch requests to send after processing all points.")
            return False

        logging.debug(f"Batch payload prepared with {len(batch_payload['requests'])} requests.")
        return self.send_batch_request(batch_payload, max_retries, backoff_factor)

    def send_batch_request(self, batch_payload: Dict[str, Any], max_retries: int, backoff_factor: float) -> bool:
        """
        Sends a batch API request to the ECY device with retry logic.

        Args:
            batch_payload (Dict[str, Any]): The batch request payload.
            max_retries (int): Maximum number of retry attempts.
            backoff_factor (float): Factor for exponential backoff between retries.

        Returns:
            bool: True if successful, False otherwise.
        """
        batch_url = f"https://{self.device_ip_address}/api/rest/v2/batch"
        headers = {"Content-Type": "application/json"}

        for attempt in range(1, max_retries + 1):
            logging.debug(f"Attempt {attempt}: Sending batch request to {batch_url} with payload: {batch_payload}")
            with self.lock:
                try:
                    response = self.session.post(batch_url, headers=headers, json=batch_payload, verify=self.session.verify)
                    response.raise_for_status()
                    logging.info(f"Batch request successful for device {self.device_ip_address}. Status Code: {response.status_code}")
                    return True
                except requests.RequestException as e:
                    logging.error(f"Batch request failed for device {self.device_ip_address} on attempt {attempt}: {e}")
                    if hasattr(e, 'response') and e.response is not None:
                        logging.error(f"Response status code: {e.response.status_code}")
                        logging.error(f"Response content: {e.response.content}")
                    if attempt < max_retries:
                        sleep_time = backoff_factor * (2 ** (attempt - 1))
                        logging.info(f"Retrying in {sleep_time} seconds...")
                        time.sleep(sleep_time)
                    else:
                        logging.error(f"All {max_retries} attempts failed for batch request to {self.device_ip_address}.")
                        return False

    def set_out_of_service(self, object_type: str, instance_number: int, out_of_service: bool = True) -> bool:
        """
        Sets the out-of-service status for a specific object on the ECY device.

        Args:
            object_type (str): Type of the ECY object (e.g., "AnalogValue").
            instance_number (int): Instance number of the ECY object.
            out_of_service (bool): Desired out-of-service status.

        Returns:
            bool: True if the operation is successful, False otherwise.
        """
        url = f"https://{self.device_ip_address}/api/rest/v2/services/bacnet/local/objects/{object_type}/{instance_number}/out-of-service"
        headers = {"Content-Type": "application/json"}

        payload = {"value": out_of_service}

        logging.debug(f"Setting out-of-service for {object_type} instance {instance_number} to {out_of_service}.")

        with self.lock:
            try:
                response = self.session.post(url, headers=headers, json=payload, verify=self.session.verify)
                response.raise_for_status()
                logging.info(f"Set out-of-service for {object_type} instance {instance_number} to {out_of_service}.")
                return True
            except requests.RequestException as e:
                logging.error(f"Failed to set out-of-service for {object_type} instance {instance_number}: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logging.error(f"Response status code: {e.response.status_code}")
                    logging.error(f"Response content: {e.response.content}")
                return False