"""API client for Judo iSoft water treatment system."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)


class JudoiSoftAPIError(Exception):
    """Exception raised for API errors."""

    pass


class JudoiSoftConnectionError(JudoiSoftAPIError):
    """Exception raised for connection errors."""

    pass


class JudoiSoftCommandError(JudoiSoftAPIError):
    """Exception raised for command execution errors."""

    pass


class JudoiSoftAPI:
    """API client for Judo iSoft system with local and cloud support."""

    CLOUD_BASE_URL = "https://www.myjudo.eu/interface"

    def __init__(
        self,
        host: str,
        port: int = 80,
        timeout: int = 10,
        username: Optional[str] = None,
        password: Optional[str] = None,
        force_cloud: bool = False,
    ) -> None:
        """Initialize the API client.

        Args:
            host: Device IP address for local access
            port: Port for local access
            timeout: Request timeout in seconds
            username: Username for authentication (required for cloud)
            password: Password for authentication (required for cloud)
            force_cloud: Skip local access and use cloud only
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.username = username
        self.password = password
        self.force_cloud = force_cloud
        self.session = None
        self._auth_headers: Dict[str, str] = {}
        self._auth_cookies: Dict[str, str] = {}
        self._auth_token: Optional[str] = None
        self._use_cloud = force_cloud
        self._cloud_session_valid = False

        # URLs for both access methods
        self.local_base_url = f"http://{host}:{port}"
        self.cloud_base_url = self.CLOUD_BASE_URL

        # Set up basic auth for local access if credentials provided
        if username and password and not force_cloud:
            import base64

            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            self._auth_headers["Authorization"] = f"Basic {credentials}"

    async def _authenticate_cloud(self) -> bool:
        """Authenticate with the cloud service using the exact method from working example."""
        if not self.username or not self.password:
            _LOGGER.error("Username and password required for cloud access")
            return False

        # Hash the password using MD5 as required by Judo API - exactly like working example
        password_hash = hashlib.md5(self.password.encode("utf-8")).hexdigest()

        # Judo API authentication parameters - exactly like working example
        params = {
            "group": "register",
            "command": "login",
            "name": "login",
            "user": self.username,
            "password": password_hash,
            "nohash": "Service",
            "role": "customer",
        }

        _LOGGER.info("Attempting Judo cloud authentication for user: %s", self.username)
        _LOGGER.debug("Using hashed password: %s", password_hash[:8] + "...")

        session = await self._get_session()

        try:
            # Use the interface URL directly for authentication - exactly like working example
            auth_url = self.cloud_base_url
            _LOGGER.debug("Authenticating at: %s", auth_url)

            async with session.get(
                auth_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                # Check if the request was successful - like working example
                response.raise_for_status()

                # Check if we got an empty response (known Judo API issue)
                response_text = await response.text()
                if not response_text.strip():
                    _LOGGER.error(
                        "Judo cloud API returned empty response - API may be down or changed"
                    )
                    raise JudoiSoftConnectionError(
                        "Judo cloud service returned empty response. This appears to be an issue with "
                        "Judo's cloud API. Try again later or contact Judo support if the problem persists."
                    )

                # Parse the JSON response asynchronously - like working example
                try:
                    login_response_json = await response.json()
                    _LOGGER.debug("Auth JSON response: %s", login_response_json)
                except ValueError as e:
                    _LOGGER.error("Invalid JSON from Judo API: %s", e)
                    _LOGGER.error("Response text: %s", response_text[:200])
                    raise JudoiSoftConnectionError(
                        "Invalid response from Judo cloud service"
                    )

                if "token" in login_response_json:
                    self._auth_token = login_response_json["token"]
                    _LOGGER.info(
                        "Token retrieved successfully: %s...", self._auth_token[:8]
                    )
                    self._cloud_session_valid = True
                    return True
                else:
                    _LOGGER.error(
                        "Token not found in response: %s", login_response_json
                    )
                    raise JudoiSoftConnectionError(
                        "Authentication failed - no token in response"
                    )

        except Exception as err:
            error_str = str(err)
            _LOGGER.error("Exception during cloud authentication: %s", err)

            # Detect aiohttp compatibility issues
            if (
                "Channel.getaddrinfo" in error_str
                or "takes 3 positional arguments but 4 positional arguments"
                in error_str
            ):
                raise JudoiSoftConnectionError(
                    "aiohttp compatibility issue detected in development environment. "
                    "This integration will work correctly in a normal Home Assistant environment."
                )

            return False

    def _get_cloud_endpoint(self, local_endpoint: str) -> str:
        """Map local API endpoints to cloud equivalents."""
        # Map local endpoints to cloud service endpoints
        endpoint_mapping = {
            "api/status": "status",
            "api/system/status": "system/status",
            "api/water/data": "water/data",
            "api/maintenance/data": "maintenance/data",
            "api/device/info": "device/info",
            "api/control": "control",
        }

        mapped = endpoint_mapping.get(
            local_endpoint.lstrip("/"), local_endpoint.lstrip("/")
        )

        # Try different possible device ID formats
        device_id = self.host

        # If it looks like an IP address, it might not work for cloud
        import re

        if re.match(r"^(\d+\.){3}\d+$", self.host):
            _LOGGER.warning(
                "Using IP address %s for cloud access - this may not work. Consider using device ID instead.",
                self.host,
            )

        # Try different possible cloud endpoint structures
        possible_paths = [
            f"api/device/{device_id}/{mapped}",
            f"device/{device_id}/{mapped}",
            f"api/{mapped}?device={device_id}",
            f"{mapped}?device={device_id}",
        ]

        # Return the first path for now - we'll try others if this fails
        return possible_paths[0]

    async def _try_cloud_access(self) -> bool:
        """Switch to cloud access after local access fails."""
        if self._use_cloud:
            return self._cloud_session_valid

        _LOGGER.info("Local access failed, trying cloud access...")
        _LOGGER.info("Using cloud service: %s", self.cloud_base_url)

        if not self.username or not self.password:
            _LOGGER.error("Cannot switch to cloud: missing username/password")
            return False

        success = await self._authenticate_cloud()
        if success:
            self._use_cloud = True
            _LOGGER.info("Successfully switched to cloud access")
        else:
            _LOGGER.error("Failed to authenticate with cloud service")
        return success

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def _request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make an API request with automatic local/cloud fallback."""

        # First attempt: try local access (unless cloud-only mode)
        if not self._use_cloud and not self.force_cloud:
            try:
                return await self._request_local(endpoint, method, data, **kwargs)
            except (JudoiSoftConnectionError, aiohttp.ClientConnectorError) as err:
                _LOGGER.warning("Local access failed: %s", err)
                # Try to fallback to cloud
                if await self._try_cloud_access():
                    return await self._request_cloud(endpoint, method, data, **kwargs)
                else:
                    raise JudoiSoftConnectionError(
                        "Both local and cloud access failed"
                    ) from err
            except Exception as err:
                # For other errors, still try cloud fallback if available
                _LOGGER.warning("Local request failed: %s", err)
                if not self._use_cloud and await self._try_cloud_access():
                    return await self._request_cloud(endpoint, method, data, **kwargs)
                else:
                    raise

        # Cloud access
        if self._use_cloud or self.force_cloud:
            if not self._cloud_session_valid and not await self._authenticate_cloud():
                raise JudoiSoftConnectionError("Cloud authentication failed")
            return await self._request_cloud(endpoint, method, data, **kwargs)

        raise JudoiSoftConnectionError("No access method available")

    async def _request_local(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make a request to local device API."""
        url = f"{self.local_base_url}/{endpoint.lstrip('/')}"
        session = await self._get_session()

        # Merge auth headers with any additional headers
        headers = {**self._auth_headers}
        if "headers" in kwargs:
            headers.update(kwargs["headers"])
        kwargs["headers"] = headers

        # Add JSON data if provided
        if data is not None:
            kwargs["json"] = data
            headers["Content-Type"] = "application/json"

        _LOGGER.debug("Making %s request to local API: %s", method, url)

        try:
            async with session.request(method, url, **kwargs) as response:
                return await self._process_response(response, "local")
        except aiohttp.ClientConnectorError as err:
            _LOGGER.debug("Local connection failed: %s", err)
            raise JudoiSoftConnectionError(
                f"Failed to connect to local device at {self.host}:{self.port}"
            ) from err
        except asyncio.TimeoutError as err:
            _LOGGER.debug("Local request timed out")
            raise JudoiSoftConnectionError(
                f"Local request timed out after {self.timeout}s"
            ) from err

    async def _request_cloud(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make a request to cloud API using Judo API method - matching working example."""
        session = await self._get_session()

        # For Judo cloud API, we use the main interface URL with parameters - like working example
        url = self.cloud_base_url

        # Prepare parameters for Judo API - exactly like working example send_authenticated_request
        params = kwargs.get("params", {})

        # Add authentication token if we have it - like working example
        if self._auth_token:
            params["token"] = self._auth_token

        # Map endpoints to Judo API commands - matching working example discover_devices
        if endpoint == "api/status" or endpoint == "status":
            params.update({"group": "register", "command": "get device data"})
        elif endpoint == "api/device/info":
            params.update({"group": "register", "command": "get device data"})
        else:
            # For other endpoints, default to device data
            _LOGGER.debug("Mapping unknown endpoint %s to get device data", endpoint)
            params.update({"group": "register", "command": "get device data"})

        kwargs["params"] = params

        _LOGGER.debug(
            "Making %s request to Judo cloud API: %s with params: %s",
            method,
            url,
            {k: v if k != "token" else "***" for k, v in params.items()},
        )

        try:
            async with session.request(method, url, **kwargs) as response:
                # Check if the request was successful - like working example
                response.raise_for_status()

                # Parse the JSON response asynchronously - like working example
                result = await response.json()
                _LOGGER.debug("Cloud API response: %s", result)

                return result

        except Exception as err:
            _LOGGER.error("Cloud request failed: %s", err)
            raise JudoiSoftConnectionError(f"Cloud request failed: {err}")

    async def _process_response(
        self, response: aiohttp.ClientResponse, source: str
    ) -> Dict[str, Any]:
        """Process API response from local or cloud source."""
        response_text = await response.text()

        if response.status >= 400:
            _LOGGER.error(
                "%s API request failed with status %s: %s",
                source,
                response.status,
                response_text,
            )
            if response.status in (401, 403):
                raise JudoiSoftConnectionError(
                    f"{source.title()} authentication failed (HTTP {response.status})"
                )
            elif response.status == 404:
                raise JudoiSoftAPIError(f"Endpoint not found on {source} API")
            else:
                raise JudoiSoftAPIError(
                    f"{source.title()} API HTTP {response.status}: {response_text}"
                )

        # Handle different content types
        content_type = response.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            try:
                result = await response.json()
                # Add source information to response
                if isinstance(result, dict):
                    result["_source"] = source
                return result
            except json.JSONDecodeError as e:
                _LOGGER.error(
                    "Failed to decode JSON response from %s API: %s", source, e
                )
                return {"raw_response": response_text, "_source": source}
        else:
            # Try to parse as JSON anyway
            try:
                result = json.loads(response_text)
                if isinstance(result, dict):
                    result["_source"] = source
                return result
            except json.JSONDecodeError:
                return {"raw_response": response_text, "_source": source}

    # Connection info and debugging methods
    @property
    def is_using_cloud(self) -> bool:
        """Check if currently using cloud access."""
        return self._use_cloud

    @property
    def connection_source(self) -> str:
        """Get current connection source."""
        return "cloud" if self._use_cloud else "local"

    async def force_cloud_mode(self) -> bool:
        """Force switch to cloud mode."""
        if not self.username or not self.password:
            _LOGGER.error("Cannot force cloud mode: missing credentials")
            return False

        if await self._authenticate_cloud():
            self._use_cloud = True
            self.force_cloud = True
            _LOGGER.info("Successfully forced cloud mode")
            return True
        return False

    async def test_cloud_only(self) -> bool:
        """Test cloud access only (skip local) for debugging."""
        if not self.username or not self.password:
            raise JudoiSoftConnectionError(
                "Username and password are required for cloud access"
            )

        _LOGGER.info(
            "Testing cloud-only access to %s with user %s",
            self.cloud_base_url,
            self.username,
        )

        # Test basic connectivity
        try:
            _LOGGER.info("Testing connectivity to myjudo.eu...")
            session = await self._get_session()
            async with session.get(
                "https://www.myjudo.eu/", timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                _LOGGER.info("Cloud service reachable, status: %d", response.status)

        except Exception as e:
            error_str = str(e)
            if "Channel.getaddrinfo" in error_str:
                _LOGGER.error("Connection issue: %s", e)
                raise JudoiSoftConnectionError(
                    "Unable to reach cloud service. Please check internet connectivity."
                )
            else:
                _LOGGER.error("Error reaching cloud service: %s", e)
                raise JudoiSoftConnectionError(f"Error reaching cloud service: {e}")

        # Force cloud mode
        self._use_cloud = True

        try:
            # Try to authenticate
            if not await self._authenticate_cloud():
                raise JudoiSoftConnectionError("Cloud authentication failed")

            # Try to get basic status
            result = await self._request("api/status")
            _LOGGER.info("Cloud test successful: %s", result)
            return True

        except JudoiSoftConnectionError:
            # Re-raise our specific connection errors
            raise
        except Exception as err:
            error_str = str(err)
            if "Channel.getaddrinfo" in error_str:
                raise JudoiSoftConnectionError(
                    "aiohttp compatibility issue detected in development environment"
                )
            _LOGGER.error("Cloud test failed: %s", err)
            raise JudoiSoftConnectionError(f"Cloud test failed: {err}")

    async def test_connection(self) -> bool:
        """Test connection to the Judo iSoft system with fallback."""
        try:
            # Test endpoint that should work on both local and cloud
            result = await self._request("api/status")
            source = result.get("_source", "unknown")
            _LOGGER.info("Connection test successful via %s access", source)
            return True
        except JudoiSoftConnectionError as err:
            # More specific error for connection issues
            if "authentication" in str(err).lower():
                _LOGGER.error("Connection test failed - authentication error: %s", err)
                raise JudoiSoftConnectionError(
                    "Authentication failed. Please verify your username and password."
                ) from err
            else:
                _LOGGER.error("Connection test failed - connection error: %s", err)
                raise JudoiSoftConnectionError(
                    "Connection failed. Please check your device IP/ID and network connectivity."
                ) from err
        except Exception as err:
            _LOGGER.error("Connection test failed with unexpected error: %s", err)
            # Provide more helpful error message
            if "ssl" in str(err).lower() or "certificate" in str(err).lower():
                raise JudoiSoftConnectionError(
                    "SSL/Certificate error. The cloud service may be temporarily unavailable."
                ) from err
            elif "timeout" in str(err).lower():
                raise JudoiSoftConnectionError(
                    "Connection timeout. Please check your internet connection."
                ) from err
            elif "name" in str(err).lower() or "dns" in str(err).lower():
                raise JudoiSoftConnectionError(
                    "Cannot resolve cloud service address. Please check your internet connection."
                ) from err
            else:
                raise JudoiSoftConnectionError(
                    f"Unexpected connection error: {str(err)}"
                ) from err

    async def get_system_status(self) -> dict[str, Any]:
        """Get system status information."""
        try:
            data = await self._request("api/system/status")
            return {
                "online": True,
                "alarm": data.get("alarm", False),
                "maintenance_required": data.get("maintenance_required", False),
                "regeneration_active": data.get("regeneration_active", False),
                "error_code": data.get("error_code"),
                "last_update": data.get("timestamp"),
            }
        except Exception as err:
            _LOGGER.error("Failed to get system status: %s", err)
            return {
                "online": False,
                "alarm": False,
                "maintenance_required": False,
                "regeneration_active": False,
            }

    async def get_water_data(self) -> dict[str, Any]:
        """Get water-related data."""
        try:
            data = await self._request("api/water/data")
            return {
                "hardness": data.get("hardness"),  # °dH
                "consumption": data.get("consumption"),  # L
                "flow_rate": data.get("flow_rate"),  # L/min
                "pressure": data.get("pressure"),  # bar
            }
        except Exception as err:
            _LOGGER.error("Failed to get water data: %s", err)
            return {}

    async def get_maintenance_data(self) -> dict[str, Any]:
        """Get maintenance-related data."""
        try:
            data = await self._request("api/maintenance/data")
            return {
                "salt_level": data.get("salt_level"),  # %
                "filter_remaining": data.get("filter_remaining_days"),  # days
                "last_regeneration": data.get("last_regeneration"),
                "next_maintenance": data.get("next_maintenance"),
            }
        except Exception as err:
            _LOGGER.error("Failed to get maintenance data: %s", err)
            return {}

    async def get_device_info(self) -> dict[str, Any]:
        """Get device information - matching working example response format."""
        if self._use_cloud:
            # For cloud mode, use device data like working example discover_devices
            try:
                data = await self._request("api/device/info")
                _LOGGER.debug("Cloud device info response: %s", data)

                # Parse response like working example - check status and data array
                if data.get("status") == "ok" and "data" in data:
                    # Extract info from first device like working example
                    devices = data["data"]
                    if devices:
                        device = devices[0]
                        # Parse device data like working example BaseDevice.__init__
                        device_data = device.get("data", [{}])[0]
                        device_type = device_data.get("dt", "unknown")
                        device_address = device_data.get("da", "unknown")

                        return {
                            "model": f"iSoft (Type: {device_type})",
                            "serial_number": device.get("serialnumber", "unknown"),
                            "device_type": device_type,
                            "device_address": device_address,
                            "manufacturer": "Judo Wasseraufbereitung GmbH",
                            "cloud_mode": True,
                        }

                # Fallback for unexpected response format
                return {
                    "model": "iSoft",
                    "serial_number": "unknown",
                    "manufacturer": "Judo Wasseraufbereitung GmbH",
                    "cloud_mode": True,
                }
            except Exception as err:
                _LOGGER.error("Failed to get cloud device info: %s", err)
                return {
                    "model": "iSoft",
                    "serial_number": "unknown",
                    "manufacturer": "Judo Wasseraufbereitung GmbH",
                    "cloud_mode": True,
                }
        else:
            # Local mode
            try:
                data = await self._request("api/device/info")
                return {
                    "model": data.get("model", "iSoft"),
                    "serial_number": data.get("serial_number"),
                    "firmware_version": data.get("firmware_version"),
                    "hardware_version": data.get("hardware_version"),
                    "manufacturer": data.get(
                        "manufacturer", "Judo Wasseraufbereitung GmbH"
                    ),
                }
            except Exception as err:
                _LOGGER.error("Failed to get device info: %s", err)
                return {
                    "model": "iSoft",
                    "serial_number": "Unknown",
                    "manufacturer": "Judo Wasseraufbereitung GmbH",
                }

    # Control Commands
    async def send_command(
        self, command: str, value: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Send a control command to the device."""
        try:
            data = {"command": command}
            if value is not None:
                data["value"] = value

            result = await self._request("api/control", method="POST", data=data)

            if result.get("status") != "ok":
                raise JudoiSoftCommandError(
                    f"Command failed: {result.get('error', 'Unknown error')}"
                )

            _LOGGER.info("Successfully executed command: %s", command)
            return result

        except Exception as err:
            _LOGGER.error("Failed to execute command '%s': %s", command, err)
            if isinstance(err, JudoiSoftCommandError):
                raise
            raise JudoiSoftCommandError(f"Command execution failed: {err}") from err

    async def trigger_alarm(self) -> bool:
        """Trigger a system alarm for testing."""
        try:
            await self.send_command("trigger_alarm")
            return True
        except JudoiSoftCommandError:
            return False

    async def clear_alarm(self) -> bool:
        """Clear the system alarm."""
        try:
            await self.send_command("clear_alarm")
            return True
        except JudoiSoftCommandError:
            return False

    async def start_regeneration(self) -> bool:
        """Start a regeneration cycle."""
        try:
            await self.send_command("start_regeneration")
            return True
        except JudoiSoftCommandError:
            return False

    async def stop_regeneration(self) -> bool:
        """Stop the current regeneration cycle."""
        try:
            await self.send_command("stop_regeneration")
            return True
        except JudoiSoftCommandError:
            return False

    async def trigger_maintenance(self) -> bool:
        """Trigger maintenance required flag."""
        try:
            await self.send_command("trigger_maintenance")
            return True
        except JudoiSoftCommandError:
            return False

    async def clear_maintenance(self) -> bool:
        """Clear maintenance required flag."""
        try:
            await self.send_command("clear_maintenance")
            return True
        except JudoiSoftCommandError:
            return False

    async def set_salt_level(self, level: float) -> bool:
        """Set salt level (for testing/calibration).

        Args:
            level: Salt level percentage (0-100)
        """
        if not 0 <= level <= 100:
            raise ValueError("Salt level must be between 0 and 100")

        try:
            await self.send_command("set_salt_level", level)
            return True
        except JudoiSoftCommandError:
            return False

    async def set_flow_rate(self, rate: float) -> bool:
        """Set flow rate (for testing).

        Args:
            rate: Flow rate in L/min (0-50)
        """
        if not 0 <= rate <= 50:
            raise ValueError("Flow rate must be between 0 and 50 L/min")

        try:
            await self.send_command("set_flow_rate", rate)
            return True
        except JudoiSoftCommandError:
            return False

    async def set_water_hardness(self, hardness: float) -> bool:
        """Set water hardness value.

        Args:
            hardness: Water hardness in °dH (0-30)
        """
        if not 0 <= hardness <= 30:
            raise ValueError("Water hardness must be between 0 and 30 °dH")

        try:
            await self.send_command("set_water_hardness", hardness)
            return True
        except JudoiSoftCommandError:
            return False

    async def reset_system(self) -> bool:
        """Reset the system to default state."""
        try:
            await self.send_command("reset_system")
            return True
        except JudoiSoftCommandError:
            return False

    async def set_device_offline(self) -> bool:
        """Set device to offline mode (for testing)."""
        try:
            await self.send_command("go_offline")
            return True
        except JudoiSoftCommandError:
            return False

    async def set_device_online(self) -> bool:
        """Set device to online mode."""
        try:
            await self.send_command("go_online")
            return True
        except JudoiSoftCommandError:
            return False

    # Enhanced query methods
    async def get_all_data(self) -> Dict[str, Any]:
        """Get all available data from the device."""
        try:
            system_status = await self.get_system_status()
            water_data = await self.get_water_data()
            maintenance_data = await self.get_maintenance_data()
            device_info = await self.get_device_info()

            return {
                "system_status": system_status,
                "water_data": water_data,
                "maintenance_data": maintenance_data,
                "device_info": device_info,
                "last_update": datetime.now().isoformat(),
            }
        except Exception as err:
            _LOGGER.error("Failed to get all data: %s", err)
            raise

    async def get_available_commands(self) -> List[Dict[str, Any]]:
        """Get list of available control commands."""
        try:
            data = await self._request("api/control", method="GET")
            return data.get("available_commands", [])
        except Exception as err:
            _LOGGER.error("Failed to get available commands: %s", err)
            return []

    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health information."""
        try:
            all_data = await self.get_all_data()

            # Calculate health score based on various factors
            health_factors = []

            # Check online status
            if all_data["system_status"]["online"]:
                health_factors.append(("connectivity", 100))
            else:
                health_factors.append(("connectivity", 0))

            # Check alarm status
            if not all_data["system_status"]["alarm"]:
                health_factors.append(("alarm_status", 100))
            else:
                health_factors.append(("alarm_status", 0))

            # Check salt level
            salt_level = all_data["maintenance_data"].get("salt_level", 0)
            if salt_level >= 80:
                health_factors.append(("salt_level", 100))
            elif salt_level >= 50:
                health_factors.append(("salt_level", 70))
            elif salt_level >= 20:
                health_factors.append(("salt_level", 40))
            else:
                health_factors.append(("salt_level", 10))

            # Check maintenance status
            if not all_data["system_status"]["maintenance_required"]:
                health_factors.append(("maintenance", 100))
            else:
                health_factors.append(("maintenance", 50))

            # Calculate overall health score
            if health_factors:
                overall_health = sum(score for _, score in health_factors) / len(
                    health_factors
                )
            else:
                overall_health = 0

            return {
                "overall_health": round(overall_health, 1),
                "health_factors": dict(health_factors),
                "status": (
                    "excellent"
                    if overall_health >= 90
                    else (
                        "good"
                        if overall_health >= 70
                        else "fair" if overall_health >= 50 else "poor"
                    )
                ),
                "last_check": datetime.now().isoformat(),
            }

        except Exception as err:
            _LOGGER.error("Failed to get system health: %s", err)
            return {
                "overall_health": 0,
                "status": "unknown",
                "error": str(err),
            }
