# Getting Started: Establishing a Connection to the VideoIPath Server

The following example shows how to establish a connection to the VideoIPath Server. All business logic is implemented in the `VideoIPathApp` class. Therefore, the user only needs to import the `VideoIPathApp` class from the `videoipath_automation_tool` package and initialize it with the required parameters.This could be done via environment variables or directly in the code.

The `VideoIPathApp` class provides all necessary methods to interact with the VideoIPath Server. Although methods are available on a lower level, it is strongly recommended to use the public methods of the `VideoIPathApp` class to interact with the VideoIPath Server. This guarantees easy handling, validation, logging, and reliability.

---

## Prerequisite

Before establishing a connection to the VideoIPath Server, ensure that the following requirements are met:

### User Account Settings (User Info)

- **User Authorization**:<br>The user account must be authorized using the `VideoIPath` authentication method.
- **Permissions**:<br>For a straightforward setup, enable both `API` and `Administrator` options for the user account (User Info). This ensures that the user has all necessary permissions to interact with the VideoIPath Server.

### Driver Versioning

To ensure IntelliSense support and runtime validation of custom settings, the VideoIPath Server should be running a compatible version of the driver schema. By default, the package uses the latest Long-Term Support (LTS) version, which is currently **2024.4.12**. If you need to use a different version, refer to the [Driver Versioning Guide](../driver-versioning.md).

## Example 1: Establishing a Connection to the VideoIPath Server via Environment Variables

### Step 1: Configure Environment Variables (.env File)

Create a `.env` file and define the following environment variables to configure the connection:

```bash
VIPAT_ENVIRONMENT=DEV
VIPAT_VIDEOIPATH_SERVER_ADDRESS=10.1.100.10
VIPAT_VIDEOIPATH_USERNAME=api-user
VIPAT_VIDEOIPATH_PASSWORD=veryStrongPassword
VIPAT_USE_HTTPS=true
VIPAT_VERIFY_SSL_CERT=false
VIPAT_LOG_LEVEL=INFO
VIPAT_ADVANCED_DRIVER_SCHEMA_CHECK=true
VIPAT_EDGE_FETCH_MODE=BATCHED
VIPAT_EDGE_MAX_FETCH_WORKERS=15
```

### Step 2: Code Example

To establish the connection, import the `VideoIPathApp` class and initialize it as follows:

```python
# Import the `VideoIPathApp` class from the videoipath_automation_tool package
from videoipath_automation_tool import VideoIPathApp

# Initialize the VideoIPathApp
app = VideoIPathApp()

# Example: Get the server version
print(app.get_server_version())
# > 2024.1.4
```

## Example 2: Establishing a Connection to the VideoIPath Server via parameters

```python
# Import the `VideoIPathApp` class from the videoipath_automation_tool package
from videoipath_automation_tool import VideoIPathApp

# Initialize the VideoIPathApp
app = VideoIPathApp(server_address="10.1.100.10", username="api-user", password="veryStrongPassword", use_https=True, verify_ssl_cert=False, log_level="DEBUG")

# Example: Get the server version
print(app.get_server_version())
# > 2024.1.4
```

## Additional Information

### Parameters

- `server_address`: The IP address or hostname of the VideoIPath Server
- `username`: Username for the API User.
- `password`: Password for the API User.
- `use_https`: Set to `True` if the VideoIPath Server uses HTTPS.
- `verify_ssl_cert`: Set to `True` if the SSL certificate should be verified.
- `log_level`: The log level for the logging module, possible values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`. If not set as a parameter or environment variable, it falls back to the root logger's level (default is set to `WARNING`).
- `environment`: The environment of the VideoIPath Server, possible values are `DEV`, `TEST`, and `PROD` (for future use)
- `advanced_driver_schema_check`: If set to `True`, the local driver schema is checked against the server's driver schema (custom settings fields).

### Environment Variables

| Variable        | Values                                          | Description                                      |
|-----------------|-------------------------------------------------|--------------------------------------------------|
| `VIPAT_ENVIRONMENT`   | `DEV`, `TEST`, `PROD`                          | Optional: Define the environment. Defaults to `PROD`. |
| `VIPAT_VIDEOIPATH_SERVER_ADDRESS` | e.g. IP `10.200.10.21` or hostname `vip.company.com` | IP address or hostname of the VideoIPath server. |
| `VIPAT_VIDEOIPATH_USERNAME` | e.g. `api_user`                               | Username for the API User.                      |
| `VIPAT_VIDEOIPATH_PASSWORD` | e.g. `very_strong_passw0rd`                    | Password for the API User.                      |
| `VIPAT_USE_HTTPS`         | `true`, `false`                                | Optional: Use HTTPS for the connection. Defaults to `true`. |
| `VIPAT_VERIFY_SSL_CERT`  | `true`, `false`                                | Optional: Verify the SSL certificate. Defaults to `true`. |
| `VIPAT_LOG_LEVEL`     | `debug`, `info`, `warning`, `error`, `critical` | Optional: Set the log level. |
| `VIPAT_ADVANCED_DRIVER_SCHEMA_CHECK` | `true`, `false` | Optional: Enable advanced driver schema checks. Defaults to `true`. |
| `VIPAT_EDGE_FETCH_MODE` | `BATCHED`, `BULK` | Optional: Defines how revision data for unidirectional edges is fetched. <br> **BATCHED** (default) performs multiple smaller, parallel requests and scales better for large topologies. <br> **BULK** (legacy) performs a single request and is only recommended for very small topologies. Defaults to `BATCHED`. |
| `VIPAT_EDGE_MAX_FETCH_WORKERS` | Integer > 1 (e.g. `15`) | Optional: Maximum number of parallel workers used for batched revision fetches. Defaults to `15`. |

## Log Levels

- `DEBUG`: Detailed information, typically of interest only when diagnosing problems
- `INFO`: Confirmation that things are working as expected
- `WARNING`: An indication that something unexpected happened, or indicative of some problem in the near future (e.g., ‘fallback used’, ‘deprecated method used’). The software is still working as expected, but future versions may not work the same way.
- `ERROR`: Due to a more serious problem, the software has not been able to perform some function.
- `CRITICAL`: Not used, reserved for future use
