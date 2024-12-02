import requests
import logging
import json

class BOPTestClient:
    """Client for interacting with the BOPTest simulation server."""

    def __init__(self, server_ip, server_port):
        """Initialize the client with the server IP and port."""
        self.base_url = f"http://{server_ip}:{server_port}"
        self.testid = None

    def select_test_case(self, testcase_name):
        """Select a test case and retrieve the testid."""
        url = f"{self.base_url}/testcases/{testcase_name}/select"
        try:
            # Add timeout parameter
            response = requests.post(url, timeout=10)  # 10 seconds timeout
            response.raise_for_status()
            self.testid = response.json().get("testid")
            logging.info(f"Test case '{testcase_name}' selected with testid: {self.testid}")
            return True
        except requests.Timeout:
            logging.error(f"Timeout while connecting to {url}")
            return False
        except requests.RequestException as e:
            logging.error(f"Error selecting test case: {e}")
            return False

    def get_metadata(self):
        """Fetch input and measurement metadata from the server and combine them."""
        if not self.testid:
            logging.error("Test case not selected. Please select a test case first.")
            return {}

        inputs_url = f"{self.base_url}/inputs/{self.testid}"
        measurements_url = f"{self.base_url}/measurements/{self.testid}"

        try:
            inputs_response = requests.get(inputs_url)
            measurements_response = requests.get(measurements_url)

            inputs_response.raise_for_status()
            measurements_response.raise_for_status()

            inputs_payload = inputs_response.json().get("payload", {})
            measurements_payload = measurements_response.json().get("payload", {})

            combined_metadata = {**inputs_payload, **measurements_payload}
            logging.info("Metadata fetched successfully.")
            return combined_metadata

        except requests.RequestException as e:
            logging.error(f"Error fetching metadata: {e}")
            return {}

    def initialize_system(self, start_time, warmup_period):
        """Initialize the system with the specified start time and warmup period."""
        if not self.testid:
            logging.error("Test case not selected. Please select a test case first.")
            return False, {}

        url = f"{self.base_url}/initialize/{self.testid}"
        data = {"start_time": start_time, "warmup_period": warmup_period}

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
        if not self.testid:
            logging.error("Test case not selected. Please select a test case first.")
            return False, {}

        url = f"{self.base_url}/step/{self.testid}"
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
        """Advance the simulation by one step, optionally providing control inputs."""
        if not self.testid:
            logging.error("Test case not selected. Please select a test case first.")
            return False, {}

        url = f"{self.base_url}/advance/{self.testid}"
        if control_inputs is None:
            control_inputs = {}

        try:
            payload_str = json.dumps(control_inputs, indent=2)
            logging.debug(f"Sending POST request to {url} with payload:\n{payload_str}")
        except (TypeError, ValueError) as e:
            logging.error(f"Failed to serialize control_inputs to JSON: {e}")
            return False, {}

        try:
            response = requests.post(url, json=control_inputs, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            
            try:
                response_json = response.json()
                response_pretty = json.dumps(response_json, indent=2)
                logging.debug(f"Received successful response from {url}:\n{response_pretty}")
            except ValueError:
                logging.debug(f"Received non-JSON response from {url}:\n{response.text}")

            logging.info("Simulation advanced successfully.")
            return True, response_json if 'response_json' in locals() else {}
        
        except requests.exceptions.HTTPError as e:
            logging.error(f"Error advancing simulation: {e}")
            if response.content:
                try:
                    response_json = response.json()
                    response_pretty = json.dumps(response_json, indent=2)
                    logging.error(f"Response content from {url}:\n{response_pretty}")
                except ValueError:
                    logging.error(f"Response content from {url} is not valid JSON:\n{response.content}")
            return False, {}
        
        except requests.exceptions.RequestException as e:
            logging.error(f"RequestException while advancing simulation: {e}")
            return False, {}

    def get_kpis(self):
        """Retrieve KPI values from the /kpi endpoint."""
        if not self.testid:
            logging.error("Test case not selected. Please select a test case first.")
            return False, {}

        url = f"{self.base_url}/kpi/{self.testid}"

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