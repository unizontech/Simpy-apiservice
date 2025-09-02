# Advanced Metrics Collection - Implementation Prompt

**Purpose**: Add comprehensive per-second metrics collection and JSON export capabilities to SimPy microservice simulation

---

## 🎯 Metrics System Requirements

### 1. Per-Second Resource Tracking

**Enhanced Server Metrics:**
```python
class Server:
    def __init__(self, env, name, threads=4, ram_gb=32, disk_q=16, net_mbps=1000):
        # ... existing initialization ...
        
        # Per-second metrics storage
        self.per_second_metrics = defaultdict(lambda: {
            'cpu_usage': 0.0,           # CPU seconds used this second
            'ram_used': 0.0,            # RAM GB currently allocated
            'disk_queue': 0,            # Current disk queue length
            'active_requests': 0,       # Requests currently processing
            'requests_started': 0,      # New requests this second
            'requests_completed': 0,    # Completed requests this second
            'request_types': defaultdict(int)  # Pattern distribution
        })
        
    def process_request(self, cpu_ms=50, ram_gb=1, disk_mb=10, net_mb=5, req_type=None):
        start_time = self.env.now
        start_second = int(start_time)
        
        # Record request start
        self.per_second_metrics[start_second]['requests_started'] += 1
        self.per_second_metrics[start_second]['active_requests'] += 1
        if req_type:
            self.per_second_metrics[start_second]['request_types'][req_type.value] += 1
        
        # ... existing processing logic ...
        
        # Record completion
        end_second = int(self.env.now)
        self.per_second_metrics[end_second]['requests_completed'] += 1
        self.per_second_metrics[end_second]['active_requests'] -= 1
        self.per_second_metrics[end_second]['ram_used'] = self.ram.capacity - self.ram.level
```

### 2. Time-Series Data Collection

**Continuous Monitoring:**
```python
def collect_resource_snapshots(system, interval=1.0):
    """Collect resource usage snapshots at regular intervals"""
    while True:
        current_second = int(system.env.now)
        
        for server in system.get_all_servers():
            metrics = server.per_second_metrics[current_second]
            
            # Calculate utilization rates
            metrics['cpu_utilization_percent'] = (
                metrics['cpu_usage'] / server.cpu.capacity
            ) * 100
            
            metrics['ram_utilization_percent'] = (
                metrics['ram_used'] / server.ram.capacity
            ) * 100
            
            # Update disk queue status
            if hasattr(server, 'disk'):
                metrics['disk_queue'] = len(server.disk.queue)
        
        yield system.env.timeout(interval)
```

### 3. JSON Export Structure

**Hierarchical Data Format:**
```python
def export_per_second_data(system, arrival_rate, sim_time):
    """Export comprehensive per-second metrics to JSON"""
    export_data = {
        'scenario': {
            'arrival_rate': arrival_rate,
            'simulation_time': sim_time,
            'timestamp': datetime.now().isoformat(),
            'pattern_weights': {
                pattern.pattern_id: pattern.probability 
                for pattern in REQUEST_PATTERNS
            }
        },
        'servers': {}
    }
    
    for server in system.get_all_servers():
        export_data['servers'][server.name] = {
            'specs': {
                'threads': server.cpu.capacity,
                'ram_gb': server.ram.capacity,
                'disk_queue_capacity': getattr(server.disk, 'capacity', 'unlimited'),
                'net_mbps': server.net_mbps
            },
            'per_second_data': {}
        }
        
        # Export time-series data
        for second in range(int(sim_time) + 1):
            metrics = server.per_second_metrics.get(second, {})
            
            export_data['servers'][server.name]['per_second_data'][str(second)] = {
                'cpu_usage_seconds': round(metrics.get('cpu_usage', 0), 3),
                'cpu_utilization_percent': round(
                    (metrics.get('cpu_usage', 0) / server.cpu.capacity) * 100, 2
                ),
                'ram_used_gb': round(metrics.get('ram_used', 0), 2),
                'ram_utilization_percent': round(
                    (metrics.get('ram_used', 0) / server.ram.capacity) * 100, 2
                ),
                'disk_queue_length': metrics.get('disk_queue', 0),
                'active_requests': metrics.get('active_requests', 0),
                'requests_started': metrics.get('requests_started', 0),
                'requests_completed': metrics.get('requests_completed', 0),
                'request_types': dict(metrics.get('request_types', {}))
            }
    
    return export_data
```

### 4. Performance Analysis Functions

