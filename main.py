# main.py

import os
import logging
import threading
import time
import json
import sys
import requests

try:
    from zoneinfo import ZoneInfo  # For Python 3.9+
except ImportError:
    from pytz import timezone as ZoneInfo  # Fallback to pytz if zoneinfo is not available

from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv
from utils import setup_logging, UnitConverter
from equipment.equipment_manager import EquipmentManager
from clients.boptest_client import BOPTestClient  # Corrected import
from clients.ecy_device_client import ECYDeviceClient
from points.analog_output_point import AnalogOutputPoint
from points.binary_output_point import BinaryOutputPoint
from points.analog_input_point import AnalogInputPoint
from points.binary_input_point import BinaryInputPoint
from points.analog_value_point import AnalogValuePoint
from points.binary_value_point import BinaryValuePoint

# Load environment variables from .env file
load_dotenv()

# Load environment variables
server_ip = os.getenv('BOP_SERVER_IP')
server_port = os.getenv('BOP_SERVER_PORT')
testcase_name = os.getenv('TESTCASE_NAME')
start_time_str = os.getenv('BOP_START_TIME')
warmup_period = os.getenv('BOP_WARMUP_PERIOD')
step_time = os.getenv('BOP_STEP_TIME')
ecy_username = os.getenv('ECY2_LOGIN_USERNAME')
ecy_password = os.getenv('ECY2_LOGIN_PWORD')
unit_system = os.getenv('UNIT_SYSTEM', 'SI').upper()
log_file = os.getenv('LOG_FILE', 'app.log')       
desired_timezone = os.getenv('DESIRED_TIMEZONE')  # Removed default value

# Verify required environment variables
required_env_vars = {
    'BOP_SERVER_IP': server_ip,
    'BOP_SERVER_PORT': server_port,
    'TESTCASE_NAME': testcase_name,
    'BOP_START_TIME': start_time_str,
    'BOP_WARMUP_PERIOD': warmup_period,
    'BOP_STEP_TIME': step_time,
    'ECY2_LOGIN_USERNAME': ecy_username,
    'ECY2_LOGIN_PWORD': ecy_password,
    'UNIT_SYSTEM': unit_system,
    'LOG_FILE': log_file
    # 'DESIRED_TIMEZONE' is now optional and removed from required variables
}

missing_vars = [var for var, value in required_env_vars.items() if not value]
if missing_vars:
    # Initialize basic logging temporarily to capture the error
    logging.basicConfig(
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )
    logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    exit(1)

# Setup logging with DEBUG level and log to the specified log file
setup_logging(log_level=logging.DEBUG, log_file=log_file)

# Log initialization details
logging.info("Starting BOP Broker application.")

# Determine the unit system based on the environment variable
if unit_system == 'US':
    use_us_units = True
elif unit_system == 'SI':
    use_us_units = False
else:
    logging.warning(f"Invalid UNIT_SYSTEM '{unit_system}' specified. Defaulting to 'SI'.")
    use_us_units = False

# Initialize UnitConverter
unit_converter = UnitConverter()

# **Convert Human-Readable Start Time to Unix Timestamp**
try:
    # Define the expected format. Adjust if necessary.
    # Example format: '2023-07-06 14:00:00'
    start_time_naive = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')

    if desired_timezone:
        # Assign the desired timezone
        try:
            desired_tz = ZoneInfo(desired_timezone)
        except Exception as e:
            logging.error(f"Invalid 'DESIRED_TIMEZONE': {desired_timezone}. Error: {e}")
            exit(1)

        # Make the datetime object timezone-aware
        if 'zoneinfo' in sys.modules:
            # Using zoneinfo
            start_time_dt = start_time_naive.replace(tzinfo=desired_tz)
        else:
            # Using pytz
            start_time_dt = desired_tz.localize(start_time_naive)

        # Convert to Unix timestamp
        start_time_unix = int(start_time_dt.timestamp())
        logging.debug(f"Converted 'BOP_START_TIME' from '{start_time_str}' ({desired_timezone}) to Unix time: {start_time_unix}")
    else:
        # If no timezone is provided, assume UTC or handle accordingly
        start_time_dt = start_time_naive.replace(tzinfo=ZoneInfo('UTC'))
        start_time_unix = int(start_time_dt.timestamp())
        logging.debug(f"No 'DESIRED_TIMEZONE' provided. Converted 'BOP_START_TIME' from '{start_time_str}' (UTC) to Unix time: {start_time_unix}")

