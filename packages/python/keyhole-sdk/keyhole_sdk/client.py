import requests


class RuntimeBridgeClient:

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def identity(self) -> dict:
        return requests.get(f"{self.base_url}/identity").json()

    def state(self) -> dict:
        return requests.get(f"{self.base_url}/state").json()

    def realize(self, package: dict) -> dict:
        return requests.post(f"{self.base_url}/realize", json=package).json()
