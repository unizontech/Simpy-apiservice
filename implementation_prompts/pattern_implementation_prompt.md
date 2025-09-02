# Multi-Pattern Request Processing - Implementation Prompt

**Purpose**: Add sophisticated request pattern handling to existing SimPy microservice simulation

---

## 🎯 Pattern System Requirements

### 1. Request Pattern Enumeration

**Pattern Definitions:**
```python
from enum import Enum

class RequestType(Enum):
    SIMPLE_READ = ("simple_read", 0.40, "Lightweight read operation")
    USER_AUTH = ("user_auth", 0.25, "User authentication with parallel processing")
    DATA_PROCESSING = ("data_processing", 0.20, "Heavy data processing with DB")
    FILE_UPLOAD = ("file_upload", 0.08, "Large file upload with storage")
    ANALYTICS = ("analytics", 0.05, "Complex analytics processing")
    ADMIN_TASK = ("admin_task", 0.02, "Administrative system-wide task")
    
    def __init__(self, pattern_id: str, probability: float, description: str):
        self.pattern_id = pattern_id
        self.probability = probability
        self.description = description
```

### 2. Pattern-Specific Processing Flows

#### **Simple Read Pattern (40%)**
```python
def simple_read_flow(system, req_type):
    """Optimized read path - minimal resource usage"""
    yield system.env.process(system.nginx.process_request(cpu_ms=5, net_mb=0.5, req_type=req_type))
    yield system.env.process(system.app1.process_request(cpu_ms=20, ram_gb=1, req_type=req_type))
    yield system.env.process(system.service.process_request(cpu_ms=30, ram_gb=1, req_type=req_type))
    yield system.env.process(system.app2.process_request(cpu_ms=15, ram_gb=1, req_type=req_type))
```

#### **User Authentication Pattern (25%)**
```python
def user_auth_flow(system, req_type):
    """Authentication with parallel auth/policy processing"""
    yield system.env.process(system.nginx.process_request(cpu_ms=10, net_mb=1, req_type=req_type))
    yield system.env.process(system.app1.process_request(cpu_ms=40, ram_gb=2, req_type=req_type))
    
    # Parallel authentication and authorization
    auth_task = system.env.process(system.auth.process_request(cpu_ms=60, ram_gb=2, req_type=req_type))
    policy_task = system.env.process(system.policy.process_request(cpu_ms=45, ram_gb=1, req_type=req_type))
    yield system.env.all_of([auth_task, policy_task])
    
    yield system.env.process(system.service.process_request(cpu_ms=50, ram_gb=2, req_type=req_type))
    yield system.env.process(system.app2.process_request(cpu_ms=30, ram_gb=2, req_type=req_type))
```

#### **Data Processing Pattern (20%)**
```python
def data_processing_flow(system, req_type):
    """Heavy database operations with data transformation"""
    yield system.env.process(system.nginx.process_request(cpu_ms=10, net_mb=2, req_type=req_type))
    yield system.env.process(system.app1.process_request(cpu_ms=50, ram_gb=3, req_type=req_type))
    yield system.env.process(system.service.process_request(cpu_ms=100, ram_gb=4, req_type=req_type))
    
    # Required database processing
    yield system.env.process(system.db.process_request(
        cpu_ms=200, ram_gb=8, disk_mb=100, net_mb=5, req_type=req_type
    ))
    
    yield system.env.process(system.servicehub.process_request(cpu_ms=80, ram_gb=3, req_type=req_type))
    yield system.env.process(system.app2.process_request(cpu_ms=60, ram_gb=3, req_type=req_type))
```

#### **File Upload Pattern (8%)**
```python
def file_upload_flow(system, req_type):
    """Large file upload with storage processing"""
    # Large network transfer
    yield system.env.process(system.nginx.process_request(cpu_ms=15, net_mb=50, req_type=req_type))
    yield system.env.process(system.app1.process_request(cpu_ms=80, ram_gb=8, req_type=req_type))
    yield system.env.process(system.auth.process_request(cpu_ms=40, ram_gb=1, req_type=req_type))
    yield system.env.process(system.service.process_request(cpu_ms=120, ram_gb=6, req_type=req_type))
    
    # Parallel storage and logging
    s3_task = system.env.process(system.s3.process_request(
        cpu_ms=30, ram_gb=10, disk_mb=500, net_mb=100, req_type=req_type
    ))
    logger_task = system.env.process(system.logger.process_request(cpu_ms=25, ram_gb=2, req_type=req_type))
    yield system.env.all_of([s3_task, logger_task])
    
    yield system.env.process(system.app2.process_request(cpu_ms=40, ram_gb=4, req_type=req_type))
```

#### **Analytics Pattern (5%)**
```python
def analytics_flow(system, req_type):
    """Compute-intensive analytics with parallel processing"""
    yield system.env.process(system.nginx.process_request(cpu_ms=10, net_mb=3, req_type=req_type))
    yield system.env.process(system.app1.process_request(cpu_ms=100, ram_gb=8, req_type=req_type))
    
    # Heavy parallel computation
    service_task = system.env.process(system.service.process_request(cpu_ms=300, ram_gb=12, req_type=req_type))
    db_task = system.env.process(system.db.process_request(
        cpu_ms=400, ram_gb=16, disk_mb=200, net_mb=10, req_type=req_type
    ))
    yield system.env.all_of([service_task, db_task])
    
    yield system.env.process(system.servicehub.process_request(cpu_ms=200, ram_gb=8, req_type=req_type))
    yield system.env.process(system.app2.process_request(cpu_ms=80, ram_gb=6, req_type=req_type))
    
    # Asynchronous result logging
    system.env.process(system.logger.process_request(cpu_ms=30, ram_gb=3, req_type=req_type))
```

