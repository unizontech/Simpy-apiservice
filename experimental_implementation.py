#!/usr/bin/env python3
"""
Microservices Performance Simulation System

A comprehensive SimPy-based simulation system that models a 10-server microservice
architecture with realistic resource constraints, request patterns, and performance metrics.

Author: Claude Code
Python Version: 3.8+
Dependencies: simpy>=4.0, numpy>=1.24
"""

import simpy
import random
import numpy as np
import time
import json
from typing import Dict, List, Tuple, Optional, Any, NamedTuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, deque
import threading
import logging
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RequestPattern(Enum):
    """Request pattern types with their probability weights."""
    SIMPLE_READ = ("simple_read", 0.40, "Lightweight read operation")
    USER_AUTH = ("user_auth", 0.25, "User authentication with parallel auth/policy")
    DATA_PROCESSING = ("data_processing", 0.20, "Heavy data processing with DB")
    FILE_UPLOAD = ("file_upload", 0.08, "Large file upload with storage")
    ANALYTICS = ("analytics", 0.05, "Complex analytics processing")
    ADMIN_TASK = ("admin_task", 0.02, "Administrative system-wide task")
    
    def __init__(self, pattern_id: str, probability: float, description: str):
        self.pattern_id = pattern_id
        self.probability = probability
        self.description = description

@dataclass
class ServerConfig:
    """Server resource configuration."""
    name: str
    cpu_threads: int
    ram_gb: int
    network_gbps: float = 1.0
    disk_queue_size: int = 16

@dataclass
class ResourceUsage:
    """Resource usage specification for operations."""
    cpu_time_ms: float = 0.0
    ram_mb: float = 0.0
    disk_operations: int = 0
    network_mb: float = 0.0

class ServerMetrics(NamedTuple):
    """Per-server metrics snapshot."""
    timestamp: float
    cpu_usage: int
    cpu_utilization: float
    ram_usage: float
    ram_utilization: float
    disk_queue_length: int
    active_requests: int
    requests_started: int
    requests_completed: int
    pattern_distribution: Dict[str, int]

class GlobalMetrics(NamedTuple):
    """System-wide metrics snapshot."""
    timestamp: float
    total_requests: int
    completed_requests: int
    failed_requests: int
    throughput_per_sec: float
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    success_rate: float
    pattern_success_rates: Dict[str, float]
    pattern_avg_times: Dict[str, float]

