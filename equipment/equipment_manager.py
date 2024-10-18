# equipment/equipment_manager.py

import os
import json
import logging
from typing import Dict, Any, List
from clients.ecy_device_client import ECYDeviceClient
from points import create_point  # Factory function that returns point instances

class EquipmentManager:
    """
    Manages equipment configurations and associated points.
    Handles loading configurations and initializing point instances.
    """

    def __init__(
        self,
        config_dir: str,
        ecy_username: str,
        ecy_password: str,
        bop_client: Any,
        unit_converter: Any
    ):
        """
        Initializes the EquipmentManager.

        Args:
            config_dir (str): Directory containing equipment configuration JSON files.
            ecy_username (str): Username for ECY device authentication.
            ecy_password (str): Password for ECY device authentication.
            bop_client (Any): Client instance for interacting with BOPTest.
            unit_converter (Any): Instance for handling unit conversions.
        """
        self.config_dir = config_dir
        self.ecy_username = ecy_username
        self.ecy_password = ecy_password
        self.bop_client = bop_client
        self.unit_converter = unit_converter
        self.equipment: Dict[str, Dict[str, Any]] = {}

    def load_equipments(self) -> None:
        """
        Loads all equipment configurations from the config directory.
        """
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.config_dir, filename)
                with open(filepath, 'r') as file:
                    try:
                        equipment_config = json.load(file)
                        self.initialize_equipment(equipment_config, filename)
                        logging.info(f"Loaded equipment configuration from '{filename}'.")
                    except json.JSONDecodeError as e:
                        logging.error(f"Error parsing '{filename}': {e}")

    def initialize_equipment(self, equipment_config: Dict[str, Any], filename: str) -> None:
        """
        Initializes equipment and their associated points.

        Args:
            equipment_config (dict): Equipment configuration dictionary.
            filename (str): Name of the configuration file for logging purposes.
        """
        device_ip = equipment_config.get('device_ip')
        equipment_name = equipment_config.get('equipment_name', 'UnnamedEquipment')

        if not device_ip:
            logging.error(f"'device_ip' not found in configuration '{filename}'.")
            return

        # Initialize ECYDeviceClient with credentials
        try:
            ecy_client = ECYDeviceClient(
                device_ip_address=device_ip,
                device_username=self.ecy_username,
                device_password=self.ecy_password
            )
            # ecy_client has fetched endpoints at this point
            logging.debug(f"ECYDeviceClient initialized for device {device_ip}.")
        except Exception as e:
            logging.error(f"Failed to initialize ECYDeviceClient for '{equipment_name}': {e}")
            return

        # Create point instances
        points: List[Any] = []
        for point_config in equipment_config.get('points', []):
            # Ensure the ECY point exists
            ecy_point_name = point_config.get('ecy_point')
            object_type = point_config.get('object_type')

            if not ecy_point_name:
                logging.error(f"Point configuration missing 'ecy_point' in equipment '{equipment_name}'.")
                continue

            if ecy_point_name not in ecy_client.endpoints_by_name:
                logging.error(f"ECY point '{ecy_point_name}' not found on device {device_ip}.")
                continue  # Skip this point or handle as needed

            # Create point instance with unit_converter if needed
            object_type_lower = object_type.lower() if object_type else ''
            if object_type_lower == 'binaryoutput':
                point = create_point(
                    point_config=point_config,
                    ecy_client=ecy_client,
                    bop_client=self.bop_client
                    # Do not pass unit_converter for BinaryOutput
                )
            else:
                point = create_point(
                    point_config=point_config,
                    ecy_client=ecy_client,
                    bop_client=self.bop_client,
                    unit_converter=self.unit_converter
                )
            if point:
                # Assign object_instance to the point
                instance_number = ecy_client.get_instance_number(ecy_point_name, object_type)
                if instance_number is not None:
                    point.assign_object_instance(instance_number)
                    logging.debug(f"Assigned object_instance={instance_number} to point '{point.object_name}'.")
                else:
                    logging.error(f"Could not find object_instance for point '{ecy_point_name}'. Skipping point.")
                    continue  # Skip this point as it cannot be synchronized without object_instance

                points.append(point)
                logging.debug(f"Created and initialized point '{point.object_name}' for equipment '{equipment_name}'.")
            else:
                logging.error(f"Failed to create point for '{ecy_point_name}' in equipment '{equipment_name}'.")

        if points:
            self.equipment[equipment_name] = {
                'ecy_client': ecy_client,
                'points': points
            }
            logging.info(f"Initialized equipment '{equipment_name}' with {len(points)} points.")
        else:
            logging.warning(f"No valid points found for equipment '{equipment_name}'.")

    def get_all_ecy_clients(self) -> List[ECYDeviceClient]:
        """
        Retrieves all ECYDeviceClient instances managed by this EquipmentManager.

        Returns:
            List[ECYDeviceClient]: A list of ECYDeviceClient instances.
        """
        return [equipment['ecy_client'] for equipment in self.equipment.values()]

    def get_pending_points_by_ecy_client(self) -> Dict[ECYDeviceClient, List[Any]]:
        """
        Retrieves all points that are pending synchronization, grouped by their ECYDeviceClient.

        Returns:
            Dict[ECYDeviceClient, List[Any]]: A dictionary mapping ECYDeviceClient instances to lists of pending points.
        """
        pending_points: Dict[ECYDeviceClient, List[Any]] = {}
        for equipment in self.equipment.values():
            ecy_client = equipment['ecy_client']
            for point in equipment['points']:
                if point.has_pending_sync():
                    if ecy_client not in pending_points:
                        pending_points[ecy_client] = []
                    pending_points[ecy_client].append(point)
        return pending_points

    def get_ecy_client_points_mapping(self) -> Dict[str, List[Any]]:
        """
        Retrieves a mapping of ECY device IP addresses to their associated points.

        Returns:
            Dict[str, List[Any]]: A dictionary mapping device IPs to lists of point instances.
        """
        mapping: Dict[str, List[Any]] = {}
        for equipment_name, equipment in self.equipment.items():
            ecy_client = equipment['ecy_client']
            device_ip = ecy_client.device_ip_address
            points = equipment['points']
            if device_ip not in mapping:
                mapping[device_ip] = []
            mapping[device_ip].extend(points)
        return mapping

    def synchronize_time_and_timezone(self, start_time_unix: int, timezone: str) -> None:
        """
        Synchronizes the time and timezone between the BOPTest client and all ECY clients.

        Args:
            start_time_unix (int): The start time in Unix time to synchronize.
            timezone (str): The timezone string to set on ECY clients (e.g., "America/New_York").
        """
        logging.info("Starting time and timezone synchronization with ECY clients.")
        ecy_clients = self.get_all_ecy_clients()

        for ecy_client in ecy_clients:
            logging.debug(f"Synchronizing time for ECY device {ecy_client.device_ip_address}.")

            # Step 1: Disable NTP (if still required)
            if not ecy_client.disable_ntp():
                logging.error(f"Failed to disable NTP on ECY device {ecy_client.device_ip_address}. Skipping further synchronization for this device.")
                continue  # Skip to next ECY client if disabling NTP fails

            # Step 2 & 3: Set Timezone and Synchronize Start Time
            if not ecy_client.set_time_and_timezone(timezone=timezone, unix_time=start_time_unix):
                logging.error(f"Failed to set timezone and time on ECY device {ecy_client.device_ip_address}.")
                continue  # Skip to next ECY client if setting timezone and time fails

            logging.info(f"Successfully synchronized time and timezone on ECY device {ecy_client.device_ip_address}.")

        logging.info("Completed time and timezone synchronization with all ECY clients.")