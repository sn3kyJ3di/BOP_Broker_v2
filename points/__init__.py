# points/__init__.py

import logging
from typing import Optional, Dict, Any, Type

from .analog_input_point import AnalogInputPoint
from .analog_output_point import AnalogOutputPoint
from .analog_value_point import AnalogValuePoint
from .binary_input_point import BinaryInputPoint
from .binary_output_point import BinaryOutputPoint
from .binary_value_point import BinaryValuePoint
from .activation_point import ActivationPoint

def create_point(
    point_config: Dict[str, Any],
    ecy_client: Any,
    bop_client: Any,
    unit_converter: Any = None  # Make it optional
) -> Optional[Any]:
    """
    Factory function to create point instances based on object_type.

    Args:
        point_config (Dict[str, Any]): Configuration dictionary for the point.
        ecy_client (Any): Instance of ECYDeviceClient to communicate with ECY devices.
        bop_client (Any): Instance of BOPTestClient to communicate with BOPTest devices.
        unit_converter (Any, optional): Instance of UnitConverter for unit conversions. Defaults to None.

    Returns:
        Optional[Any]: Instance of the appropriate point class or None if unsupported.
    """
    object_type = point_config.get('object_type', '').strip().lower()
    activate = point_config.get('activate', False)

    # Mapping of object_type to corresponding Point classes
    object_type_mapping: Dict[str, Type[Any]] = {
        'analoginput': AnalogInputPoint,
        'analogoutput': AnalogOutputPoint,
        'analogvalue': AnalogValuePoint,
        'binaryinput': BinaryInputPoint,
        'binaryoutput': BinaryOutputPoint,
        'binaryvalue': BinaryValuePoint
        # Add other mappings here as needed
    }

    if activate:
        logging.debug(f"Creating ActivationPoint for '{point_config.get('ecy_point', 'UnnamedPoint')}'.")
        try:
            return ActivationPoint(point_config, ecy_client, bop_client, unit_converter)
        except Exception as e:
            logging.error(f"Error creating ActivationPoint for '{point_config.get('ecy_point', 'UnnamedPoint')}': {e}")
            return None

    point_class = object_type_mapping.get(object_type)
    if point_class:
        logging.debug(f"Creating {point_class.__name__} for '{point_config.get('ecy_point', 'UnnamedPoint')}'.")
        try:
            # Determine if the point class requires a unit_converter
            if point_class in [AnalogInputPoint, AnalogValuePoint]:
                if unit_converter is None:
                    logging.error(f"UnitConverter is required for {point_class.__name__} but not provided.")
                    return None
                point_instance = point_class(point_config, ecy_client, bop_client, unit_converter)
            elif point_class in [BinaryValuePoint, BinaryInputPoint, AnalogOutputPoint, BinaryOutputPoint]:
                # These points do not require unit_converter
                point_instance = point_class(point_config, ecy_client, bop_client)
            else:
                # Handle other point types if any
                point_instance = point_class(point_config, ecy_client, bop_client, unit_converter)
            logging.info(f"Created {point_class.__name__} '{point_instance.object_name}'.")
            return point_instance
        except Exception as e:
            logging.error(f"Error creating instance of {point_class.__name__} for '{point_config.get('ecy_point', 'UnnamedPoint')}': {e}")
            return None
    else:
        logging.error(f"Unsupported object type: '{point_config.get('object_type', 'Unknown')}' for point '{point_config.get('ecy_point', 'UnnamedPoint')}'.")
        return None