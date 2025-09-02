# Basic SimPy Microservice Simulation - Implementation Prompt

**Purpose**: Create a foundational SimPy-based microservice simulation with essential components

---

## 🎯 Basic Requirements

### 1. Simple Server Architecture (5 Core Servers)

**Essential Server Configuration:**
- **Nginx**: 8 threads, 16GB RAM (Load balancer)
- **APP**: 16 threads, 64GB RAM (Application server)
- **Auth**: 4 threads, 32GB RAM (Authentication)
- **Service**: 16 threads, 64GB RAM (Business logic)
- **DB**: 32 threads, 128GB RAM (Database)

**Resource Modeling:**
```python
# CPU: simpy.PreemptiveResource for parallel processing
self.cpu = simpy.PreemptiveResource(env, capacity=threads)

# RAM: simpy.Container for dynamic memory allocation
self.ram = simpy.Container(env, capacity=ram_gb, init=ram_gb)

# Basic metrics tracking
self.total_requests = 0
self.response_times = []
```

### 2. Single Request Flow

**Processing Path:**
```
Nginx (10ms) → APP (60ms, 2GB RAM) → Auth (40ms, 1GB RAM) → Service (80ms, 2GB RAM) → DB (120ms, 4GB RAM)
```

**Flow Implementation:**
```python
def request_handler(system, request_id):
    start_time = system.env.now
    
    # Sequential processing through each server
    yield system.env.process(system.nginx.process_request(cpu_ms=10, net_mb=1))
    yield system.env.process(system.app.process_request(cpu_ms=60, ram_gb=2))
    yield system.env.process(system.auth.process_request(cpu_ms=40, ram_gb=1))
    yield system.env.process(system.service.process_request(cpu_ms=80, ram_gb=2))
    yield system.env.process(system.db.process_request(cpu_ms=120, ram_gb=4))
    
    # Record metrics
    response_time = system.env.now - start_time
    system.completed_requests += 1
    system.response_times.append(response_time)
```

### 3. Basic Metrics

**Essential Metrics:**
- Total requests processed
- Completed requests count
- Average response time
- Basic CPU utilization per server
- Success rate

**Simple Analysis Output:**
```python
def analyze_results(system, sim_time):
    print(f"Total Requests: {system.total_requests}")
    print(f"Completed: {system.completed_requests}")
    print(f"Success Rate: {system.completed_requests/system.total_requests*100:.1f}%")
    print(f"Avg Response Time: {statistics.mean(system.response_times):.3f}s")
    
    for server in [system.nginx, system.app, system.auth, system.service, system.db]:
        cpu_util = (server.cpu_time / sim_time) * 100 / server.cpu.capacity
        print(f"{server.name}: {cpu_util:.1f}% CPU")
```

## 🚀 Implementation Instructions

### Core Classes Needed:
1. **Server Class**: Resource management (CPU, RAM, basic metrics)
2. **MicroserviceSystem Class**: 5-server setup
3. **Request Handler Function**: Linear processing flow
4. **Request Generator**: Poisson arrival process
5. **Analysis Function**: Basic performance output

### Minimal Dependencies:
```txt
simpy>=4.0.0
```

### Expected Code Size:
- Approximately 150-200 lines
- Single Python file implementation
- Focus on clarity over features

## 📊 Success Criteria

**Functional Requirements:**
- ✅ All 5 servers processing requests successfully
- ✅ Resource allocation/deallocation working
- ✅ Basic metrics collection functional
- ✅ Simulation runs without errors

**Output Requirements:**
- ✅ Request processing statistics
- ✅ Server utilization summary
- ✅ Response time analysis
- ✅ Simple bottleneck identification

## 🎯 Implementation Request

Please create a clean, educational SimPy microservice simulation that demonstrates:
1. Basic SimPy resource management
2. Sequential request processing
3. Simple performance metrics
4. Clear, understandable code structure

This should serve as a foundation that can be extended with more advanced features later.

---

**Target Audience**: Learning SimPy fundamentals, understanding microservice simulation basics  
**Complexity Level**: Beginner to Intermediate  
**Extension Path**: Can be enhanced with multi-pattern processing, advanced metrics, or parallel processing