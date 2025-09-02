#!/usr/bin/env python3
"""
Demo script showing request tracing capabilities.

Run this to see how request paths are visualized.
"""

from request_tracer import RequestTracer, trace_request_flow
from trace_integration import print_live_trace
import random

def demo_pattern_flows():
    """Demo showing different request pattern flows."""
    
    tracer = RequestTracer()
    
    # Define the 6 request patterns and their typical server flows
    pattern_flows = {
        "simple_read": {
            "servers": ["Nginx", "APP1", "Service", "APP2"],
            "durations": [10, 60, 80, 40]
        },
        "user_auth": {
            "servers": ["Nginx", "APP1", "Auth", "Policy", "Service", "APP2"],
            "durations": [10, 40, 60, 45, 50, 30]
        },
        "data_processing": {
            "servers": ["Nginx", "APP1", "Service", "DB", "ServiceHub", "APP2"],
            "durations": [10, 50, 100, 200, 80, 60]
        },
        "file_upload": {
            "servers": ["Nginx", "APP1", "Auth", "Service", "S3", "Logger", "APP2"],
            "durations": [15, 80, 40, 120, 30, 25, 40]
        },
        "analytics": {
            "servers": ["Nginx", "APP1", "Service", "DB", "ServiceHub", "APP2", "Logger"],
            "durations": [10, 100, 300, 400, 200, 80, 30]
        },
        "admin_task": {
            "servers": ["Nginx", "APP1", "Auth", "Policy", "Service", "DB", "ServiceHub", "S3", "Logger", "APP2"],
            "durations": [20, 150, 80, 120, 250, 300, 180, 50, 40, 100]
        }
    }
    
    print("🚀 SimPy Microservice Request Tracing Demo")
    print("=" * 50)
    
    # Simulate requests for each pattern
    request_counter = 1
    
    for pattern_name, flow in pattern_flows.items():
        print(f"\n📋 Tracing {pattern_name} pattern...")
        
        # Simulate multiple requests of this pattern
        for i in range(3):
            request_id = f"req_{request_counter:03d}"
            
            # Add some randomness to durations (±20%)
            varied_durations = [
                duration * (0.8 + random.random() * 0.4) 
                for duration in flow["durations"]
            ]
            
            trace_request_flow(
                tracer, 
                request_id, 
                pattern_name,
                flow["servers"],
                varied_durations
            )
            
            request_counter += 1
    
    # Show pattern summary
    print("\n" + "=" * 50)
    print("📊 PATTERN FLOW SUMMARY")
    print("=" * 50)
    
    tracer.print_pattern_summary()
    
    # Show detailed trace for one request of each pattern
    print("\n" + "=" * 50)
    print("🔍 DETAILED REQUEST TRACES")
    print("=" * 50)
    
    sample_requests = ["req_001", "req_004", "req_007", "req_010", "req_013", "req_016"]
    
    for req_id in sample_requests:
        if req_id in tracer.traces:
            tracer.print_request_trace(req_id)
    
    # Export results
    tracer.export_traces("demo_traces.json")
    
    # Show live trace view
    print("\n" + "=" * 50) 
    print("📈 LIVE TRACE VIEW")
    print("=" * 50)
    
    print_live_trace(tracer)
    
    return tracer

def demo_bottleneck_analysis(tracer: RequestTracer):
    """Analyze bottlenecks from traced requests."""
    
    print("\n" + "=" * 50)
    print("⚡ BOTTLENECK ANALYSIS")
    print("=" * 50)
    
    # Analyze timing by server across all requests
    server_times = {}
    server_counts = {}
    
    for trace in tracer.traces.values():
        timing = trace.get_timing_summary()
        for server, duration in timing.items():
            if server not in server_times:
                server_times[server] = 0
                server_counts[server] = 0
            server_times[server] += duration
            server_counts[server] += 1
    
    # Calculate average times
    print("Average processing time by server:")
    server_avg = {}
    for server in server_times:
        avg_time = server_times[server] / server_counts[server]
        server_avg[server] = avg_time
        print(f"  {server:12}: {avg_time:6.1f}ms ({server_counts[server]} requests)")
    
    # Identify bottlenecks
    print("\nPotential bottlenecks (servers with >100ms avg):")
    bottlenecks = {k: v for k, v in server_avg.items() if v > 100}
    
    for server, avg_time in sorted(bottlenecks.items(), key=lambda x: x[1], reverse=True):
        print(f"  🚨 {server}: {avg_time:.1f}ms")
    
    # Pattern-specific analysis
    print("\nPattern complexity analysis:")
    pattern_times = {}
    for trace in tracer.traces.values():
        if trace.pattern not in pattern_times:
            pattern_times[trace.pattern] = []
        if trace.total_duration:
            pattern_times[trace.pattern].append(trace.total_duration * 1000)  # Convert to ms
    
    for pattern, times in pattern_times.items():
        if times:
            avg_time = sum(times) / len(times)
            max_time = max(times)
            print(f"  {pattern:15}: avg={avg_time:6.1f}ms, max={max_time:6.1f}ms")

def demo_real_time_monitoring():
    """Demo real-time request monitoring."""
    
    print("\n" + "=" * 50)
    print("📡 REAL-TIME MONITORING DEMO")
    print("=" * 50)
    
    tracer = RequestTracer()
    
    # Simulate real-time requests coming in
    patterns = ["simple_read", "user_auth", "data_processing"]
    
    print("Simulating real-time requests...")
    print("(Request ID | Pattern | Path)")
    print("-" * 60)
    
    for i in range(10):
        pattern = random.choice(patterns)
        request_id = f"live_req_{i+1:02d}"
        
        # Quick trace for demo
        if pattern == "simple_read":
            servers = ["Nginx", "APP1", "Service", "APP2"]
            durations = [10, 60, 80, 40]
        elif pattern == "user_auth":
            servers = ["Nginx", "APP1", "Auth", "Policy", "Service", "APP2"] 
            durations = [10, 40, 60, 45, 50, 30]
        else:  # data_processing
            servers = ["Nginx", "APP1", "Service", "DB", "ServiceHub", "APP2"]
            durations = [10, 50, 100, 200, 80, 60]
        
        trace_request_flow(tracer, request_id, pattern, servers, durations)
        
        # Show immediate result
        path = " → ".join(servers)
        print(f"{request_id} | {pattern:15} | {path}")
    
    print("\n📊 Real-time Summary:")
    print_live_trace(tracer)

if __name__ == "__main__":
    # Run all demos
    print("🎯 Starting Request Tracing Demonstration\n")
    
    # Main pattern flow demo
    tracer = demo_pattern_flows()
    
    # Bottleneck analysis
    demo_bottleneck_analysis(tracer)
    
    # Real-time monitoring demo
    demo_real_time_monitoring()
    
    print(f"\n✅ Demo complete! Check 'demo_traces.json' for exported data.")
    print("💡 Integration tip: Use trace_integration.py to add this to your existing simulation.")