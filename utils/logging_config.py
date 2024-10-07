# utils/logging_config.py

import logging
import sys

def setup_logging(log_level=logging.INFO, log_file=None):
    """
    Configures the logging settings for the project.

    Args:
        log_level (int): The logging level (e.g., logging.INFO, logging.DEBUG).
        log_file (str, optional): Path to a file to log messages. Defaults to None.
    """
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Define the log format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Stream handler for console output
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # File handler for logging to a file, if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent logging from propagating to the root logger multiple times
    logger.propagate = False