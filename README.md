# Project Title: BOPTest ECY Device Integration

## Overview

This project integrates a Building Optimization Performance Test (BOPTest) simulation with Distech Controls' ECY Series devices using REST API. 
The application synchronizes simulation data from BOPTest with ECY devices, allowing for real-time testing and validation of building control systems. 
This project initializes the remote BOPTest TestCase, sets its start time, step time, warmup period and matches up the timezone and time of the BOPTest and the ECY Controllers.  As this project moves the TestCase forward in time, it writes values from the TestCase to one or more Distech Controls ECY devices, as well as taking values from the ECY devices and writing them back to the TestCase.  This allows for a true building simulation using EC-GFX code to control the BOPTest TestCase. This project aims to require minimal "controller logic" modifications to function properly, in other words - all things being equal the user should be able to install a standard Distech GFX application, match the points between the Testcase and Controllers and start interacting with it.  

This project is valuable in a number of ways - for training building automation customers and system's integrators on real data, sales demonstrations, 
trade show booths, testing Distech Controls Builder applications, as well as training machine learning such as reinforcement learning.

The key components of this project are:

- **BOPTestClient**: Interface to interact with the BOPTest simulation server.
- **ECYDeviceClient**: Interface to interact with ECY devices via REST API.
- **EquipmentManager**: Manages equipment configurations and associated points.
- **Points**: Represents individual points (sensors, setpoints, actuators, commands) with methods for processing and syncing values.
- **Unit Conversion Utilities**: Functions for converting units from/to US or SI units.
- **Configurations**: JSON Configuration files that designate ECY endpoints along with the desired point matching between BOPTest Client and ECY Device Client.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Code Explanation](#code-explanation)
  - [Main Application (`main.py`)](#main-application-mainpy)
  - [BOPTest Client (`boptest_client.py`)](#boptest-client-boptest_clientpy)
  - [ECY Device Client (`ecy_device_client.py`)](#ecy-device-client-ecy_device_clientpy)
  - [Equipment Manager (`equipment_manager.py`)](#equipment-manager-equipment_managerpy)
  - [Points (`points/`)](#points-points)
  - [Unit Conversion Utilities (`unit_conversion.py`)](#unit-conversion-utilities-unit_conversionpy)
- [Extending the Project](#extending-the-project)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Project Structure

```
project-root/
├── main.py
├── clients/
│   ├── boptest_client.py
│   └── ecy_device_client.py
├── equipment/
│   └── equipment_manager.py
├── points/
│   ├── __init__.py
│   ├── activation_point.py
│   ├── analog_input_point.py
│   ├── analog_output_point.py
│   ├── analog_value_point.py
│   ├── base_point.py
│   ├── binary_input_point.py
│   ├── binary_output_point.py
│   └── binary_value_point.py
├── utils/
│   ├── __init__.py
│   ├── logging_config.py
│   ├── unit_conversion.py
│   └── pint_registry.yaml
├── configs/
│   ├── AHU.json
│   └── # Other equipment configs
├── requirements.txt
├── app.log
└── README.md
```

---

## Prerequisites

- **Python 3.12.5 or higher**
- **pip** package manager
- **Virtual environment** (recommended)

---

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```

2. **Create a Virtual Environment (Optional but Recommended)**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration

### **Environment Variables**

Create a `.env` file in the project root or export the following environment variables in your shell:

- **BOPTest Simulation Settings**

  - `BOP_SERVER_IP`: IP address of the BOPTest server.
  - `BOP_SERVER_PORT`: Port number of the BOPTest server.
  - `BOP_START_TIME`: Simulation start time.
  - `BOP_WARMUP_PERIOD`: Warm-up period for the simulation.
  - `BOP_STEP_TIME`: Step time for each simulation advance.
  - `UNIT_SYSTEM`: Global System Unit of Measurement.
  - `LOG_FILE`: log file.
  - `DESIRED_TIMEZONE`: Timezone to use to synch the ECYs to, it should be the same as the testcase and you need to format this according to what an ECY will accept.

- **ECY Device Credentials**

  - `ECY2_LOGIN_USERNAME`: Username for the ECY device.
  - `ECY2_LOGIN_PWORD`: Password for the ECY device.

**Example `.env` File:**

```env
BOP_SERVER_IP = '10.168.16.203'
BOP_SERVER_PORT = '5000'
BOP_START_TIME = '2023-07-06 14:00:00'
BOP_WARMUP_PERIOD = '0'
BOP_STEP_TIME = '1'
ECY2_LOGIN_USERNAME = 'nv_vis'
ECY2_LOGIN_PWORD = 'p55FBTws+cvujL:'
UNIT_SYSTEM = 'US'
LOG_FILE = 'app.log'
DESIRED_TIMEZONE = 'US/Mountain'
```

### **Equipment Configuration**

Equipment configurations are stored in JSON files within the `configs/` directory.

**Example `AHU.json`:**

```json
{
  "equipment_name": "AHU",
  "device_ip": "10.168.15.12",
  "points": [
    {
      "bop_point": "weaSta_reaWeaTDryBul_y",
      "ecy_point": "OutdoorAirTemp",
      "object_type": "AnalogValue",
      "unit": "K",
      "si_unit": "degC",
      "us_unit": "degF",
      "convert_to_us": true,
      "priority": 14
    },
    {
      "bop_point": "weaSta_reaWeaRelHum_y",
      "ecy_point": "OutdoorAirHumidity",
      "object_type": "AnalogValue",
      "unit": "dimensionless",
      "si_unit": "percent",
      "us_unit": "percent",
      "convert_to_us": true,
      "priority": 14
    },
    {
      "bop_point": "hvac_reaAhu_V_flow_sup_y",
      "ecy_point": "SupplyAirFlow",
      "object_type": "AnalogInput",
      "unit": "m**3/s",
      "si_unit": "m**3/s",
      "us_unit": "ft**3/min",
      "convert_to_us": true,
      "priority": 14
    },
    {
      "bop_point": "hvac_reaAhu_TSup_y",
      "ecy_point": "DischAirTemp",
      "object_type": "AnalogInput",
      "unit": "K",
      "si_unit": "degC",
      "us_unit": "degF",
      "convert_to_us": true,
      "priority": 14
    },
    {
      "bop_point": "hvac_reaAhu_TRet_y",
      "ecy_point": "RetAirTemp",
      "object_type": "AnalogInput",
      "unit": "K",
      "si_unit": "degC",
      "us_unit": "degF",
      "convert_to_us": true,
      "priority": 14
    },
    {
      "bop_point": "hvac_reaAhu_TMix_y",
      "ecy_point": "MixedAirTemp",
      "object_type": "AnalogInput",
      "unit": "K",
      "si_unit": "degC",
      "us_unit": "degF",
      "convert_to_us": true,
      "priority": 14
    },
    {
      "bop_point": "hvac_reaAhu_dp_sup_y",
      "ecy_point": "DischAirPress",
      "object_type": "AnalogInput",
      "unit": "pascal",
      "si_unit": "pascal",
      "us_unit": "inH2O",
      "convert_to_us": true,
      "priority": 14
    },
    {
      "bop_point": "hvac_oveAhu_yFan_u",
      "bop_override_point": "hvac_oveAhu_yFan_activate",
      "ecy_point": "DischFanSpeed",
      "object_type": "AnalogOutput"
    },
    {
      "bop_point": "hvac_oveAhu_yOA_u",
      "bop_override_point": "hvac_oveAhu_yOA_activate",
      "ecy_point": "OutdoorAirDamper",
      "object_type": "AnalogOutput"
    },
    {
      "bop_point": "hvac_oveAhu_yRet_u",
      "bop_override_point": "hvac_oveAhu_yRet_activate",
      "ecy_point": "ReturnAirDamper",
      "object_type": "AnalogOutput"
    },
    {
      "bop_point": "hvac_oveAhu_yCoo_u",
      "bop_override_point": "hvac_oveAhu_yCoo_activate",
      "ecy_point": "CoolingValve",
      "object_type": "AnalogOutput"
    },
    {
      "bop_point": "hvac_oveAhu_yHea_u",
      "bop_override_point": "hvac_oveAhu_yHea_activate",
      "ecy_point": "HeatingValve",
      "object_type": "AnalogOutput"
    },
    {
      "bop_point": "hvac_reaAhu_PFanSup_y",
      "ecy_point": "DischFanStatus",
      "object_type": "BinaryInput",
      "threshold": 0.5,
      "priority": 14
    },
    {
      "bop_point": "hvac_reaAhu_PPumHea_y",
      "ecy_point": "HeatingPumpStatus",
      "object_type": "BinaryInput",
      "threshold": 3,
      "priority": 14
    },
    {
      "bop_point": "hvac_reaAhu_PPumCoo_y",
      "ecy_point": "CoolingPumpStatus",
      "object_type": "BinaryInput",
      "threshold": 3,
      "priority": 14
    },
    {
      "bop_point": "hvac_oveAhu_yPumCoo_u",
      "bop_override_point": "hvac_oveAhu_yPumCoo_activate",
      "ecy_point": "CoolingPumpCmd",
      "object_type": "BinaryOutput"
    },
    {
      "bop_point": "hvac_oveAhu_yPumHea_u",
      "bop_override_point": "hvac_oveAhu_yPumHea_activate",
      "ecy_point": "HeatingPumpCmd",
      "object_type": "BinaryOutput"
    }
  ]
}
```

---

## Usage

1. **Ensure Environment Variables Are Set**

   - Export them in your shell or configure a `.env` file.

2. **Run the Application**

   ```bash
   python main.py
   ```

3. **Monitoring**

   - Observe the console output for log messages.
   - Logs will indicate the progress of the simulation and communication with the ECY devices.

4. **Stopping the Application**

   - Press `Ctrl+C` to gracefully shut down the application.

---

## Code Explanation

### Main Application (`main.py`)

The `main.py` script orchestrates the simulation and synchronization processes.

- **Environment Setup**: Loads necessary environment variables and verifies their presence.
- **Initialization**:
- Initializes the `UnitConverter` for getting the right data units in and out.
  - Initializes the `BOPTestClient` for interacting with the simulation.
  - Synchronizes the time and timezone of the model to the ECY Clients.
  - Initializes the `EquipmentManager`, which in turn initializes `ECYDeviceClient` instances for each equipment configuration file created by the user.
  - Loads equipment and point configurations.
- **Simulation Loop**:
  - Runs in a separate thread.
  - Advances the simulation at each time step.
  - Processes simulation data and updates point values.
- **ECY Communication Loop**:
  - Runs in another thread.
  - Synchronizes point values with the ECY devices using batch writes.
  - Each ECY device has its own instance with unique points lists and authentication management including basic authentication and cookie re-use.
- **Graceful Shutdown**:
  - Uses a threading `Event` to signal threads to stop.
  - Handles `KeyboardInterrupt` to allow manual interruption.

---

### BOPTest Client (`boptest_client.py`)

Handles communication with the BOPTest simulation server.

- **Methods**:
  - `__init____()`: Initialize the client with the server IP and port.
  - `get_metadata()`: Fetches input and measurement metadata from the server and combines them.
  - `initialize_system(start_time, warmup_period)`: Initializes the simulation environment.
  - `set_step_time(step_time)`: Sets the time increment for simulation steps.
  - `advance_simulation(control_inputs)`: Advances the simulation by one step.
  - `get_kpis()`: Fetches the models KPIs.

---

### ECY Device Client (`ecy_device_client.py`)

Handles communication with ECY devices via REST API.

- **Initialization**:
  - Fetches available endpoints from the device using Data filters.
  - Stores a mapping of object names and object instances to their details for quick access.
  - Uses the points from the JSON files to match BOPTest points to ECY Device points
- **Authentication**:
  - Handles Basic authentication and session management.
  - Uses basic authentication as well as cookie re-use for efficiency.
- **Batch Request** (`batch_request`):
  - Uses the `batch` endpoint to read and write multiple values in a single HTTP request.
  - Values read are the ones from the JSON file and what was found during initialization.
  - Handles special cases, such as setting `outOfService` for input objects before writing.
- **Methods**:
  - `__init____()`: Initialize the client with the server IP and port.
  - `disable_ntp()`: Turns off auto NTP
  - `set_time_and_timezone( timezone, unix_time)`: Sets the time and timezone of the ECYs to match the model
  - `get_existing_endpoints()`: Fetches the ECY devices existing Endpoints for Matching to BOPtest Endpoints using the config files
  - `get_instance_number( object_name, object_type)`: Fetches the ECY devices object's instance number
  - `get_property_value(object_name, object_type, property_name)`: Fetches the ECY devices object's values
  - `read_values_from_endpoints(points)`: Reads the current values of specified points from the ECY device, List of point instances to read, Dictionary mapping point names to their current values.
  - `write_values_from_endpoints(batch_payload)`: Writes multiple point values to the ECY device using batch requests.
  - `send_batch_request(points)`: Sends a batch API request to the ECY device with retry logic.
  - `set_out_of_service(object_type, instance_number, out_of_service)`: Sets the out-of-service status for a specific object on the ECY device.
---

### Equipment Manager (`equipment_manager.py`)

Manages equipment configurations and associated points.
Handles loading configurations and initializing point instances.

- **Methods**:
  - `load_equipments()`: Loads equipment configurations from the `configs/` directory.
  - `initialize_equipment(equipment_config)`: Initializes `ECYDeviceClient` and point instances for each equipment.
  - `get_all_ecy_clients()`: Retrieves all ECYDeviceClient instances managed by this EquipmentManager.
  - `get_pending_points_by_ecy_client()`: Retrieves all points that are pending synchronization, grouped by their ECYDeviceClient.
  - `get_ecy_client_points_mapping()`: Retrieves a mapping of ECY device IP addresses to their associated points.
  - `synchronize_time_and_timezone(start_time_unix, timezone)`: Synchronizes the time and timezone between the BOPTest client and all ECY clients.
- **Attributes**:
  - `equipment`: A dictionary containing equipment data, including `ecy_client` instances and point lists.

---

### Points (`points/`)

Represents individual points (sensors, setpoints, actuators, commands) with methods for processing and syncing values.

- **Base Class (`base_point.py`)**:
  - Defines common attributes and methods shared among all point types.
- **Analog Value (`analog_value_point.py`)**:
  - Initializes an AnalogValuePoint instance.
- **Binary Value (`binary_value_point.py`)**:
  - Initializes a BinaryValuePoint instance. 
- **Analog Output (`analog_output_point.py`)**: 
  - Initializes a AnalogOutputPoint instance. 
- **Binary Output (`binary_output_point.py`)**:
  - Initializes a BinaryOutputPoint instance.  
- **Analog Input (`analog_input_point.py`)**:
  - Initializes an AnalogInputPoint instance. 
- **Binary Input (`binary_input_point.py`)**:
  - Initializes an BinaryInputPoint instance.  
- **Methods**:
    - `process_bop_value(bop_value, metadata)`: Processes the raw value from the simulation, including unit conversion.
    - `sync_with_ecy()`: Previously used for individual synchronization; now batch writing is used.
- **Attributes**:
  - `config`: Configuration data for the point.
  - `ecy_client`: Reference to the `ECYDeviceClient` instance.
  - `value`: The current value of the point to be written to the ECY device.
  - `object_name`, `object_type`, `instance_number`: Identifiers for communication with the ECY device.

---

### Unit Conversion Utilities (`unit_conversion.py`)

Provides functions for converting units from SI to US customary units.

- **Function**: `convert(value, unit)`
  - Converts the input `value` based on the specified `unit`.
  - Supports temperature (`K` to `F`), pressure (`Pa` to `InWC`), and others as needed.
- **Usage**:
  - Used in point classes within `process_bop_value` when `convert_to_us` is set to `True`.

---

## Extending the Project

- **Adding New Equipment**:
  - Create a new configuration file in the `configs/` directory.
  - Define equipment name, device IP, and point mappings.
- **Implementing New Point Types**:
  - Create a new point class in the `points/` directory, inheriting from `Point`.
  - Implement the necessary methods, especially `process_bop_value`.
- **Expanding Unit Conversions**:
  - Add new conversion cases in `unit_conversion.py` for additional units.

---

## Troubleshooting

- **Missing Environment Variables**:
  - Ensure all required environment variables are set.
  - Check for typos in variable names.
- **Connection Issues**:
  - Verify network connectivity to the BOPTest server and ECY devices.
  - Check for correct IP addresses and ports.
- **Authentication Failures**:
  - Confirm the ECY device credentials are correct.
  - Ensure the ECY device API is accessible and the user has sufficient permissions.
- **Simulation Errors**:
  - Review simulation settings for correctness.
  - Check the BOPTest server logs for error messages.
- **Unit Conversion Errors**:
  - Ensure units specified in point configurations are supported.
  - Verify the accuracy of conversion functions.

---

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

---

## Acknowledgements

- **Distech Controls**: For providing the ECY Series device APIs and documentation.
- **BOPTest Framework**: For the simulation platform used in this project.

---

**Note**: This README provides an overview of the project's structure and functionality. For detailed documentation on each module and class, refer to the docstrings and comments within the code.

---

## Contact

For questions or collaboration, please reach out to [Aaron Fish](mailto:afish@distech-controls.com).