class Server:
    """Individual microservice server with realistic resource modeling."""
    
    def __init__(self, env: simpy.Environment, config: ServerConfig):
        self.env = env
        self.config = config
        self.name = config.name
        
        # Resource modeling using SimPy primitives
        self.cpu = simpy.PreemptiveResource(env, capacity=config.cpu_threads)
        self.ram = simpy.Container(env, capacity=config.ram_gb * 1024)  # MB
        self.disk = simpy.Resource(env, capacity=config.disk_queue_size)
        self.network_bandwidth = config.network_gbps * 1024  # Mbps
        
        # Metrics tracking
        self.active_requests = 0
        self.requests_started = 0
        self.requests_completed = 0
        self.pattern_counts = defaultdict(int)
        
        # Thread-safe metrics updates
        self._metrics_lock = threading.Lock()
        
        logger.info(f"Initialized server {self.name} with {config.cpu_threads} CPUs, {config.ram_gb}GB RAM")
    
    @contextmanager
    def request_context(self, pattern: RequestPattern):
        """Context manager for request lifecycle tracking."""
        with self._metrics_lock:
            self.active_requests += 1
            self.requests_started += 1
            self.pattern_counts[pattern.pattern_id] += 1
        
        try:
            yield
        finally:
            with self._metrics_lock:
                self.active_requests -= 1
                self.requests_completed += 1
    
    def calculate_network_delay(self, data_mb: float) -> float:
        """Calculate realistic network transfer delay based on bandwidth."""
        if data_mb <= 0:
            return 0.0
        
        # Convert MB to Mbits and calculate transfer time
        data_mbits = data_mb * 8
        transfer_time = data_mbits / self.network_bandwidth
        
        # Add realistic network overhead (5-15ms base + jitter)
        overhead = random.uniform(0.005, 0.015)
        jitter = random.normalvariate(0, 0.002)  # 2ms std dev
        
        return max(0, transfer_time + overhead + jitter)
    
    def process_request(self, resource_usage: ResourceUsage, priority: int = 1):
        """Process a request with specified resource usage."""
        ram_request = None
        disk_requests = []
        cpu_req = None
        
        try:
            # Network delay (if data transfer required)
            if resource_usage.network_mb > 0:
                network_delay = self.calculate_network_delay(resource_usage.network_mb)
                yield self.env.timeout(network_delay)
            
            # RAM allocation (if required)
            if resource_usage.ram_mb > 0:
                if resource_usage.ram_mb <= self.ram.capacity:
                    ram_request = self.ram.get(resource_usage.ram_mb)
                    yield ram_request
            
            # Disk I/O (if required)
            if resource_usage.disk_operations > 0:
                for _ in range(min(resource_usage.disk_operations, 10)):  # Limit disk ops
                    disk_req = self.disk.request()
                    disk_requests.append(disk_req)
                    yield disk_req
                    # Simulate disk operation time
                    yield self.env.timeout(random.uniform(0.001, 0.010))  # 1-10ms per operation
            
            # CPU processing
            if resource_usage.cpu_time_ms > 0:
                cpu_req = self.cpu.request(priority=priority)
                yield cpu_req
                
                # Simulate CPU-bound processing
                processing_time = resource_usage.cpu_time_ms / 1000.0
                # Add realistic CPU processing variance
                actual_time = max(0.001, random.normalvariate(processing_time, processing_time * 0.1))
                yield self.env.timeout(actual_time)
            
        finally:
            # Clean up resources
            if cpu_req:
                self.cpu.release(cpu_req)
            for disk_req in reversed(disk_requests):
                self.disk.release(disk_req)
            if ram_request:
                yield self.ram.put(resource_usage.ram_mb)
    
    def get_metrics_snapshot(self) -> ServerMetrics:
        """Get current metrics snapshot for this server."""
        with self._metrics_lock:
            cpu_util = (self.cpu.count / self.cpu.capacity) * 100 if self.cpu.capacity > 0 else 0
            ram_used = self.ram.capacity - self.ram.level
            ram_util = (ram_used / self.ram.capacity) * 100 if self.ram.capacity > 0 else 0
            
            return ServerMetrics(
                timestamp=self.env.now,
                cpu_usage=self.cpu.count,
                cpu_utilization=cpu_util,
                ram_usage=ram_used,
                ram_utilization=ram_util,
                disk_queue_length=len(self.disk.queue),
                active_requests=self.active_requests,
                requests_started=self.requests_started,
                requests_completed=self.requests_completed,
                pattern_distribution=dict(self.pattern_counts)
            )

