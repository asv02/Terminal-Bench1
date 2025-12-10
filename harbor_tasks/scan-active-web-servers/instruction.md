Implement a comprehensive network scanning tool in '/app/solution.py' with the following functions:

## 1. `web_scraper(ip_range: str, timeout: float) -> list[str]`
Scans a specified IPv4 network range and returns a list of active web servers.

**Behavior:**
- `ip_range` is a CIDR string (e.g., `"192.168.0.0/24"`).
- Iterate over ALL IPv4 addresses in the network, including network and broadcast addresses.
- For each IP, send an HTTP GET request to `http://<ip>/` using the given `timeout` (in seconds).
- If `response.status_code == 200`, add that IP address (as a string) to the result list.
- If the request fails (connection error, timeout, non-200 status code, etc.), skip that IP and continue.
- Return a `list[str]` of IP addresses that responded with **exactly** status code 200, in scan order.
- Raise `ValueError` if `ip_range` is not a valid IPv4 CIDR range.

## 2. `scan_with_ports(ip_range: str, ports: list[int], timeout: float) -> dict[str, list[int]]`
Scans IP addresses across multiple HTTP ports and returns active servers with their responding ports.

**Behavior:**
- `ip_range` is a CIDR string (e.g., `"10.0.0.0/28"`).
- `ports` is a list of port numbers to scan (e.g., `[80, 8080, 8000]`).
- For each IP in the range, test HTTP GET requests to `http://<ip>:<port>/` for each port.
- Return a dictionary where keys are IP addresses (strings) and values are lists of ports that returned status code 200.
- Only include IPs that have at least one responding port.
- Ports in the result lists must be sorted in ascending order.
- Raise `ValueError` if `ip_range` is invalid or if `ports` is empty.
- Raise `TypeError` if `ports` contains non-integer values.

## 3. `scan_with_headers(ip_range: str, timeout: float) -> dict[str, dict[str, str]]`
Scans IP addresses and returns server information from HTTP response headers.

**Behavior:**
- `ip_range` is a CIDR string.
- For each IP, send HTTP GET request to `http://<ip>/`.
- For IPs that return status code 200, extract the following headers from `response.headers` (case-insensitive lookup):
  - `Server` (e.g., "nginx/1.18.0")
  - `Content-Type` (e.g., "text/html")
  - `X-Powered-By` (if present)
- Return a dictionary where keys are IP addresses and values are dictionaries of header names to header values. Store all header keys in lowercase (e.g., 'server', 'content-type', 'x-powered-by'). Use `key.lower()` to compare header names case-insensitively.
- Include ALL IPs that returned status code 200, even if none of the target headers are present (use empty dict {} for such IPs).
- If a specific header is not present in the response, do not include that header key in the inner dictionary.
- Raise `ValueError` if `ip_range` is invalid.

## 4. `parallel_scan(ip_range: str, timeout: float, max_workers: int = 10) -> list[str]`
Performs parallel scanning of IP addresses for better performance on large ranges.

**Behavior:**
- Same as `web_scraper()` but uses concurrent execution with `concurrent.futures.ThreadPoolExecutor`.
- `max_workers` specifies the maximum number of concurrent threads (default: 10).
- Results must still be returned in the same order as sequential scanning (sorted by IP address).
- Raise `ValueError` if `ip_range` is invalid or if `max_workers < 1`.

## Implementation Requirements:
- **Must use `ipaddress` module**: All functions must import and use `ipaddress.IPv4Network` for CIDR parsing and IP iteration. Do not use alternative IP parsing methods.
- **Must use `requests` library**: All HTTP requests must use `requests.get()` with the timeout parameter.
- **Must use `concurrent.futures.ThreadPoolExecutor`**: The `parallel_scan()` function must use `ThreadPoolExecutor` from `concurrent.futures` for concurrent execution. Do not use other concurrency methods.
- All functions must handle network errors gracefully without raising exceptions for individual failed requests.
- Timeout values must be respected for all HTTP requests (pass `timeout` parameter to `requests.get()`).
- IP addresses in results must always be strings, not `IPv4Address` objects.
