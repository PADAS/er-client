# EarthRanger Client
## Introduction
[EarthRanger](https://www.earthranger.com/) is a software solution that helps protected area managers, ecologists, and wildlife biologists make informed operational decisions for wildlife conservation.

The earthranger-client (er-client) is a Python library for accessing the EarthRanger HTTP API. It simplifies interaction with the API by abstracting away the complexity of resource-based endpoints and provides multi-threaded and async capabilities for improved performance.

## Uses of er-client
* Extracting data for analysis
* Importing ecological or other historical data
* Integrating a new field sensor type. If you do and will be supporting multiple ER sites, contact us to talk about our Gundi integrations platform
* Performing external analysis that results in publishing an Alert on the ER platform.

## Quick Start

see simple-example.py

## Installation
From pypi
```
pip install earthranger-client
```

## Usage
In your code, import the library and create an instance of the client.

```
from erclient import ERClient

client = ERClient(service_root="https://sandbox.pamdas.org/api/v1.0", username="", password="")
```
## Async Support
We also offer an async client (asyncio).

Disclaimer: The async client is experimental and the current capabilities are limited to:
* Posting Sensor Observations (a.k.a Positions)
* Posting Reports (a.k.a Events)
* Posting Report Attachments
* Posting Camera Trap Reports
* Getting Events
* Getting Observations
```
from erclient import AsyncERClient

# You can use it as an async context-managed client
async with AsyncERClient(service_root="https://sandbox.pamdas.org/api/v1.0", username="", password="") as client:
   await self.er_client.post_sensor_observation(position)
   await client.post_report(report)
   await self.er_client.post_camera_trap_report(camera_trap_payload, file)
   ...
   
async with AsyncERClient(service_root="https://sandbox.pamdas.org/api/v1.0", username="", password="") as client:
   async for observation in client.get_observations(start="2023-11-10T00:00:00-06:00"):
      print(observation)
      ...

# Or create an instance and close the client explicitly later
client = AsyncERClient(service_root="https://sandbox.pamdas.org/api/v1.0", username="", password="")
await self.er_client.post_sensor_observation(position)
await client.post_report(report)
await self.er_client.post_camera_trap_report(camera_trap_payload, file)
...
await client.close()  # Close the session used to send requests to ER API
```
