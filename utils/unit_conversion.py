# utils/unit_conversion.py

from pint import UnitRegistry, UndefinedUnitError
import logging

class UnitConverter:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UnitConverter, cls).__new__(cls)
            cls._instance.ureg = UnitRegistry()
            # Define any additional units or aliases if necessary
            cls._instance.ureg.define('cubic_meter_per_second = m**3/s = m3/s')
            cls._instance.ureg.define('cubic_foot_per_minute = ft**3/min = ft3/min')
            cls._instance.ureg.define('degrees_celsius = degC = C')  # Alias for Celsius
            cls._instance.ureg.define('ppm = parts_per_million = 1e-6')  # Define PPM if not default
            #cls._instance.ureg.define('percent = [] = % = pct = 0.01*dimensionless')  # Define percent
            # Manually define 'inH2O'
            cls._instance.ureg.define('inH2O = 249.082 Pa')
            #logging.debug("Manually defined 'inH2O' as 249.082 Pa.")

            # Log all available units for verification
            #logging.debug("Available units in UnitRegistry:")
            #for unit in sorted(cls._instance.ureg):
                #logging.debug(f" - {unit}")
        return cls._instance

    def convert(self, value: float, from_unit: str, to_unit: str) -> float:
        """
        Converts a value from one unit to another.

        Args:
            value (float): The numerical value to convert.
            from_unit (str): The current unit of the value.
            to_unit (str): The target unit for conversion.

        Returns:
            float: The converted value.

        Raises:
            ValueError: If the conversion between specified units is not supported or fails.
        """
        #logging.debug(f"Attempting to convert {value} from '{from_unit}' to '{to_unit}'.")
        try:
            quantity = value * self.ureg(from_unit)
            converted_quantity = quantity.to(to_unit)
            #logging.debug(f"Successfully converted {value} {from_unit} to {converted_quantity.magnitude} {to_unit}.")
            return converted_quantity.magnitude
        except UndefinedUnitError as e:
            logging.error(f"Undefined unit in conversion: '{to_unit}' is not defined in the unit registry.")
            raise ValueError(f"Undefined unit in conversion: '{to_unit}' is not defined in the unit registry.") from e
        except Exception as e:
            logging.error(f"Error converting from '{from_unit}' to '{to_unit}': {e}")
            raise ValueError(f"Error converting from '{from_unit}' to '{to_unit}': {e}") from e

    def list_units(self):
        """
        Prints all available units in the UnitRegistry.
        """
        print("Available units in UnitRegistry:")
        for unit in sorted(self.ureg):
            print(f" - {unit}")