import os
import requests

class PromClient:
    def __init__(self, base_url=None):
        self.base_url = base_url or os.getenv("PROM_URL", "http://prometheus:9090")

    def query(self, q: str):
        r = requests.get(f"{self.base_url}/api/v1/query", params={'query': q}, timeout=5)
        r.raise_for_status()
        return r.json()['data']['result']
    
    def query_range(self, q: str, start: int, end: int, step: str):
        r = requests.get(
            f"{self.base_url}/api/v1/query_range",
            params={'query': q, 'start': start, 'end': end, 'step': step},
            timeout=12
        )
        r.raise_for_status()
        return r.json().get("data", {}).get("result", [])

    # helpers (exemples)
    def cpu_usage(self):
        q = '100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)'
        return self.query(q)

    def mem_usage(self):
        q = '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'
        return self.query(q)

    def disk_usage_root(self):
        q = '100 - (node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"}) * 100'
        return self.query(q)
