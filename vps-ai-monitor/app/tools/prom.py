import requests

class PromClient:
    def __init__(self, base_url=None):
        self.base_url = base_url or os.getenv("PROM_URL", "http://localhost:9091")
    
    def query(self, q: str):
        r = requests.get(f"{self.base_url}/api/v1/query", params={'query': q}, timeout=5)
        r.raise_for_status()
        return r.json()['data']['result']

    # Exemples de helpers
    def cpu_usage(self):
      # moyenne CPU sur 1m
      q = '100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)'
      return self.query(q)

    def mem_usage(self):
      q = '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'
      return self.query(q)

    def disk_usage_root(self):
      q = '100 - (node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"}) * 100'
      return self.query(q)