**Statistical Analysis:**
```python
def analyze_time_series_metrics(system, sim_time):
    """Comprehensive time-series analysis"""
    analysis = {
        'overall_stats': {},
        'server_analysis': {},
        'bottleneck_detection': {},
        'pattern_performance': {}
    }
    
    # Overall system performance
    analysis['overall_stats'] = {
        'total_requests': system.total_requests,
        'completed_requests': system.completed_requests,
        'success_rate_percent': (system.completed_requests / system.total_requests) * 100,
        'avg_response_time_seconds': statistics.mean(system.end_to_end_times) if system.end_to_end_times else 0,
        'p95_response_time_seconds': calculate_percentile(system.end_to_end_times, 0.95),
        'p99_response_time_seconds': calculate_percentile(system.end_to_end_times, 0.99)
    }
    
    # Per-server detailed analysis
    for server in system.get_all_servers():
        server_stats = analyze_server_metrics(server, sim_time)
        analysis['server_analysis'][server.name] = server_stats
        
        # Bottleneck detection
        if server_stats['max_cpu_utilization'] > 70:
            analysis['bottleneck_detection'][server.name] = 'CPU_BOTTLENECK'
        if server_stats['max_ram_utilization'] > 80:
            analysis['bottleneck_detection'][server.name] = 'RAM_BOTTLENECK'
    
    return analysis

def analyze_server_metrics(server, sim_time):
    """Detailed per-server analysis"""
    cpu_utilizations = []
    ram_utilizations = []
    queue_lengths = []
    
    for second in range(int(sim_time) + 1):
        metrics = server.per_second_metrics.get(second, {})
        
        cpu_util = (metrics.get('cpu_usage', 0) / server.cpu.capacity) * 100
        ram_util = (metrics.get('ram_used', 0) / server.ram.capacity) * 100
        
        cpu_utilizations.append(cpu_util)
        ram_utilizations.append(ram_util)
        queue_lengths.append(metrics.get('disk_queue', 0))
    
    return {
        'avg_cpu_utilization': statistics.mean(cpu_utilizations),
        'max_cpu_utilization': max(cpu_utilizations),
        'avg_ram_utilization': statistics.mean(ram_utilizations),
        'max_ram_utilization': max(ram_utilizations),
        'max_disk_queue': max(queue_lengths),
        'total_requests': server.total_requests,
        'request_distribution': dict(server.request_types)
    }
```

### 5. Multi-Load Testing Framework

**Automated Load Testing:**
```python
def run_load_test_suite(test_loads=[10, 25, 50, 100], sim_time=60):
    """Run simulation at multiple load levels"""
    results = {}
    
    for load in test_loads:
        print(f"\n🚀 Testing at {load} req/s...")
        
        # Run simulation
        env = simpy.Environment()
        system = MicroserviceSystem(env)
        
        # Start metrics collection
        env.process(collect_resource_snapshots(system))
        env.process(request_generator(system, arrival_rate=load, sim_time=sim_time))
        
        # Execute simulation
        env.run(until=sim_time)
        
        # Analyze and export results
        analysis = analyze_time_series_metrics(system, sim_time)
        export_data = export_per_second_data(system, load, sim_time)
        
        # Save to files
        with open(f'metrics_{load}rps_{sim_time}s.json', 'w') as f:
            json.dump(export_data, f, indent=2)
        
        results[load] = {
            'analysis': analysis,
            'export_file': f'metrics_{load}rps_{sim_time}s.json'
        }
        
        print(f"✅ {load} req/s completed - {analysis['overall_stats']['success_rate_percent']:.1f}% success rate")
    
    return results
```

### 6. Real-time Monitoring Display

**Live Metrics Dashboard:**
```python
def display_live_metrics(system, interval=5.0):
    """Display live system metrics during simulation"""
    while True:
        current_time = system.env.now
        
        print(f"\n⏰ Time: {current_time:.1f}s")
        print("=" * 60)
        
        for server in system.get_all_servers():
            current_second = int(current_time)
            metrics = server.per_second_metrics.get(current_second, {})
            
            cpu_util = (metrics.get('cpu_usage', 0) / server.cpu.capacity) * 100
            ram_util = (metrics.get('ram_used', 0) / server.ram.capacity) * 100
            active_reqs = metrics.get('active_requests', 0)
            
            print(f"{server.name:12} | CPU: {cpu_util:5.1f}% | RAM: {ram_util:5.1f}% | Active: {active_reqs:3}")
        
        yield system.env.timeout(interval)
```

## 🚀 Implementation Instructions

### Integration Steps:
1. **Enhance Server class** with per-second metrics storage
2. **Add continuous monitoring process** for resource snapshots
3. **Implement JSON export functionality** with hierarchical structure
4. **Create analysis functions** for statistical insights
5. **Add multi-load testing framework** for comprehensive evaluation
6. **Optional: Real-time monitoring** for live system observation

### File Output Requirements:
- `metrics_{load}rps_{time}s.json` - Detailed per-second data
- `analysis_summary_{load}rps.json` - Statistical analysis
- Console output with live metrics and final summary

## 📊 Success Criteria

**Data Collection:**
- ✅ Per-second metrics for all servers captured
- ✅ Resource utilization calculated accurately
- ✅ Pattern distribution tracked over time
- ✅ JSON export with complete hierarchical data

**Analysis Capabilities:**
- ✅ Bottleneck identification across time series
- ✅ Statistical analysis (mean, percentiles, max values)
- ✅ Multi-load comparison capabilities
- ✅ Pattern-specific performance insights

**Performance:**
- ✅ Metrics collection doesn't significantly impact simulation speed
- ✅ Memory usage remains reasonable for long simulations
- ✅ JSON export completes successfully for all load levels

## 🎯 Implementation Request

Please enhance an existing SimPy microservice simulation with comprehensive per-second metrics collection that provides:
1. Detailed time-series resource utilization data
2. JSON export for external analysis tools
3. Multi-load testing capabilities
4. Statistical analysis and bottleneck detection
5. Optional real-time monitoring dashboard

This will transform the simulation into a production-ready capacity planning and performance analysis tool.

---

**Use Case**: Detailed performance analysis, capacity planning, bottleneck identification  
**Data Output**: Time-series JSON files suitable for visualization tools  
**Complexity Level**: Advanced - comprehensive monitoring and analysis system