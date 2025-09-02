#!/usr/bin/env python3
"""
Request Tracer Module for SimPy Microservice Simulation

Provides request path visualization and tracing capabilities.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json

@dataclass
class TraceEvent:
    """Individual trace event for a request."""
    timestamp: float
    server: str
    event_type: str  # 'start', 'end', 'wait'
    duration_ms: Optional[float] = None
    resource_usage: Optional[Dict[str, Any]] = None
    queue_info: Optional[Dict[str, Any]] = None

@dataclass
class RequestTrace:
    """Complete trace for a single request."""
    request_id: str
    pattern: str
    start_time: float
    end_time: Optional[float] = None
    events: List[TraceEvent] = None
    total_duration: Optional[float] = None
    success: bool = True
    
    def __post_init__(self):
        if self.events is None:
            self.events = []
    
    def add_event(self, server: str, event_type: str, timestamp: float = None, 
                  duration_ms: float = None, resource_usage: Dict = None, 
                  queue_info: Dict = None):
        """Add a trace event to this request."""
        if timestamp is None:
            timestamp = time.time()
        
        event = TraceEvent(
            timestamp=timestamp,
            server=server,
            event_type=event_type,
            duration_ms=duration_ms,
            resource_usage=resource_usage,
            queue_info=queue_info
        )
        self.events.append(event)
    
    def complete(self, end_time: float = None):
        """Mark request as completed."""
        if end_time is None:
            end_time = time.time()
        self.end_time = end_time
        self.total_duration = end_time - self.start_time
    
    def get_path(self) -> List[str]:
        """Get the server path this request took."""
        path = []
        current_server = None
        
        for event in self.events:
            if event.event_type == 'start' and event.server != current_server:
                path.append(event.server)
                current_server = event.server
        
        return path
    
    def get_timing_summary(self) -> Dict[str, float]:
        """Get timing breakdown by server."""
        timing = {}
        
        for event in self.events:
            if event.event_type == 'end' and event.duration_ms:
                if event.server not in timing:
                    timing[event.server] = 0
                timing[event.server] += event.duration_ms
        
        return timing

class RequestTracer:
    """Main tracer class for tracking request flows."""
    
    def __init__(self):
        self.traces: Dict[str, RequestTrace] = {}
        self.pattern_paths: Dict[str, List[str]] = {}
    
    def start_request(self, request_id: str, pattern: str, start_time: float = None) -> RequestTrace:
        """Start tracing a new request."""
        if start_time is None:
            start_time = time.time()
        
        trace = RequestTrace(
            request_id=request_id,
            pattern=pattern,
            start_time=start_time
        )
        
        self.traces[request_id] = trace
        return trace
    
    def trace_server_start(self, request_id: str, server: str, sim_time: float, 
                          resource_usage: Dict = None, queue_info: Dict = None):
        """Trace when a request starts processing on a server."""
        if request_id in self.traces:
            self.traces[request_id].add_event(
                server=server,
                event_type='start',
                timestamp=sim_time,
                resource_usage=resource_usage,
                queue_info=queue_info
            )
    
    def trace_server_end(self, request_id: str, server: str, sim_time: float, 
                        duration_ms: float, resource_usage: Dict = None):
        """Trace when a request finishes processing on a server."""
        if request_id in self.traces:
            self.traces[request_id].add_event(
                server=server,
                event_type='end',
                timestamp=sim_time,
                duration_ms=duration_ms,
                resource_usage=resource_usage
            )
    
    def complete_request(self, request_id: str, end_time: float = None, success: bool = True):
        """Mark a request as completed."""
        if request_id in self.traces:
            trace = self.traces[request_id]
            trace.complete(end_time)
            trace.success = success
            
            # Update pattern paths
            path = trace.get_path()
            if trace.pattern not in self.pattern_paths:
                self.pattern_paths[trace.pattern] = path
    
    def get_request_path(self, request_id: str) -> Optional[List[str]]:
        """Get the path a specific request took."""
        if request_id in self.traces:
            return self.traces[request_id].get_path()
        return None
    
    def get_pattern_paths(self) -> Dict[str, List[str]]:
        """Get typical paths for each pattern."""
        return self.pattern_paths.copy()
    
    def print_request_trace(self, request_id: str):
        """Print detailed trace for a request."""
        if request_id not in self.traces:
            print(f"No trace found for request {request_id}")
            return
        
        trace = self.traces[request_id]
        print(f"\n=== Request Trace: {request_id} ===")
        print(f"Pattern: {trace.pattern}")
        print(f"Total Duration: {trace.total_duration:.3f}s")
        print(f"Success: {trace.success}")
        print(f"Path: {' → '.join(trace.get_path())}")
        print("\nDetailed Timeline:")
        
        for i, event in enumerate(trace.events):
            print(f"  {i+1:2d}. {event.timestamp:.3f}s - {event.server:12} - {event.event_type:5}")
            if event.duration_ms:
                print(f"      Duration: {event.duration_ms:.1f}ms")
            if event.queue_info:
                print(f"      Queue: {event.queue_info}")
    
    def print_pattern_summary(self):
        """Print summary of all patterns and their paths."""
        print("\n=== Pattern Path Summary ===")
        for pattern, path in self.pattern_paths.items():
            print(f"{pattern:20}: {' → '.join(path)}")
    
    def export_traces(self, filename: str):
        """Export all traces to JSON file."""
        export_data = {
            'pattern_paths': self.pattern_paths,
            'request_traces': {}
        }
        
        for req_id, trace in self.traces.items():
            export_data['request_traces'][req_id] = {
                'pattern': trace.pattern,
                'start_time': trace.start_time,
                'end_time': trace.end_time,
                'total_duration': trace.total_duration,
                'success': trace.success,
                'path': trace.get_path(),
                'timing_summary': trace.get_timing_summary(),
                'events': [
                    {
                        'timestamp': event.timestamp,
                        'server': event.server,
                        'event_type': event.event_type,
                        'duration_ms': event.duration_ms,
                        'resource_usage': event.resource_usage,
                        'queue_info': event.queue_info
                    }
                    for event in trace.events
                ]
            }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Traces exported to {filename}")

# Simple integration functions for existing simulation
def create_tracer() -> RequestTracer:
    """Create a new request tracer instance."""
    return RequestTracer()

def trace_request_flow(tracer: RequestTracer, request_id: str, pattern: str, 
                      servers: List[str], durations: List[float]):
    """Quick function to trace a complete request flow."""
    trace = tracer.start_request(request_id, pattern)
    
    current_time = trace.start_time
    for i, (server, duration) in enumerate(zip(servers, durations)):
        tracer.trace_server_start(request_id, server, current_time)
        current_time += duration / 1000  # Convert ms to seconds
        tracer.trace_server_end(request_id, server, current_time, duration)
    
    tracer.complete_request(request_id, current_time)
    return trace

if __name__ == "__main__":
    # Example usage
    tracer = create_tracer()
    
    # Simulate a simple_read request
    trace_request_flow(
        tracer, 
        "req_001", 
        "simple_read",
        ["Nginx", "APP1", "Service", "APP2"],
        [10, 60, 80, 40]  # durations in ms
    )
    
    # Simulate a user_auth request
    trace_request_flow(
        tracer,
        "req_002",
        "user_auth", 
        ["Nginx", "APP1", "Auth", "Policy", "Service", "APP2"],
        [10, 40, 60, 45, 50, 30]
    )
    
    tracer.print_pattern_summary()
    tracer.print_request_trace("req_001")
    tracer.export_traces("request_traces.json")