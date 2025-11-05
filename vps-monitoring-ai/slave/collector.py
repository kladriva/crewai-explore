"""
Slave Collector Agent - Lightweight metrics collector for slave nodes
Collects system and Docker metrics, sends to master via gRPC
"""
import os
import time
import psutil
import docker
import socket
import platform
from datetime import datetime, timezone
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment
MASTER_HOST = os.getenv('MASTER_HOST', 'localhost')
MASTER_PORT = int(os.getenv('MASTER_PORT', '50051'))
NODE_NAME = os.getenv('NODE_NAME', socket.gethostname())
COLLECTION_INTERVAL = int(os.getenv('COLLECTION_INTERVAL', '5'))  # seconds
HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '30'))  # seconds


class MetricsCollector:
    """Collects system and Docker metrics"""
    
    def __init__(self):
        self.docker_client = None
        try:
            if os.getenv('DOCKER_DISABLED', '0') == '1':
                raise RuntimeError('Docker disabled via DOCKER_DISABLED=1')
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized")
        except Exception as e:
            logger.warning(f"Docker client initialization failed: {e}")
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level metrics (CPU, Memory, Disk)"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_total_mb = memory.total / (1024 * 1024)
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            disk_total_gb = disk.total / (1024 * 1024 * 1024)
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_used_mb": memory_used_mb,
                "memory_total_mb": memory_total_mb,
                "disk_percent": disk_percent,
                "disk_used_gb": disk_used_gb,
                "disk_total_gb": disk_total_gb,
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {}
    
    def collect_container_metrics(self) -> List[Dict[str, Any]]:
        """Collect Docker container metrics"""
        if not self.docker_client:
            return []
        
        containers_metrics = []
        
        try:
            containers = self.docker_client.containers.list(all=True)
            
            for container in containers:
                try:
                    stats = container.stats(stream=False)
                    
                    # Calculate CPU percentage robustly (handle missing precpu/percpu)
                    cpu_stats = stats.get('cpu_stats', {}) or {}
                    precpu_stats = stats.get('precpu_stats', {}) or {}
                    cpu_usage = cpu_stats.get('cpu_usage', {}) or {}
                    precpu_usage = precpu_stats.get('cpu_usage', {}) or {}
                    total = cpu_usage.get('total_usage', 0) or 0
                    pre_total = precpu_usage.get('total_usage', 0) or 0
                    system_total = cpu_stats.get('system_cpu_usage', 0) or 0
                    pre_system_total = precpu_stats.get('system_cpu_usage', 0) or 0
                    # number of CPUs
                    ncpu = (len(cpu_usage.get('percpu_usage') or [])
                            or cpu_stats.get('online_cpus')
                            or psutil.cpu_count()
                            or 1)
                    cpu_delta = max(total - pre_total, 0)
                    system_delta = max(system_total - pre_system_total, 0)
                    cpu_percent = (cpu_delta / system_delta * ncpu * 100.0) if system_delta > 0 else 0.0
                    
                    # Calculate Memory
                    mem_stats = stats.get('memory_stats', {}) or {}
                    memory_usage = mem_stats.get('usage', 0) or 0
                    memory_limit = mem_stats.get('limit', 1) or 1
                    memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0
                    memory_used_mb = memory_usage / (1024 * 1024)
                    memory_limit_mb = memory_limit / (1024 * 1024)
                    
                    # Network
                    networks = stats.get('networks', {}) or {}
                    try:
                        network_rx = sum((net.get('rx_bytes', 0) or 0) for net in networks.values()) / (1024 * 1024)
                        network_tx = sum((net.get('tx_bytes', 0) or 0) for net in networks.values()) / (1024 * 1024)
                    except Exception:
                        network_rx = 0.0
                        network_tx = 0.0
                    
                    # Container info
                    container_info = {
                        "container_id": container.id[:12],
                        "container_name": container.name,
                        "image": (container.image.tags[0] if container.image.tags else "unknown"),
                        "status": container.status,
                        "cpu_percent": round(cpu_percent, 2),
                        "memory_percent": round(memory_percent, 2),
                        "memory_used_mb": round(memory_used_mb, 2),
                        "memory_limit_mb": round(memory_limit_mb, 2),
                        "network_rx_mb": round(network_rx, 2),
                        "network_tx_mb": round(network_tx, 2),
                        "ports": [f"{k}/{v}" for k, v in (container.ports or {}).items()],
                        "created_at": int(datetime.fromisoformat(container.attrs['Created'].replace('Z', '+00:00')).timestamp() * 1000),
                        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
                    }
                    
                    containers_metrics.append(container_info)
                
                except Exception as e:
                    logger.error(f"Error collecting stats for container {container.name}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error listing containers: {e}")
        
        return containers_metrics
    
    def get_node_info(self) -> Dict[str, str]:
        """Get static node information"""
        return {
            "node_id": NODE_NAME,
            "ip_address": self.get_local_ip(),
            "hostname": socket.gethostname(),
            "os_type": platform.system(),
            "os_version": platform.release(),
            "agent_version": "1.0.0"
        }
    
    def get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"


def send_metrics_to_master(metrics: Dict[str, Any]):
    """Send metrics to master via gRPC (placeholder - requires gRPC implementation)"""
    # TODO: Implement actual gRPC client
    # For now, just log
    logger.info(f"Would send metrics: CPU={metrics['system_metrics']['cpu_percent']:.1f}%, "
                f"Memory={metrics['system_metrics']['memory_percent']:.1f}%, "
                f"Containers={len(metrics['containers'])}")
    
    # In production, this would be:
    # stub.SendMetrics(monitoring_pb2.MetricsRequest(
    #     node_info=...,
    #     system_metrics=...,
    #     containers=...
    # ))


def send_heartbeat():
    """Send heartbeat to master"""
    logger.debug(f"Sending heartbeat for node {NODE_NAME}")
    # TODO: Implement gRPC heartbeat


def main():
    """Main collector loop"""
    logger.info(f"Starting metrics collector for node: {NODE_NAME}")
    logger.info(f"Master server: {MASTER_HOST}:{MASTER_PORT}")
    logger.info(f"Collection interval: {COLLECTION_INTERVAL}s")
    
    collector = MetricsCollector()
    last_heartbeat = time.time()
    
    while True:
        try:
            # Collect metrics
            system_metrics = collector.collect_system_metrics()
            containers_metrics = collector.collect_container_metrics()
            node_info = collector.get_node_info()
            
            # Prepare payload
            metrics_payload = {
                "node_info": node_info,
                "system_metrics": system_metrics,
                "containers": containers_metrics,
                "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000)
            }
            
            # Send to master
            send_metrics_to_master(metrics_payload)
            
            # Send heartbeat if needed
            if time.time() - last_heartbeat >= HEARTBEAT_INTERVAL:
                send_heartbeat()
                last_heartbeat = time.time()
            
            # Wait before next collection
            time.sleep(COLLECTION_INTERVAL)
        
        except KeyboardInterrupt:
            logger.info("Collector stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in collector main loop: {e}", exc_info=True)
            time.sleep(COLLECTION_INTERVAL)


if __name__ == "__main__":
    main()
