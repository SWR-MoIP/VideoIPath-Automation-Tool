# Example 1: Establishing a Connection to the VideoIPath Server

The following example shows how to establish a connection to the VideoIPath Server. All business logic is implemented in the `VideoIPathApp` class. Therefore, the user only needs to import the `VideoIPathApp` class from the videoipath_automation_tool package and initialize it with the required parameters. This could be done via environment variables or directly in the code. The `VideoIPathApp` class provides all necessary methods to interact with the VideoIPath Server. Although methods are available on a lower level, it is strongly recommended to use the public methods of the `VideoIPathApp` class to interact with the VideoIPath Server. This guarantees easy handling, validation, logging, and reliability.

---

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
```

### Step 2: Code Example

To establish the connection, import the `VideoIPathApp` class and initialize it as follows:

```python
# Import the `VideoIPathApp` class from the videoipath_automation_tool package
from videoipath_automation_tool import VideoIPathApp

# Initialize the VideoIPathApp
app = VideoIPathApp()
```

## Example 2: Establishing a Connection to the VideoIPath Server via Direct Parameters

```python
# Import the `VideoIPathApp` class from the videoipath_automation_tool package
from videoipath_automation_tool import VideoIPathApp

# Initialize the VideoIPathApp
app = VideoIPathApp(server_address="10.1.100.10", username="api-user", password="veryStrongPassword", use_https=True, verify_ssl_cert=False, log_level="DEBUG")```

```

## Notes

### Parameters

- `server_address`: The IP address or hostname of the VideoIPath Server
- `username`: Username for the API User.
- `password`: Password for the API User.
- `use_https`: Set to `True` if the VideoIPath Server uses HTTPS.
- `verify_ssl_cert`: Set to `True` if the SSL certificate should be verified.
- `log_level`: The log level for the logging module, possible values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`.
- `environment`: The environment of the VideoIPath Server, possible values are `DEV`, `TEST`, and `PROD` (for future use)

### Environment Variables

| Variable        | Values                                          | Description                                      |
|-----------------|-------------------------------------------------|--------------------------------------------------|
| `VIPAT_ENVIRONMENT`   | `DEV`, `TEST`, `PROD`                          | Optional: Define the environment. Defaults to `PROD`. |
| `VIPAT_VIDEOIPATH_IP` | e.g. IP `10.200.10.21` or hostname `vip.company.com` | IP address or hostname of the VideoIPath server. |
| `VIPAT_VIDEOIPATH_USER` | e.g. `api_user`                               | Username for the API User.                      |
| `VIPAT_VIDEOIPATH_PWD` | e.g. `very_strong_passw0rd`                    | Password for the API User.                      |
| `VIPAT_HTTPS`         | `true`, `false`                                | Optional: Use HTTPS for the connection. Defaults to `false`. |
| `VIPAT_HTTPS_VERIFY`  | `true`, `false`                                | Optional: Verify the SSL certificate. Defaults to `false`. |
| `VIPAT_LOG_LEVEL`     | `debug`, `info`, `warning`, `error`, `critical` | Optional: Set the log level. Defaults to `warning`. |

## Log Levels

- `DEBUG`: Detailed information, typically of interest only when diagnosing problems
- `INFO`: Confirmation that things are working as expected
- `WARNING`: An indication that something unexpected happened, or indicative of some problem in the near future (e.g., ‘fallback used’, ‘deprecated method used’). The software is still working as expected, but future versions may not work the same way.
- `ERROR`: Due to a more serious problem, the software has not been able to perform some function.
- `CRITICAL`: Not used, reserved for future use
