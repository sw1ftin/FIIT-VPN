from random import randint
import requests
import json
from datetime import datetime, timedelta


class Marzban:
    def __init__(self, url, username, password):
        self.url = url
        self.token = self.get_token(username, password)
        self.proxies = {
            "vmess": {
                "id": "35e4e39c-7d5c-4f4b-8b71-558e4f37ff53"
            },
            "vless": {
                "id": "56609674-08db-4211-ac31-b2224ed1f05d",
                "flow": ""
            }
        }
        self.inbounds = {
            "vmess": [
                "VMess TCP",
                "VMess Websocket"
            ],
            "vless": [
                "VLESS TCP REALITY",
                "VLESS GRPC REALITY"
            ]
        }

    def get_token(self, username, password):
        response = requests.post(
            f"{self.url}/api/admin/token",
            headers={
                'accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data={
                'grant_type': '',
                'username': username,
                'password': password,
                'scope': '',
                'client_id': '',
                'client_secret': ''
            }
        )
        response.raise_for_status()
        return response.json().get('access_token')

    def create_user_profile(self, username):
        """Create a new user profile."""
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

        expire_date = (datetime.now() + timedelta(days=30)).timestamp()

        data = {
            "username": username,
            "proxies": self.proxies,
            "inbounds": self.inbounds,
            "expire": int(expire_date),  # Expiration time in seconds since epoch
            "data_limit": 0,
            "data_limit_reset_strategy": "no_reset",
            "status": "active",
            "note": "",
            "on_hold_timeout": None,
            "on_hold_expire_duration": 0
        }

        response = requests.post(f"{self.url}/api/user", headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            print("User profile created successfully:", response.json())
            return response.json()
        else:
            print("Error creating user profile:", response.status_code, response.json())
            return None

    def get_user_profile(self, username):
        """Retrieve an existing user's profile."""
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }

        response = requests.get(f"{self.url}/api/user/{username}", headers=headers)

        if response.status_code == 200:
            print("User profile retrieved successfully:", response.json())
            return response.json()
        elif response.status_code == 404:
            print(f"User profile '{username}' not found.")
            return None
        else:
            print(f"Error retrieving user profile: {response.status_code}", response.json())
            return None

    def extend_user_profile(self, username):
        """Extend an existing user's profile by one month."""
        user_profile = self.get_user_profile(username)
        if not user_profile:
            print(f"Cannot extend profile for '{username}': User not found.")
            return None

        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

        current_expire = user_profile.get('expire')
        if current_expire is None:
            new_expire_date = datetime.now() + timedelta(days=30)
        else:
            current_expire_date = datetime.fromtimestamp(current_expire)
            new_expire_date = current_expire_date + timedelta(days=30)

        new_expire_timestamp = int(new_expire_date.timestamp())

        data = {
            "proxies": user_profile.get("proxies", self.proxies),
            "inbounds": user_profile.get("inbounds", self.inbounds),
            "expire": new_expire_timestamp,
            "data_limit": user_profile.get("data_limit", 0),
            "data_limit_reset_strategy": user_profile.get("data_limit_reset_strategy", "no_reset"),
            "status": user_profile.get("status", "active"),
            "note": user_profile.get("note", ""),
            "on_hold_timeout": user_profile.get("on_hold_timeout", None),
            "on_hold_expire_duration": user_profile.get("on_hold_expire_duration", 0)
        }

        response = requests.put(f"{self.url}/api/user/{username}", headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            print(f"User profile '{username}' extended successfully:", response.json())
            return response.json()
        else:
            print(f"Error extending user profile: {response.status_code}", response.json())
            return None

    def update_user_subscription(self, username):
        """Check if user exists and extend profile if found, otherwise create new profile."""
        user_profile = self.get_user_profile(username)

        if user_profile:
            print(f"User '{username}' exists. Extending profile...")
            result = self.extend_user_profile(username)
        else:
            print(f"User '{username}' not found. Creating new profile...")
            result = self.create_user_profile(username)

        # Check if result contains 'subscription_url' and return it
        if result and 'subscription_url' in result:
            subscription_link = f"{self.url}{result['subscription_url']}"
            print(f"Subscription link for '{username}': {subscription_link}")
            return subscription_link
        else:
            print(f"No subscription link found for '{username}'.")
            return None


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    marzban = Marzban(os.getenv("MZB_URL"), os.getenv("MZB_USERNAME"), os.getenv("MZB_PASSWORD"))

    random_user = "test_shit" + str(randint(1, 1000000))
    marzban.update_user_subscription(random_user)
