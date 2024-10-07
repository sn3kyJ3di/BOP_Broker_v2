import requests
import numpy as np
 
base_url = "http://10.168.16.203:5000"
 
# 1. Initialization
requests.put(f"{base_url}/initialize", json={"start_time": 0, "warmup_period": 3600})
 
# 2. Scenario setup
requests.put(f"{base_url}/scenario", json={"time_period": "test_day", "electricity_price": "dynamic"})
 
# 3. Get available forecast points
forecast_points = requests.get(f"{base_url}/forecast_points").json()
 
# 4. Main control loop (24 hours with 1-hour steps)
for hour in range(24):
    # Get forecast for the next 6 hours
    forecast = requests.put(f"{base_url}/forecast", json={
        "point_names": ["outdoor_temperature", "electricity_price"],
        "horizon": 6 * 3600,  # 6 hours
        "interval": 3600  # 1-hour interval
    }).json()
 
    # Analyze forecast
    future_temps = np.array(forecast["outdoor_temperature"])
    future_prices = np.array(forecast["electricity_price"])
    # Simple strategy based on forecast:
    # If temperature and price are expected to rise, pre-cool
    if np.mean(future_temps) > 25 and np.mean(future_prices) > np.median(future_prices):
        cooling_strategy = "pre_cool"
    else:
        cooling_strategy = "normal"
 
    # Get current measurements and apply strategy
    for _ in range(4):  # 4 steps of 15 minutes each hour
        measurements = requests.post(f"{base_url}/advance", json={}).json()
        if cooling_strategy == "pre_cool":
            if measurements['zon_temp_1'] > 23:
                cooling_command = 1
            elif measurements['zon_temp_1'] < 21:
                cooling_command = 0
            else:
                cooling_command = 0.5
        else:  # normal strategy
            if measurements['zon_temp_1'] > 25:
                cooling_command = 1
            elif measurements['zon_temp_1'] < 22:
                cooling_command = 0
            else:
                cooling_command = 0.3
        # Send control command
        requests.post(f"{base_url}/advance", json={"cooling_com": cooling_command})
 
# 5. Get results
results = requests.put(f"{base_url}/results", json={
    "point_names": ["zon_temp_1", "cooling_com", "outdoor_temperature", "electricity_price"],
    "start_time": 0,
    "final_time": 86400
}).json()
 
kpi = requests.get(f"{base_url}/kpi").json()
 
# Analyze results
print("KPIs:", kpi)
print("Average zone temperature:", np.mean(results["zon_temp_1"]))
print("Total cooling command:", np.sum(results["cooling_com"]))
print("Average electricity price:", np.mean(results["electricity_price"]))