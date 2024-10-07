import requests
import logging
import json

class BOPTestClient:
    """Client for interacting with the BOPTest simulation server."""

    def __init__(self, server_ip, server_port):
        """Initialize the client with the server IP and port."""
        self.base_url = f"http://{server_ip}:{server_port}"

    def get_metadata(self):
        """Fetch input and measurement metadata from the server and combine them."""
        inputs_url = f"{self.base_url}/inputs"
        measurements_url = f"{self.base_url}/measurements"

        try:
            inputs_response = requests.get(inputs_url)
            measurements_response = requests.get(measurements_url)

            inputs_response.raise_for_status()
            measurements_response.raise_for_status()

            inputs_payload = inputs_response.json().get("payload", {})
            measurements_payload = measurements_response.json().get("payload", {})

            # Combine input and measurement metadata
            combined_metadata = {**inputs_payload, **measurements_payload}
            logging.info("Metadata fetched successfully.")
            return combined_metadata

        except requests.RequestException as e:
            logging.error(f"Error fetching metadata: {e}")
            return {}

    def initialize_system(self, start_time, warmup_period):
        """Initialize the system with the specified start time and warmup period."""
        url = f"{self.base_url}/initialize"
        data = {"start_time": start_time, "warmup_period": warmup_period}
        print(data)

        try:
            response = requests.put(url, json=data)
            response.raise_for_status()
            logging.info("System initialization successful.")
            return True, response.json()
        except requests.RequestException as e:
            logging.error(f"Error initializing system: {e}")
            return False, {}

    def set_step_time(self, step_time):
        """Set the simulation step time in seconds."""
        url = f"{self.base_url}/step"
        data = {"step": step_time}

        try:
            response = requests.put(url, json=data)
            response.raise_for_status()
            logging.info("Step time set successfully.")
            return True, response.json()
        except requests.RequestException as e:
            logging.error(f"Error setting step time: {e}")
            return False, {}

    def advance_simulation(self, control_inputs=None):
        """
        Advance the simulation by one step, optionally providing control inputs.

        Args:
            control_inputs (dict, optional): Dictionary containing control inputs to send to BOPTest.
                                            Defaults to None.

        Returns:
            tuple: (success: bool, response_data: dict)
                - success: True if the simulation was advanced successfully, False otherwise.
                - response_data: The JSON response from the server if successful, else an empty dict.
        """
        url = f"{self.base_url}/advance"
        if control_inputs is None:
            control_inputs = {}

        # Serialize and log the payload being sent
        try:
            payload_str = json.dumps(control_inputs, indent=2)
            logging.debug(f"Sending POST request to {url} with payload:\n{payload_str}")
        except (TypeError, ValueError) as e:
            logging.error(f"Failed to serialize control_inputs to JSON: {e}")
            return False, {}

        try:
            response = requests.post(url, json=control_inputs, headers={"Content-Type": "application/json"})
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            
            # Log the successful response
            try:
                response_json = response.json()
                response_pretty = json.dumps(response_json, indent=2)
                logging.debug(f"Received successful response from {url}:\n{response_pretty}")
            except ValueError:
                # Response is not JSON
                logging.debug(f"Received non-JSON response from {url}:\n{response.text}")

            logging.info("Simulation advanced successfully.")
            return True, response_json if 'response_json' in locals() else {}
        
        except requests.exceptions.HTTPError as e:
            # Log detailed error information
            logging.error(f"Error advancing simulation: {e}")
            
            if response.content:
                try:
                    response_json = response.json()
                    response_pretty = json.dumps(response_json, indent=2)
                    logging.error(f"Response content from {url}:\n{response_pretty}")
                except ValueError:
                    # Response content is not JSON
                    logging.error(f"Response content from {url} is not valid JSON:\n{response.content}")
            
            return False, {}
        
        except requests.exceptions.RequestException as e:
            # Catch all other request-related errors
            logging.error(f"RequestException while advancing simulation: {e}")
            return False, {}
        
    def get_kpis(self):
        """
        Retrieve KPI values from the /kpi endpoint.

        Returns:
            tuple: (success: bool, kpis: dict)
                - success: True if KPIs were retrieved successfully, False otherwise.
                - kpis: The KPI data if successful, else an empty dict.
        """
        url = f"{self.base_url}/kpi"

        try:
            logging.debug(f"Fetching KPIs from {url}")
            response = requests.get(url)
            response.raise_for_status()
            kpis = response.json().get("payload", {})
            logging.info("KPIs fetched successfully.")
            return True, kpis
        except requests.RequestException as e:
            logging.error(f"Error fetching KPIs: {e}")
            return False, {}