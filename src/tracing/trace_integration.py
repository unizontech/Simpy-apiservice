#!/usr/bin/env python3
"""
Integration helper for adding request tracing to existing SimPy simulations.

Usage:
    from trace_integration import TracingMixin, setup_tracing
    
    # Option 1: Mixin approach
    class TracedServer(Server, TracingMixin):
        pass
    
    # Option 2: Decorator approach
    system = setup_tracing(system)
"""

from request_tracer import RequestTracer, RequestTrace
from typing import Dict, Any, Optional
import functools

class TracingMixin:
    """Mixin class to add tracing capabilities to existing Server classes."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tracer: Optional[RequestTracer] = None
    
    def set_tracer(self, tracer: RequestTracer):
        """Set the tracer for this server."""
        self.tracer = tracer
    
    def trace_process_start(self, request_id: str, sim_time: float, 
                           cpu_ms: float = 0, ram_gb: float = 0, disk_mb: float = 0):
        """Trace the start of request processing."""
        if self.tracer:
            resource_usage = {
                'cpu_ms': cpu_ms,
                'ram_gb': ram_gb, 
                'disk_mb': disk_mb,
                'cpu_queue': len(self.cpu.queue) if hasattr(self, 'cpu') else 0,
                'ram_available': self.ram.level if hasattr(self, 'ram') else 0
            }
            
            queue_info = {
                'cpu_queue_length': len(self.cpu.queue) if hasattr(self, 'cpu') else 0,
                'disk_queue_length': len(self.disk.queue) if hasattr(self, 'disk') else 0
            }
            
            self.tracer.trace_server_start(
                request_id, 
                self.name, 
                sim_time,
                resource_usage=resource_usage,
                queue_info=queue_info
            )
    
    def trace_process_end(self, request_id: str, sim_time: float, duration_ms: float):
        """Trace the end of request processing."""
        if self.tracer:
            resource_usage = {
                'ram_available': self.ram.level if hasattr(self, 'ram') else 0,
                'cpu_utilization': getattr(self, 'cpu_utilization', 0)
            }
            
            self.tracer.trace_server_end(
                request_id,
                self.name,
                sim_time, 
                duration_ms,
                resource_usage=resource_usage
            )

def traced_process_request(original_method):
    """Decorator to add tracing to process_request methods."""
    
    @functools.wraps(original_method)
    def wrapper(self, request_id: str = None, cpu_ms: float = 50, ram_gb: float = 1, 
                disk_mb: float = 10, net_mb: float = 5, req_type=None, **kwargs):
        
        # Generate request ID if not provided
        if request_id is None:
            request_id = f"req_{int(self.env.now * 1000)}"
        
        start_time = self.env.now
        
        # Trace start
        if hasattr(self, 'tracer') and self.tracer:
            self.trace_process_start(request_id, start_time, cpu_ms, ram_gb, disk_mb)
        
        # Call original method
        result = original_method(self, cpu_ms=cpu_ms, ram_gb=ram_gb, 
                               disk_mb=disk_mb, net_mb=net_mb, req_type=req_type, **kwargs)
        
        # Trace end
        end_time = self.env.now
        duration_ms = (end_time - start_time) * 1000
        
        if hasattr(self, 'tracer') and self.tracer:
            self.trace_process_end(request_id, end_time, duration_ms)
        
        return result
    
    return wrapper

def setup_tracing(system_or_servers, tracer: RequestTracer = None) -> RequestTracer:
    """Setup tracing for a system or list of servers."""
    
    if tracer is None:
        tracer = RequestTracer()
    
    # Handle single system object
    if hasattr(system_or_servers, 'get_all_servers'):
        servers = system_or_servers.get_all_servers()
    elif isinstance(system_or_servers, list):
        servers = system_or_servers
    else:
        servers = [system_or_servers]
    
    # Add tracing to each server
    for server in servers:
        # Add tracer
        server.tracer = tracer
        
        # Add tracing methods if not already present
        if not hasattr(server, 'trace_process_start'):
            server.trace_process_start = TracingMixin.trace_process_start.__get__(server)
            server.trace_process_end = TracingMixin.trace_process_end.__get__(server)
        
        # Wrap process_request method if it exists
        if hasattr(server, 'process_request') and not hasattr(server.process_request, '_traced'):
            original_method = server.process_request
            server.process_request = traced_process_request(original_method)
            server.process_request._traced = True
    
    return tracer

# Quick visualization functions
def print_live_trace(tracer: RequestTracer, pattern: str = None):
    """Print live trace information."""
    patterns = tracer.get_pattern_paths()
    
    print("\n=== Live Request Tracing ===")
    
    if pattern and pattern in patterns:
        path = patterns[pattern]
        print(f"{pattern}: {' → '.join(path)}")
    else:
        for p, path in patterns.items():
            print(f"{p:20}: {' → '.join(path)}")
    
    # Show recent requests
    recent_traces = sorted(
        tracer.traces.values(), 
        key=lambda t: t.start_time, 
        reverse=True
    )[:5]
    
    print("\nRecent Requests:")
    for trace in recent_traces:
        status = "✅" if trace.success else "❌"
        duration = f"{trace.total_duration:.3f}s" if trace.total_duration else "ongoing"
        path = " → ".join(trace.get_path())
        print(f"  {status} {trace.request_id:12} [{trace.pattern:15}] {duration:8} | {path}")

# Example integration with existing code
def example_integration():
    """Example of how to integrate with existing simulation."""
    
    # Assuming you have existing Server and MicroserviceSystem classes
    
    # Method 1: Using setup_tracing function
    # system = MicroserviceSystem(env)
    # tracer = setup_tracing(system)
    
    # Method 2: Manual integration
    # tracer = RequestTracer() 
    # for server in system.get_all_servers():
    #     server.tracer = tracer
    
    # Method 3: In request handler
    # def request_handler(system, request_id, pattern):
    #     tracer = system.tracer
    #     trace = tracer.start_request(request_id, pattern, system.env.now)
    #     
    #     # Process through servers...
    #     # Each server automatically traces if tracer is set
    #     
    #     tracer.complete_request(request_id, system.env.now, success=True)
    
    print("See function comments for integration examples")

if __name__ == "__main__":
    example_integration()