except ValueError as e:
    logging.error(f"Invalid 'BOP_START_TIME' format: {start_time_str}. Expected format 'YYYY-MM-DD HH:MM:SS'. Error: {e}")
    exit(1)
except Exception as e:
    logging.error(f"An unexpected error occurred while processing 'BOP_START_TIME': {e}")
    exit(1)

# Initialize BOPTestClient
bop_client = BOPTestClient(
    server_ip=server_ip,
    server_port=int(server_port)
)

# First, select the test case
success = bop_client.select_test_case(testcase_name)
if not success:
    logging.error(f"Failed to select test case '{testcase_name}'. Exiting...")
    exit(1)
logging.info(f"Successfully selected test case: {testcase_name}")

# Initialize BOPTest with start time and warmup period
success, init_response = bop_client.initialize_system(start_time_unix, warmup_period)
if not success:
    logging.error("Failed to initialize the BOPTest system. Exiting...")
    exit(1)

# Set the step time
success, step_response = bop_client.set_step_time(float(step_time))
if not success:
    logging.error("Failed to set step time. Exiting...")
    exit(1)

# Initialize EquipmentManager with ECY credentials
config_dir = os.path.join(os.getcwd(), 'configs')
equipment_manager = EquipmentManager(
    config_dir=config_dir,
    ecy_username=ecy_username,
    ecy_password=ecy_password,
    bop_client=bop_client,
    unit_converter=unit_converter
)
equipment_manager.load_equipments()

# **Conditional Synchronization of Time and Timezone**
if desired_timezone:
    logging.debug("Desired timezone provided. Synchronizing time and timezone with EquipmentManager.")
    try:
        equipment_manager.synchronize_time_and_timezone(start_time_unix=start_time_unix, timezone=desired_timezone)
        logging.info("Time and timezone synchronized successfully.")
    except Exception as e:
        logging.error(f"Failed to synchronize time and timezone: {e}")
        exit(1)
else:
    logging.info("No 'DESIRED_TIMEZONE' provided. Skipping time and timezone synchronization.")