#### **Admin Task Pattern (2%)**
```python
def admin_task_flow(system, req_type):
    """System-wide administrative task using all servers"""
    yield system.env.process(system.nginx.process_request(cpu_ms=20, net_mb=5, req_type=req_type))
    yield system.env.process(system.app1.process_request(cpu_ms=150, ram_gb=10, req_type=req_type))
    
    # Administrative authorization
    auth_task = system.env.process(system.auth.process_request(cpu_ms=80, ram_gb=3, req_type=req_type))
    policy_task = system.env.process(system.policy.process_request(cpu_ms=120, ram_gb=4, req_type=req_type))
    yield system.env.all_of([auth_task, policy_task])
    
    # Main administrative work
    yield system.env.process(system.service.process_request(cpu_ms=250, ram_gb=8, req_type=req_type))
    yield system.env.process(system.db.process_request(
        cpu_ms=300, ram_gb=20, disk_mb=150, net_mb=8, req_type=req_type
    ))
    yield system.env.process(system.servicehub.process_request(cpu_ms=180, ram_gb=6, req_type=req_type))
    
    # Result storage and logging
    s3_task = system.env.process(system.s3.process_request(
        cpu_ms=50, ram_gb=8, disk_mb=300, net_mb=50, req_type=req_type
    ))
    logger_task = system.env.process(system.logger.process_request(cpu_ms=40, ram_gb=4, req_type=req_type))
    yield system.env.all_of([s3_task, logger_task])
    
    yield system.env.process(system.app2.process_request(cpu_ms=100, ram_gb=8, req_type=req_type))
```

### 3. Pattern Selection Logic

**Weighted Random Selection:**
```python
def select_request_pattern():
    """Select request pattern based on weighted probabilities"""
    patterns = [
        (RequestType.SIMPLE_READ, 40.0),
        (RequestType.USER_AUTH, 25.0),
        (RequestType.DATA_PROCESSING, 20.0),
        (RequestType.FILE_UPLOAD, 8.0),
        (RequestType.ANALYTICS, 5.0),
        (RequestType.ADMIN_TASK, 2.0)
    ]
    
    total_weight = sum(weight for _, weight in patterns)
    rand = random.uniform(0, total_weight)
    
    cumulative = 0
    for pattern_type, weight in patterns:
        cumulative += weight
        if rand <= cumulative:
            return pattern_type
    
    return RequestType.SIMPLE_READ  # Fallback
```

### 4. Pattern-Specific Metrics

**Enhanced Server Metrics:**
```python
class Server:
    def __init__(self, env, name, threads=4, ram_gb=32, disk_q=16, net_mbps=1000):
        # ... existing initialization ...
        self.request_types = defaultdict(int)  # Pattern-specific counters
        
    def process_request(self, cpu_ms=50, ram_gb=1, disk_mb=10, net_mb=5, req_type=None):
        # ... existing processing ...
        
        if req_type:
            self.request_types[req_type.value] += 1
```

**Pattern Performance Tracking:**
```python
class MicroserviceSystem:
    def __init__(self, env):
        # ... existing initialization ...
        self.pattern_metrics = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'success_count': 0,
            'avg_time': 0.0
        })
```

## 🚀 Implementation Instructions

### Integration Requirements:
1. **Modify existing Server class** to accept `req_type` parameter
2. **Create pattern flow functions** as shown above
3. **Implement pattern selection logic** with proper weighting
4. **Update request handler** to use selected patterns
5. **Enhance metrics collection** for pattern-specific analysis

### Expected Enhancements:
- Realistic workload distribution
- Different resource usage patterns per request type
- Parallel and asynchronous processing capabilities
- Pattern-specific performance analysis

## 📊 Success Criteria

**Functional Requirements:**
- ✅ All 6 patterns working with correct probability distribution
- ✅ Parallel processing (auth/policy, service/db, s3/logger) functional
- ✅ Pattern-specific metrics collection
- ✅ Realistic processing times per pattern

**Analysis Output:**
- ✅ Pattern distribution matching expected probabilities
- ✅ Per-pattern performance metrics
- ✅ Server utilization by pattern type
- ✅ Bottleneck identification per pattern

## 🎯 Implementation Request

Please enhance an existing basic SimPy microservice simulation with sophisticated multi-pattern request processing that demonstrates:
1. Realistic business workflow patterns
2. Weighted probability distribution
3. Parallel and asynchronous processing
4. Pattern-specific performance analysis

This will transform a basic simulation into a realistic microservice performance modeling tool.

---

**Use Case**: Realistic workload simulation, capacity planning, pattern-specific optimization  
**Extension Base**: Should build upon existing basic simulation  
**Complexity Added**: Moderate - pattern routing and parallel processing