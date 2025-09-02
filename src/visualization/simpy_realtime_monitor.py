#!/usr/bin/env python3
"""
SimPy Real-time Monitor

Real-time visualization of SimPy simulation progress with server status.
"""

import time
import threading
import simpy
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import os
from datetime import datetime
from realtime_visualizer import RealtimeVisualizer, ProcessStatus

@dataclass
class ServerStatus:
    """Real-time server status."""
    name: str
    cpu_usage: int = 0
    cpu_capacity: int = 0
    ram_usage: float = 0.0
    ram_capacity: float = 0.0
    active_requests: int = 0
    total_requests: int = 0
    queue_length: int = 0
    last_update: float = field(default_factory=time.time)
    
    @property
    def cpu_utilization(self) -> float:
        if self.cpu_capacity == 0:
            return 0.0
        return (self.cpu_usage / self.cpu_capacity) * 100
    
    @property
    def ram_utilization(self) -> float:
        if self.ram_capacity == 0:
            return 0.0
        return (self.ram_usage / self.ram_capacity) * 100

class SimPyRealtimeMonitor:
    """Real-time monitor for SimPy simulations."""
    
    def __init__(self, update_interval: float = 1.0):
        self.update_interval = update_interval
        self.server_status: Dict[str, ServerStatus] = {}
        self.request_counts = defaultdict(int)
        self.pattern_counts = defaultdict(int)
        self.response_times = deque(maxlen=100)  # Keep last 100 response times
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self.simulation_start_time = 0
        self.current_sim_time = 0
        
        # Performance metrics
        self.throughput_history = deque(maxlen=60)  # 1 minute of throughput data
        self.last_request_count = 0
    
    def register_server(self, server_name: str, cpu_capacity: int, ram_capacity: float):
        """Register a server for monitoring."""
        self.server_status[server_name] = ServerStatus(
            name=server_name,
            cpu_capacity=cpu_capacity,
            ram_capacity=ram_capacity
        )
    
    def update_server_status(self, server_name: str, cpu_usage: int = None, 
                           ram_usage: float = None, active_requests: int = None,
                           queue_length: int = None):
        """Update server status."""
        if server_name not in self.server_status:
            return
        
        server = self.server_status[server_name]
        
        if cpu_usage is not None:
            server.cpu_usage = cpu_usage
        if ram_usage is not None:
            server.ram_usage = ram_usage
        if active_requests is not None:
            server.active_requests = active_requests
        if queue_length is not None:
            server.queue_length = queue_length
        
        server.last_update = time.time()
    
    def log_request_start(self, pattern: str):
        """Log when a request starts."""
        self.request_counts['total'] += 1
        self.pattern_counts[pattern] += 1
    
    def log_request_complete(self, pattern: str, response_time: float):
        """Log when a request completes."""
        self.request_counts['completed'] += 1
        self.response_times.append(response_time)
    
    def update_simulation_time(self, sim_time: float):
        """Update current simulation time."""
        self.current_sim_time = sim_time
    
    def start_monitoring(self):
        """Start real-time monitoring."""
        if self._running:
            return
        
        self.simulation_start_time = time.time()
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop real-time monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join()
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            self._render_dashboard()
            self._update_throughput()
            time.sleep(self.update_interval)
    
    def _update_throughput(self):
        """Update throughput metrics."""
        current_requests = self.request_counts['completed']
        requests_this_second = current_requests - self.last_request_count
        self.throughput_history.append(requests_this_second)
        self.last_request_count = current_requests
    
    def _render_dashboard(self):
        """Render the monitoring dashboard."""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("🚀 SimPy Real-time Simulation Monitor")
        print("=" * 80)
        
        # Simulation overview
        real_elapsed = time.time() - self.simulation_start_time
        print(f"⏰ Real time: {real_elapsed:.1f}s | Sim time: {self.current_sim_time:.1f}s | Speed: {self.current_sim_time/real_elapsed:.1f}x")
        print()
        
        # Request metrics
        self._render_request_metrics()
        print()
        
        # Server status
        self._render_server_status()
        print()
        
        # Pattern distribution
        self._render_pattern_distribution()
    
    def _render_request_metrics(self):
        """Render request metrics section."""
        total = self.request_counts['total']
        completed = self.request_counts['completed']
        success_rate = (completed / total * 100) if total > 0 else 0
        
        print("📊 Request Metrics")
        print(f"   Total Requests: {total:,}")
        print(f"   Completed: {completed:,}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if self.response_times:
            avg_response = sum(self.response_times) / len(self.response_times)
            print(f"   Avg Response Time: {avg_response:.3f}s")
        
        # Throughput
        if self.throughput_history:
            current_throughput = self.throughput_history[-1] if self.throughput_history else 0
            avg_throughput = sum(self.throughput_history) / len(self.throughput_history)
            print(f"   Current Throughput: {current_throughput} req/s")
            print(f"   Average Throughput: {avg_throughput:.1f} req/s")
            
            # Throughput graph (simple text-based)
            print(f"   Throughput Graph: {self._create_mini_graph(list(self.throughput_history))}")
    
    def _render_server_status(self):
        """Render server status section."""
        print("🖥️  Server Status")
        
        if not self.server_status:
            print("   No servers registered")
            return
        
        print(f"   {'Server':<15} {'CPU':<12} {'RAM':<12} {'Active':<8} {'Queue':<6} {'Total':<8}")
        print("   " + "-" * 65)
        
        for server in self.server_status.values():
            cpu_bar = self._create_utilization_bar(server.cpu_utilization)
            ram_bar = self._create_utilization_bar(server.ram_utilization)
            
            print(f"   {server.name:<15} {cpu_bar:<12} {ram_bar:<12} "
                  f"{server.active_requests:<8} {server.queue_length:<6} {server.total_requests:<8}")
    
    def _render_pattern_distribution(self):
        """Render pattern distribution section."""
        print("🎯 Pattern Distribution")
        
        if not self.pattern_counts:
            print("   No patterns recorded")
            return
        
        total = sum(self.pattern_counts.values())
        
        for pattern, count in sorted(self.pattern_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            bar = self._create_progress_bar(percentage, width=20)
            print(f"   {pattern:<20} {bar} {percentage:5.1f}% ({count:,})")
    
    def _create_utilization_bar(self, percent: float) -> str:
        """Create utilization bar with color indicators."""
        if percent > 90:
            return f"🔴{percent:5.1f}%"
        elif percent > 70:
            return f"🟡{percent:5.1f}%"
        else:
            return f"🟢{percent:5.1f}%"
    
    def _create_progress_bar(self, percent: float, width: int = 20) -> str:
        """Create a text-based progress bar."""
        filled = int(width * percent / 100)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"
    
    def _create_mini_graph(self, data: List[float]) -> str:
        """Create a mini text-based graph."""
        if not data:
            return "No data"
        
        # Normalize to 0-8 range for display
        max_val = max(data) if data else 1
        normalized = [int(val / max_val * 8) if max_val > 0 else 0 for val in data[-20:]]  # Last 20 points
        
        chars = [' ', '▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
        return ''.join(chars[min(val, 8)] for val in normalized)

# Integration with existing SimPy simulation
def create_monitored_simulation(env, system, monitor_interval: float = 1.0):
    """Create a monitored SimPy simulation."""
    monitor = SimPyRealtimeMonitor(monitor_interval)
    
    # Register servers from system
    if hasattr(system, 'get_all_servers'):
        for server in system.get_all_servers():
            cpu_capacity = getattr(server.cpu, 'capacity', 4) if hasattr(server, 'cpu') else 4
            ram_capacity = getattr(server.ram, 'capacity', 32) if hasattr(server, 'ram') else 32
            monitor.register_server(server.name, cpu_capacity, ram_capacity)
    
    # Add monitoring process
    def monitoring_process():
        while True:
            monitor.update_simulation_time(env.now)
            
            # Update server metrics
            if hasattr(system, 'get_all_servers'):
                for server in system.get_all_servers():
                    cpu_usage = len(server.cpu.users) if hasattr(server, 'cpu') else 0
                    ram_usage = server.ram.capacity - server.ram.level if hasattr(server, 'ram') else 0
                    queue_len = len(server.cpu.queue) if hasattr(server, 'cpu') else 0
                    
                    monitor.update_server_status(
                        server.name,
                        cpu_usage=cpu_usage,
                        ram_usage=ram_usage,
                        queue_length=queue_len
                    )
            
            yield env.timeout(monitor_interval)
    
    env.process(monitoring_process())
    
    return monitor

def demo_monitored_simulation():
    """Demo showing monitored simulation."""
    import simpy
    from collections import namedtuple
    
    # Simple server simulation for demo
    Server = namedtuple('Server', ['name', 'cpu', 'ram'])
    
    class DemoServer:
        def __init__(self, env, name, cpu_capacity, ram_capacity):
            self.env = env
            self.name = name
            self.cpu = simpy.Resource(env, capacity=cpu_capacity)
            self.ram = simpy.Container(env, capacity=ram_capacity, init=ram_capacity)
    
    class DemoSystem:
        def __init__(self, env):
            self.env = env
            self.servers = [
                DemoServer(env, "WebServer", 4, 16),
                DemoServer(env, "AppServer", 8, 32),
                DemoServer(env, "Database", 16, 64)
            ]
        
        def get_all_servers(self):
            return self.servers
    
    # Create simulation
    env = simpy.Environment()
    system = DemoSystem(env)
    
    # Create monitored simulation
    monitor = create_monitored_simulation(env, system, monitor_interval=0.5)
    
    # Start monitoring
    monitor.start_monitoring()
    
    # Simple request generator for demo
    def request_generator():
        patterns = ["simple_read", "user_auth", "data_processing"]
        for i in range(100):
            pattern = patterns[i % len(patterns)]
            monitor.log_request_start(pattern)
            
            # Simulate some processing
            yield env.timeout(0.1 + (i % 5) * 0.1)
            
            monitor.log_request_complete(pattern, env.now * 0.1)
    
    env.process(request_generator())
    
    # Run simulation
    try:
        env.run(until=50)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop_monitoring()

if __name__ == "__main__":
    print("🎯 Starting SimPy Real-time Monitor Demo...")
    demo_monitored_simulation()