class RequestPatternProcessor:
    """Handles different request patterns and their routing through the microservice architecture."""
    
    def __init__(self, env: simpy.Environment, servers: Dict[str, Server]):
        self.env = env
        self.servers = servers
        
        # Pre-calculate weighted choices for performance
        patterns = list(RequestPattern)
        self.pattern_choices = patterns
        self.pattern_weights = [p.probability for p in patterns]
        
        logger.info("Initialized request pattern processor")
    
    def select_pattern(self) -> RequestPattern:
        """Select a request pattern based on weighted probabilities."""
        return np.random.choice(self.pattern_choices, p=self.pattern_weights)
    
    def simple_read_pattern(self, request_id: str):
        """Simple read operation: Nginx -> APP1 -> Service -> APP2"""
        try:
            with self.servers['nginx'].request_context(RequestPattern.SIMPLE_READ):
                yield self.env.process(self.servers['nginx'].process_request(
                    ResourceUsage(cpu_time_ms=2, ram_mb=4, network_mb=0.1)
                ))
            
            with self.servers['app1'].request_context(RequestPattern.SIMPLE_READ):
                yield self.env.process(self.servers['app1'].process_request(
                    ResourceUsage(cpu_time_ms=5, ram_mb=16, network_mb=0.5)
                ))
            
            with self.servers['service'].request_context(RequestPattern.SIMPLE_READ):
                yield self.env.process(self.servers['service'].process_request(
                    ResourceUsage(cpu_time_ms=15, ram_mb=32, disk_operations=1)
                ))
            
            with self.servers['app2'].request_context(RequestPattern.SIMPLE_READ):
                yield self.env.process(self.servers['app2'].process_request(
                    ResourceUsage(cpu_time_ms=8, ram_mb=24, network_mb=1.0)
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"simple_read {request_id} failed: {e}")
            return False
    
    def user_auth_pattern(self, request_id: str):
        """User authentication: Nginx -> APP1 -> (Auth + Policy parallel) -> Service -> APP2"""
        try:
            with self.servers['nginx'].request_context(RequestPattern.USER_AUTH):
                yield self.env.process(self.servers['nginx'].process_request(
                    ResourceUsage(cpu_time_ms=3, ram_mb=6, network_mb=0.2)
                ))
            
            with self.servers['app1'].request_context(RequestPattern.USER_AUTH):
                yield self.env.process(self.servers['app1'].process_request(
                    ResourceUsage(cpu_time_ms=10, ram_mb=32, network_mb=0.5)
                ))
            
            # Parallel Auth and Policy processing
            auth_proc = self.env.process(self._auth_subprocess())
            policy_proc = self.env.process(self._policy_subprocess())
            yield auth_proc & policy_proc
            
            with self.servers['service'].request_context(RequestPattern.USER_AUTH):
                yield self.env.process(self.servers['service'].process_request(
                    ResourceUsage(cpu_time_ms=25, ram_mb=64, disk_operations=2)
                ))
            
            with self.servers['app2'].request_context(RequestPattern.USER_AUTH):
                yield self.env.process(self.servers['app2'].process_request(
                    ResourceUsage(cpu_time_ms=12, ram_mb=48, network_mb=1.5)
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"user_auth {request_id} failed: {e}")
            return False
    
    def _auth_subprocess(self):
        """Authentication subprocess."""
        with self.servers['auth'].request_context(RequestPattern.USER_AUTH):
            yield self.env.process(self.servers['auth'].process_request(
                ResourceUsage(cpu_time_ms=50, ram_mb=128, disk_operations=1)
            ))
    
    def _policy_subprocess(self):
        """Policy validation subprocess."""
        with self.servers['policy'].request_context(RequestPattern.USER_AUTH):
            yield self.env.process(self.servers['policy'].process_request(
                ResourceUsage(cpu_time_ms=30, ram_mb=96, disk_operations=1)
            ))
    
    def data_processing_pattern(self, request_id: str):
        """Data processing: Nginx -> APP1 -> Service -> DB -> ServiceHub -> APP2"""
        try:
            with self.servers['nginx'].request_context(RequestPattern.DATA_PROCESSING):
                yield self.env.process(self.servers['nginx'].process_request(
                    ResourceUsage(cpu_time_ms=4, ram_mb=8, network_mb=2.0)
                ))
            
            with self.servers['app1'].request_context(RequestPattern.DATA_PROCESSING):
                yield self.env.process(self.servers['app1'].process_request(
                    ResourceUsage(cpu_time_ms=20, ram_mb=128, network_mb=5.0)
                ))
            
            with self.servers['service'].request_context(RequestPattern.DATA_PROCESSING):
                yield self.env.process(self.servers['service'].process_request(
                    ResourceUsage(cpu_time_ms=100, ram_mb=256, disk_operations=5)
                ))
            
            with self.servers['db'].request_context(RequestPattern.DATA_PROCESSING):
                yield self.env.process(self.servers['db'].process_request(
                    ResourceUsage(cpu_time_ms=200, ram_mb=512, disk_operations=10)
                ))
            
            with self.servers['servicehub'].request_context(RequestPattern.DATA_PROCESSING):
                yield self.env.process(self.servers['servicehub'].process_request(
                    ResourceUsage(cpu_time_ms=80, ram_mb=256, disk_operations=3)
                ))
            
            with self.servers['app2'].request_context(RequestPattern.DATA_PROCESSING):
                yield self.env.process(self.servers['app2'].process_request(
                    ResourceUsage(cpu_time_ms=30, ram_mb=128, network_mb=8.0)
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"data_processing {request_id} failed: {e}")
            return False
    
    def file_upload_pattern(self, request_id: str):
        """File upload: Nginx -> APP1 -> Auth -> Service -> (S3 + Logger parallel) -> APP2"""
        try:
            file_size_mb = random.uniform(10, 100)  # Reduced file sizes for testing
            
            with self.servers['nginx'].request_context(RequestPattern.FILE_UPLOAD):
                yield self.env.process(self.servers['nginx'].process_request(
                    ResourceUsage(cpu_time_ms=20, ram_mb=64, network_mb=file_size_mb)
                ))
            
            with self.servers['app1'].request_context(RequestPattern.FILE_UPLOAD):
                yield self.env.process(self.servers['app1'].process_request(
                    ResourceUsage(cpu_time_ms=50, ram_mb=256, network_mb=file_size_mb)
                ))
            
            with self.servers['auth'].request_context(RequestPattern.FILE_UPLOAD):
                yield self.env.process(self.servers['auth'].process_request(
                    ResourceUsage(cpu_time_ms=80, ram_mb=128, disk_operations=2)
                ))
            
            with self.servers['service'].request_context(RequestPattern.FILE_UPLOAD):
                yield self.env.process(self.servers['service'].process_request(
                    ResourceUsage(cpu_time_ms=100, ram_mb=512, disk_operations=5)
                ))
            
            # Parallel S3 storage and logging
            s3_proc = self.env.process(self._s3_subprocess(file_size_mb))
            logger_proc = self.env.process(self._logger_subprocess())
            yield s3_proc & logger_proc
            
            with self.servers['app2'].request_context(RequestPattern.FILE_UPLOAD):
                yield self.env.process(self.servers['app2'].process_request(
                    ResourceUsage(cpu_time_ms=20, ram_mb=64, network_mb=2.0)
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"file_upload {request_id} failed: {e}")
            return False
    
    def _s3_subprocess(self, file_size_mb: float):
        """S3 storage subprocess."""
        with self.servers['s3'].request_context(RequestPattern.FILE_UPLOAD):
            yield self.env.process(self.servers['s3'].process_request(
                ResourceUsage(cpu_time_ms=200, ram_mb=256, disk_operations=10, network_mb=file_size_mb)
            ))
    
    def _logger_subprocess(self):
        """Logging subprocess."""
        with self.servers['logger'].request_context(RequestPattern.FILE_UPLOAD):
            yield self.env.process(self.servers['logger'].process_request(
                ResourceUsage(cpu_time_ms=20, ram_mb=32, disk_operations=3)
            ))
    
    def analytics_pattern(self, request_id: str):
        """Analytics: Complex processing with parallel operations"""
        try:
            with self.servers['nginx'].request_context(RequestPattern.ANALYTICS):
                yield self.env.process(self.servers['nginx'].process_request(
                    ResourceUsage(cpu_time_ms=10, ram_mb=32, network_mb=5.0)
                ))
            
            with self.servers['app1'].request_context(RequestPattern.ANALYTICS):
                yield self.env.process(self.servers['app1'].process_request(
                    ResourceUsage(cpu_time_ms=50, ram_mb=512, network_mb=10.0)
                ))
            
            # Parallel Service and DB processing
            service_proc = self.env.process(self._analytics_service_subprocess())
            db_proc = self.env.process(self._analytics_db_subprocess())
            yield service_proc & db_proc
            
            with self.servers['servicehub'].request_context(RequestPattern.ANALYTICS):
                yield self.env.process(self.servers['servicehub'].process_request(
                    ResourceUsage(cpu_time_ms=300, ram_mb=512, disk_operations=8)
                ))
            
            with self.servers['app2'].request_context(RequestPattern.ANALYTICS):
                yield self.env.process(self.servers['app2'].process_request(
                    ResourceUsage(cpu_time_ms=80, ram_mb=256, network_mb=15.0)
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"analytics {request_id} failed: {e}")
            return False
    
    def _analytics_service_subprocess(self):
        """Analytics service subprocess."""
        with self.servers['service'].request_context(RequestPattern.ANALYTICS):
            yield self.env.process(self.servers['service'].process_request(
                ResourceUsage(cpu_time_ms=200, ram_mb=512, disk_operations=8)
            ))
    
    def _analytics_db_subprocess(self):
        """Analytics database subprocess."""
        with self.servers['db'].request_context(RequestPattern.ANALYTICS):
            yield self.env.process(self.servers['db'].process_request(
                ResourceUsage(cpu_time_ms=300, ram_mb=1024, disk_operations=15)
            ))
    
    def admin_task_pattern(self, request_id: str):
        """Admin task: Full system utilization"""
        try:
            with self.servers['nginx'].request_context(RequestPattern.ADMIN_TASK):
                yield self.env.process(self.servers['nginx'].process_request(
                    ResourceUsage(cpu_time_ms=50, ram_mb=128, network_mb=20.0)
                ))
            
            with self.servers['app1'].request_context(RequestPattern.ADMIN_TASK):
                yield self.env.process(self.servers['app1'].process_request(
                    ResourceUsage(cpu_time_ms=100, ram_mb=512, network_mb=50.0)
                ))
            
            # Multiple parallel operations
            auth_proc = self.env.process(self._admin_auth_subprocess())
            policy_proc = self.env.process(self._admin_policy_subprocess())
            service_proc = self.env.process(self._admin_service_subprocess())
            yield auth_proc & policy_proc & service_proc
            
            with self.servers['db'].request_context(RequestPattern.ADMIN_TASK):
                yield self.env.process(self.servers['db'].process_request(
                    ResourceUsage(cpu_time_ms=500, ram_mb=1024, disk_operations=20)
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"admin_task {request_id} failed: {e}")
            return False
    
    def _admin_auth_subprocess(self):
        """Admin authentication subprocess."""
        with self.servers['auth'].request_context(RequestPattern.ADMIN_TASK):
            yield self.env.process(self.servers['auth'].process_request(
                ResourceUsage(cpu_time_ms=200, ram_mb=256, disk_operations=5)
            ))
    
    def _admin_policy_subprocess(self):
        """Admin policy subprocess."""
        with self.servers['policy'].request_context(RequestPattern.ADMIN_TASK):
            yield self.env.process(self.servers['policy'].process_request(
                ResourceUsage(cpu_time_ms=150, ram_mb=192, disk_operations=4)
            ))
    
    def _admin_service_subprocess(self):
        """Admin service subprocess."""
        with self.servers['service'].request_context(RequestPattern.ADMIN_TASK):
            yield self.env.process(self.servers['service'].process_request(
                ResourceUsage(cpu_time_ms=400, ram_mb=768, disk_operations=10)
            ))
    
    def process_request(self, request_id: str):
        """Route request to appropriate pattern processor."""
        pattern = self.select_pattern()
        
        pattern_processors = {
            RequestPattern.SIMPLE_READ: self.simple_read_pattern,
            RequestPattern.USER_AUTH: self.user_auth_pattern,
            RequestPattern.DATA_PROCESSING: self.data_processing_pattern,
            RequestPattern.FILE_UPLOAD: self.file_upload_pattern,
            RequestPattern.ANALYTICS: self.analytics_pattern,
            RequestPattern.ADMIN_TASK: self.admin_task_pattern,
        }
        
        processor = pattern_processors[pattern]
        success = yield self.env.process(processor(request_id))
        
        # Store pattern and result for metrics
        return pattern, success or False

class MetricsCollector:
    """Comprehensive metrics collection and analysis system."""
    
    def __init__(self, env: simpy.Environment, servers: Dict[str, Server]):
        self.env = env
        self.servers = servers
        
        # Metrics storage
        self.server_metrics_history = defaultdict(list)
        self.global_metrics_history = []
        self.request_times = []
        self.request_outcomes = []
        self.pattern_times = defaultdict(list)
        self.pattern_outcomes = defaultdict(list)
        
        # Thread safety
        self._metrics_lock = threading.Lock()
        
        # Start metrics collection process
        self.collection_process = env.process(self._collect_metrics())
        
        logger.info("Initialized metrics collector")
    
    def _collect_metrics(self):
        """Continuous metrics collection process."""
        while True:
            try:
                current_time = self.env.now
                
                # Collect per-server metrics
                server_snapshots = {}
                for server_name, server in self.servers.items():
                    snapshot = server.get_metrics_snapshot()
                    server_snapshots[server_name] = snapshot
                    
                    with self._metrics_lock:
                        self.server_metrics_history[server_name].append(snapshot)
                
                # Calculate global metrics
                global_snapshot = self._calculate_global_metrics(server_snapshots)
                
                with self._metrics_lock:
                    self.global_metrics_history.append(global_snapshot)
                
                # Log metrics periodically
                if int(current_time) % 30 == 0:  # Every 30 simulated seconds
                    self._log_current_metrics(global_snapshot)
                
                yield self.env.timeout(1.0)  # Collect every simulated second
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                yield self.env.timeout(1.0)
    
    def _calculate_global_metrics(self, server_snapshots: Dict[str, ServerMetrics]) -> GlobalMetrics:
        """Calculate system-wide metrics from server snapshots."""
        current_time = self.env.now
        
        # Aggregate request counts
        total_started = sum(s.requests_started for s in server_snapshots.values())
        total_completed = sum(s.requests_completed for s in server_snapshots.values())
        total_failed = len([r for r in self.request_outcomes if not r])
        
        # Calculate throughput (requests per second)
        time_window = 60.0  # Last 60 seconds
        if current_time > 0:
            throughput = total_completed / current_time
        else:
            throughput = 0
        
        # Calculate response time statistics
        if self.request_times:
            avg_response_time = np.mean(self.request_times)
            p95_response_time = np.percentile(self.request_times, 95)
            p99_response_time = np.percentile(self.request_times, 99)
        else:
            avg_response_time = p95_response_time = p99_response_time = 0
        
        # Calculate success rate
        total_requests = total_completed + total_failed
        success_rate = (total_completed / total_requests * 100) if total_requests > 0 else 100
        
        # Pattern-specific metrics
        pattern_success_rates = {}
        pattern_avg_times = {}
        
        for pattern in RequestPattern:
            pattern_outcomes = self.pattern_outcomes.get(pattern.pattern_id, [])
            pattern_times = self.pattern_times.get(pattern.pattern_id, [])
            
            if pattern_outcomes:
                successes = sum(1 for outcome in pattern_outcomes if outcome)
                pattern_success_rates[pattern.pattern_id] = (successes / len(pattern_outcomes)) * 100
            else:
                pattern_success_rates[pattern.pattern_id] = 100
            
            if pattern_times:
                pattern_avg_times[pattern.pattern_id] = np.mean(pattern_times)
            else:
                pattern_avg_times[pattern.pattern_id] = 0
        
        return GlobalMetrics(
            timestamp=current_time,
            total_requests=total_started,
            completed_requests=total_completed,
            failed_requests=total_failed,
            throughput_per_sec=throughput,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            success_rate=success_rate,
            pattern_success_rates=pattern_success_rates,
            pattern_avg_times=pattern_avg_times
        )
    
    def record_request_completion(self, request_id: str, pattern: RequestPattern, 
                                 response_time: float, success: bool):
        """Record completion of a request for metrics."""
        with self._metrics_lock:
            self.request_times.append(response_time)
            self.request_outcomes.append(success)
            self.pattern_times[pattern.pattern_id].append(response_time)
            self.pattern_outcomes[pattern.pattern_id].append(success)
    
    def _log_current_metrics(self, metrics: GlobalMetrics):
        """Log current system metrics."""
        logger.info(
            f"t={metrics.timestamp:.1f}s | "
            f"Throughput: {metrics.throughput_per_sec:.2f} req/s | "
            f"Success: {metrics.success_rate:.1f}% | "
            f"Avg Response: {metrics.avg_response_time:.3f}s | "
            f"P95: {metrics.p95_response_time:.3f}s"
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Generate comprehensive performance summary."""
        if not self.global_metrics_history:
            return {"error": "No metrics data available"}
        
        latest = self.global_metrics_history[-1]
        
        # Server resource utilization summary
        server_summary = {}
        for server_name, server_metrics_list in self.server_metrics_history.items():
            if server_metrics_list:
                latest_server = server_metrics_list[-1]
                recent_metrics = server_metrics_list[-60:] if len(server_metrics_list) >= 60 else server_metrics_list
                avg_cpu = np.mean([m.cpu_utilization for m in recent_metrics])
                avg_ram = np.mean([m.ram_utilization for m in recent_metrics])
                max_queue = max([m.disk_queue_length for m in recent_metrics]) if recent_metrics else 0
                
                server_summary[server_name] = {
                    "current_cpu_util": latest_server.cpu_utilization,
                    "current_ram_util": latest_server.ram_utilization,
                    "avg_cpu_util_1min": avg_cpu,
                    "avg_ram_util_1min": avg_ram,
                    "max_disk_queue_1min": max_queue,
                    "active_requests": latest_server.active_requests,
                    "total_completed": latest_server.requests_completed
                }
        
        return {
            "simulation_time": latest.timestamp,
            "overall_metrics": {
                "total_requests": latest.total_requests,
                "completed_requests": latest.completed_requests,
                "failed_requests": latest.failed_requests,
                "success_rate": latest.success_rate,
                "throughput_per_sec": latest.throughput_per_sec,
                "avg_response_time": latest.avg_response_time,
                "p95_response_time": latest.p95_response_time,
                "p99_response_time": latest.p99_response_time
            },
            "pattern_metrics": {
                "success_rates": latest.pattern_success_rates,
                "avg_response_times": latest.pattern_avg_times
            },
            "server_metrics": server_summary
        }

class MicroservicesSimulation:
    """Main simulation orchestrator."""
    
    def __init__(self, simulation_time: float = 3600.0, request_rate: float = 10.0):
        """Initialize microservices simulation."""
        self.simulation_time = simulation_time
        self.request_rate = request_rate
        self.request_counter = 0
        
        # Create SimPy environment
        self.env = simpy.Environment()
        
        # Initialize servers with configurations
        self.servers = self._initialize_servers()
        
        # Initialize request processor and metrics collector
        self.request_processor = RequestPatternProcessor(self.env, self.servers)
        self.metrics_collector = MetricsCollector(self.env, self.servers)
        
        logger.info(f"Initialized simulation: {simulation_time}s at {request_rate} req/s")
    
    def _initialize_servers(self) -> Dict[str, Server]:
        """Initialize all microservice servers with their configurations."""
        server_configs = {
            'nginx': ServerConfig('nginx', cpu_threads=8, ram_gb=16, network_gbps=40.0),
            'app1': ServerConfig('app1', cpu_threads=16, ram_gb=64, network_gbps=10.0),
            'auth': ServerConfig('auth', cpu_threads=4, ram_gb=32, network_gbps=5.0),
            'policy': ServerConfig('policy', cpu_threads=8, ram_gb=32, network_gbps=5.0),
            'service': ServerConfig('service', cpu_threads=16, ram_gb=64, network_gbps=10.0),
            'db': ServerConfig('db', cpu_threads=32, ram_gb=128, network_gbps=20.0, disk_queue_size=64),
            'logger': ServerConfig('logger', cpu_threads=4, ram_gb=16, network_gbps=2.0),
            's3': ServerConfig('s3', cpu_threads=4, ram_gb=32, network_gbps=50.0, disk_queue_size=128),
            'servicehub': ServerConfig('servicehub', cpu_threads=16, ram_gb=64, network_gbps=10.0),
            'app2': ServerConfig('app2', cpu_threads=16, ram_gb=64, network_gbps=10.0),
        }
        
        servers = {}
        for name, config in server_configs.items():
            servers[name] = Server(self.env, config)
        
        return servers
    
    def _request_generator(self):
        """Generate requests according to Poisson distribution."""
        while True:
            try:
                # Generate next request
                self.request_counter += 1
                request_id = f"req_{self.request_counter:06d}"
                
                # Start request processing
                self.env.process(self._process_single_request(request_id))
                
                # Wait for next request (Poisson arrival)
                inter_arrival_time = random.expovariate(self.request_rate)
                yield self.env.timeout(inter_arrival_time)
                
            except Exception as e:
                logger.error(f"Request generation error: {e}")
                yield self.env.timeout(1.0)
    
    def _process_single_request(self, request_id: str):
        """Process a single request and record metrics."""
        start_time = self.env.now
        
        try:
            # Process the request
            result = yield self.env.process(self.request_processor.process_request(request_id))
            pattern, success = result
            
            # Record completion
            response_time = self.env.now - start_time
            
            self.metrics_collector.record_request_completion(
                request_id, pattern, response_time, success
            )
            
        except Exception as e:
            # Record failure
            response_time = self.env.now - start_time
            pattern = RequestPattern.SIMPLE_READ  # Default pattern for errors
            self.metrics_collector.record_request_completion(
                request_id, pattern, response_time, False
            )
            logger.error(f"Request {request_id} error: {e}")
    
    def run_simulation(self) -> Dict[str, Any]:
        """Run the complete simulation and return results."""
        logger.info(f"Starting microservices simulation...")
        
        # Start request generation
        self.env.process(self._request_generator())
        
        # Run simulation
        start_wall_time = time.time()
        try:
            self.env.run(until=self.simulation_time)
        except KeyboardInterrupt:
            logger.warning("Simulation interrupted by user")
        
        end_wall_time = time.time()
        wall_time_duration = end_wall_time - start_wall_time
        
        # Generate final report
        performance_summary = self.metrics_collector.get_performance_summary()
        performance_summary["simulation_info"] = {
            "simulated_time": self.simulation_time,
            "wall_clock_time": wall_time_duration,
            "simulation_speed": self.simulation_time / wall_time_duration,
            "target_request_rate": self.request_rate,
            "total_requests_generated": self.request_counter
        }
        
        logger.info(f"Simulation completed in {wall_time_duration:.2f}s wall time")
        logger.info(f"Simulation speed: {self.simulation_time/wall_time_duration:.1f}x real-time")
        
        return performance_summary

def main():
    """Main entry point for the simulation."""
    try:
        # Set random seed for reproducible results
        random.seed(42)
        np.random.seed(42)
        
        # Configure simulation parameters
        simulation_time = 120.0  # 2 minutes for testing
        request_rate = 8.0  # 8 requests per second average
        
        print("=" * 80)
        print("MICROSERVICES PERFORMANCE SIMULATION")
        print("=" * 80)
        print(f"Simulation Duration: {simulation_time} seconds ({simulation_time/60:.1f} minutes)")
        print(f"Target Request Rate: {request_rate} req/s")
        print(f"Expected Total Requests: ~{int(simulation_time * request_rate)}")
        print()
        
        # Run simulation
        simulation = MicroservicesSimulation(simulation_time, request_rate)
        results = simulation.run_simulation()
        
        # Display results
        print("\n" + "=" * 80)
        print("SIMULATION RESULTS")
        print("=" * 80)
        
        sim_info = results["simulation_info"]
        overall = results["overall_metrics"]
        patterns = results["pattern_metrics"]
        servers = results["server_metrics"]
        
        print(f"\nSIMULATION SUMMARY:")
        print(f"  Simulated Time: {sim_info['simulated_time']:.1f}s")
        print(f"  Wall Clock Time: {sim_info['wall_clock_time']:.2f}s")
        print(f"  Simulation Speed: {sim_info['simulation_speed']:.1f}x real-time")
        print(f"  Requests Generated: {sim_info['total_requests_generated']}")
        
        print(f"\nOVERALL PERFORMANCE:")
        print(f"  Success Rate: {overall['success_rate']:.1f}%")
        print(f"  Throughput: {overall['throughput_per_sec']:.2f} req/s")
        print(f"  Avg Response Time: {overall['avg_response_time']:.3f}s")
        print(f"  P95 Response Time: {overall['p95_response_time']:.3f}s")
        print(f"  P99 Response Time: {overall['p99_response_time']:.3f}s")
        
        print(f"\nPATTERN PERFORMANCE:")
        for pattern in RequestPattern:
            pattern_id = pattern.pattern_id
            success_rate = patterns["success_rates"].get(pattern_id, 0)
            avg_time = patterns["avg_response_times"].get(pattern_id, 0)
            print(f"  {pattern_id:15} | Success: {success_rate:5.1f}% | Avg Time: {avg_time:.3f}s")
        
        print(f"\nSERVER UTILIZATION:")
        print(f"  {'Server':<12} | {'CPU%':<6} | {'RAM%':<6} | {'Queue':<5} | {'Active':<6} | {'Completed':<9}")
        print(f"  {'-'*12}-+-{'-'*6}-+-{'-'*6}-+-{'-'*5}-+-{'-'*6}-+-{'-'*9}")
        
        for server_name, metrics in servers.items():
            cpu_util = metrics["current_cpu_util"]
            ram_util = metrics["current_ram_util"] 
            max_queue = metrics["max_disk_queue_1min"]
            active = metrics["active_requests"]
            completed = metrics["total_completed"]
            
            print(f"  {server_name:<12} | {cpu_util:5.1f}% | {ram_util:5.1f}% | "
                  f"{max_queue:4d} | {active:5d} | {completed:8d}")
        
        # Save detailed results to JSON
        results_filename = f"simulation_results_{int(time.time())}.json"
        with open(results_filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nDetailed results saved to: {results_filename}")
        
        print("\n" + "=" * 80)
        print("SIMULATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        return results
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise

if __name__ == "__main__":
    main()