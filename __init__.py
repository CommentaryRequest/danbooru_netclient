import requests
import time

__version__ = "0.1.0"

# See https://github.com/danbooru/danbooru/blob/master/app/controllers/application_controller.rb#L117
# Most other status codes are a user error and should be handled by the netclient callers.
RETRY_STATUS_CODES = [
    429, # Rate limit (RateLimiter::RateLimitError)
    500, # Server error or timeout (ActiveRecord::QueryCanceled / Rack::Timeout::RequestTimeoutException / misc errors)
    503, # Downbooru (ActiveRecord::ConnectionNotEstablished / PG::ConnectionBad), maintenance handled separately
]

class NetworkClient:
    def __init__(self, base_url, login, api_key, user_agent, request_delay):
        self.session = requests.Session()
        self.session.headers = {
            "User-Agent": user_agent
        }

        self.base_url = base_url
        self.request_delay = request_delay
        self.set_auth(login, api_key)

    def set_auth(self, login, api_key):
        self.session.auth = requests.auth.HTTPBasicAuth(login, api_key)

    def get(self, url, **kwargs):
        while True:
            try:
                response = self.session.get(f"{self.base_url}/{url}", timeout=10, **kwargs)
                time.sleep(self.request_delay)
                if response.status_code in (201, 204):
                    return {}, response
                json_resp = response.json()
                if "success" in json_resp and not json_resp["success"]:
                    print(f"Unsuccessful response ({url}): {response.text}")
                    continue
                return json_resp, response
            except requests.exceptions.JSONDecodeError:
                self.handle_json_error(response, url)
                time.sleep(0.5)
            except Exception as exc:
                print(f"Failed to fetch {url}: {exc}")
                time.sleep(0.5)

    def put(self, url, data, **kwargs):
        while True:
            try:
                response = self.session.put(f"{self.base_url}/{url}", timeout=10, json=data, **kwargs)
                time.sleep(self.request_delay)
                if response.status_code in (201, 204):
                    return {}, response
                json_resp = response.json()
                if "success" in json_resp and not json_resp["success"]:
                    print(f"Unsuccessful response (code {response.status_code} on {url}): {response.text}")
                    if response.status_code in RETRY_STATUS_CODES:
                        continue
                return json_resp, response
            except requests.exceptions.JSONDecodeError:
                self.handle_json_error(response, url)
                time.sleep(0.5)
            except Exception as exc:
                print(f"Failed to fetch {url}: {exc}")
                time.sleep(0.5)

    def handle_json_error(self, response, url):
        print(f"Server returned non-JSON response ({url}): {response.text}")
        if "<title>Downbooru</title>" in response.text:
            print("** Danbooru is down for maintenance. Retrying in 1 hour. **")
            time.sleep(3600)
        elif "CF-Ray" in response.headers:
            print(f"Cloudflare Ray ID: {response.headers["CF-Ray"]}")