def simulation_loop(
    bop_client: BOPTestClient,
    equipment_manager: EquipmentManager,
    stop_event: threading.Event,
    step_time: float
) -> None:
    """
    Continuously advances the simulation and synchronizes data with ECY endpoints.
    Executes the following steps in order within each step_time interval:
    1. Advance the simulation with previous ECY outputs.
    2. Retrieve KPIs and combine with simulation data.
    3. Process combined data and update points.
    4. Write updated point values to ECY endpoints.
    5. Read updated outputs from ECY endpoints for the next simulation advance.
    """
    # Initialize a dictionary to hold ECY outputs for the next simulation advance
    previous_ecy_outputs: Dict[str, Any] = {}
    
    # Initialize metadata (if needed, populate accordingly)
    metadata: Dict[str, Any] = {}
    
    while not stop_event.is_set():
        cycle_start_time = time.time()
        try:
            logging.debug("Simulation cycle started.")

            # 1. Advance the simulation with previous ECY outputs
            success, simulation_data = bop_client.advance_simulation(previous_ecy_outputs)
            if success:
                logging.debug(f"Simulation data received: {simulation_data}")
                
                # Extract the 'payload' from simulation_data
                payload = simulation_data.get('payload', {})
                if not payload:
                    logging.warning("Simulation data payload is empty or missing.")
                
                # 2. Retrieve KPIs after advancing the simulation
                success_kpi, kpi_data = bop_client.get_kpis()
                if success_kpi:
                    logging.debug(f"KPI data received: {json.dumps(kpi_data, indent=2)}")
                    # Combine simulation payload and KPI data
                    combined_payload = {**payload, **kpi_data}
                else:
                    logging.error("Failed to retrieve KPIs from BOPTest.")
                    combined_payload = payload  # Proceed with simulation data only
                
                # 3. Process combined data and update points
                for equipment_name, equipment in equipment_manager.equipment.items():
                    logging.debug(f"Processing equipment '{equipment_name}' with {len(equipment['points'])} points.")
                    for point in equipment['points']:
                        bop_point_key = point.config.get('bop_point')
                        if not bop_point_key:
                            logging.warning(f"Point '{point.object_name}' has no 'bop_point' configured.")
                            continue
                        bop_value = combined_payload.get(bop_point_key)
                        if bop_value is not None:
                            old_value = point.value
                            point.process_bop_value(bop_value, metadata)  # Pass metadata
                            logging.info(f"Point '{point.object_name}' value updated from {old_value} to {point.value}. Marked for synchronization.")
                        else:
                            logging.warning(f"Point '{point.object_name}' has no BOPTest value for key '{bop_point_key}'.")
        
                # 4. Write updated point values to ECY endpoints
                logging.debug("Writing data to ECY endpoints.")
                for equipment_name, equipment in equipment_manager.equipment.items():
                    ecy_client: ECYDeviceClient = equipment['ecy_client']
                    points_to_write = [
                        point for point in equipment['points'] 
                        if isinstance(point, (AnalogInputPoint, BinaryInputPoint, AnalogValuePoint, BinaryValuePoint, AnalogOutputPoint, BinaryOutputPoint)) 
                        and point.pending_sync
                    ]
                    if points_to_write:
                        logging.debug(f"Points marked for synchronization: {[point.object_name for point in points_to_write]}")
                        success_write = ecy_client.write_values_to_endpoints(points_to_write)
                        if success_write:
                            logging.info(f"Successfully wrote values to ECY device {ecy_client.device_ip_address}.")
                            # Reset pending_sync for points
                            for point in points_to_write:
                                point.pending_sync = False
                        else:
                            logging.error(f"Failed to write values to ECY device {ecy_client.device_ip_address}.")
                    else:
                        logging.debug(f"No points marked for synchronization for ECY device {ecy_client.device_ip_address}.")
        
                # 5. Read updated outputs from ECY endpoints for the next simulation advance
                logging.debug("Reading data from ECY endpoints.")
                combined_boptest_outputs: Dict[str, Any] = {}
                for equipment_name, equipment in equipment_manager.equipment.items():
                    ecy_client: ECYDeviceClient = equipment['ecy_client']
                    points_to_read = [
                        point for point in equipment['points'] 
                        if isinstance(point, (AnalogOutputPoint, BinaryOutputPoint))
                    ]
                    
                    if points_to_read:
                        ecy_outputs = ecy_client.read_values_from_endpoints(points_to_read)

                        # For each point, convert ECY output to the BOPTest equivalent payload
                        for point in points_to_read:
                            boptest_data = point.prepare_boptest_data()
                            if boptest_data:
                                combined_boptest_outputs.update(boptest_data)

                        logging.debug(f"ECY outputs from {ecy_client.device_ip_address}: {ecy_outputs}")
                        logging.debug(f"BOPTest outputs: {combined_boptest_outputs}")

                # 6. Prepare BOPTest outputs for the next simulation advance
                previous_ecy_outputs = combined_boptest_outputs  # This is now correctly BOPTest data

            else:
                logging.error("Failed to advance the simulation.")
                # Depending on requirements, decide whether to continue or stop
                # Here, we'll continue to the next cycle
        except Exception as e:
            logging.exception(f"Exception occurred in simulation_loop: {e}")
            # Depending on requirements, decide whether to continue or stop
            # Here, we'll continue to the next cycle

        # Calculate elapsed time and sleep accordingly to maintain step_time interval
        elapsed_time = time.time() - cycle_start_time
        sleep_time = step_time - elapsed_time
        if sleep_time > 0:
            logging.debug(f"Simulation cycle completed in {elapsed_time:.2f} seconds. Sleeping for {sleep_time:.2f} seconds.")
            time.sleep(sleep_time)
        else:
            logging.warning(f"Simulation cycle took longer ({elapsed_time:.2f} seconds) than the step_time ({step_time} seconds). Skipping sleep.")

def main() -> None:
    """
    Main function to start the simulation loop, KPI polling loop, and handle graceful shutdown.
    """
    # Create a stop event for graceful shutdown
    stop_event = threading.Event()

    # Start the simulation loop in a separate thread
    simulation_thread = threading.Thread(
        target=simulation_loop, 
        args=(bop_client, equipment_manager, stop_event, float(step_time)),
        daemon=True
    )
    simulation_thread.start()
    logging.info("Simulation loop started.")

    try:
        while not stop_event.is_set():
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        logging.info("Shutting down application.")
        stop_event.set()
        simulation_thread.join()
        logging.info("Application terminated gracefully.")

if __name__ == '__main__':
    main()