# points/activation_point.py

from points.base_point import Point
import logging

class ActivationPoint(Point):
    def process_bop_value(self, bop_value, metadata):
        """Activation points do not process BOPTest values; they are set to 1 each step."""
        self.value = 1  # Always set to 1

    def sync_to_ecy(self, bop_client=None):
        """Writes the activation value to the ECY device."""
        if self.value is not None:
            success = self.ecy_client.write_present_value(self.object_type, self.instance_number, self.value)
            if success:
                logging.info(f"Wrote ActivationPoint '{self.object_name}' value {self.value} to ECY.")
            else:
                logging.error(f"Failed to write ActivationPoint '{self.object_name}' to ECY.")
        else:
            logging.warning(f"No activation value set for '{self.object_name}', skipping sync.")

    def sync_from_ecy(self, bop_client):
        """Activation points do not read from ECY to write to BOPTest."""
        pass