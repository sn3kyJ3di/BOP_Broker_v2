# points/base_point.py

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class Point(ABC):
    def __init__(self, config: Dict[str, Any], ecy_client: Any):
        """
        Initializes a Point instance.

        Args:
            config (Dict[str, Any]): Configuration dictionary for the point.
            ecy_client (Any): Instance of ECYDeviceClient to communicate with ECY devices.
        """
        self.config: Dict[str, Any] = config
        self.ecy_client: Any = ecy_client
        self.value: Optional[float] = None
        self.object_name: str = config.get('ecy_point', 'UnnamedPoint')
        self.object_type: str = config.get('object_type', 'UnknownType')
        self.priority: Optional[int] = config.get('priority')  # Applicable for Outputs
        self.unit: Optional[str] = config.get('unit')
        self.convert_to_us: bool = config.get('convert_to_us', False)
        self.object_instance: Optional[int] = None  # To be assigned by EquipmentManager
        self.threshold: Optional[float] = config.get('threshold')  # For Binary Inputs
        self.activate: bool = config.get('activate', False)  # For Activation Points

    @abstractmethod
    def process_bop_value(self, bop_value: float, metadata: Dict[str, Any]) -> None:
        """
        Processes the value received from BOPTest.

        Args:
            bop_value (float): The raw value received from BOPTest.
            metadata (Dict[str, Any]): Additional metadata associated with the value.
        """
        pass

    @abstractmethod
    def prepare_batch_request(self) -> Dict[str, Any]:
        """
        Prepares the batch request payload for this point.

        Returns:
            Dict[str, Any]: The batch request payload.
        """
        pass

    @abstractmethod
    def has_pending_sync(self) -> bool:
        """
        Determines if there are pending synchronization tasks.

        Returns:
            bool: True if there's a pending sync, False otherwise.
        """
        pass

    def assign_object_instance(self, instance_number: int) -> None:
        """
        Assigns the object instance number to the point.

        Args:
            instance_number (int): The object instance number from ECY device.
        """
        self.object_instance = instance_number
        logging.debug(f"Assigned object_instance={self.object_instance} to point '{self.object_name}'.")