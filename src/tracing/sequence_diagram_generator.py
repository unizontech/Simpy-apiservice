#!/usr/bin/env python3
"""
Sequence Diagram Generator from Request Traces

Automatically generates Mermaid sequence diagrams from traced execution flows.
"""

from request_tracer import RequestTracer, RequestTrace
from typing import Dict, List, Set
import re

class SequenceDiagramGenerator:
    """Generate sequence diagrams from request traces."""
    
    def __init__(self, tracer: RequestTracer):
        self.tracer = tracer
    
    def generate_pattern_diagram(self, pattern: str) -> str:
        """Generate sequence diagram for a specific pattern."""
        
        # Get traces for this pattern
        pattern_traces = [
            trace for trace in self.tracer.traces.values() 
            if trace.pattern == pattern
        ]
        
        if not pattern_traces:
            return f"No traces found for pattern: {pattern}"
        
        # Use the first trace as representative
        trace = pattern_traces[0]
        
        # Generate Mermaid sequence diagram
        diagram_lines = [
            "```mermaid",
            "sequenceDiagram",
            f"    title {pattern.replace('_', ' ').title()} Request Flow",
            ""
        ]
        
        # Get unique servers in order
        servers = trace.get_path()
        
        # Add participants
        for server in servers:
            diagram_lines.append(f"    participant {server}")
        
        diagram_lines.append("")
        
        # Add sequence interactions
        client = "Client"
        diagram_lines.append(f"    participant {client}")
        diagram_lines.append("")
        
        # Start request
        if servers:
            first_server = servers[0]
            diagram_lines.append(f"    {client}->>+{first_server}: Request ({pattern})")
        
        # Server-to-server interactions
        current_server = None
        for event in trace.events:
            if event.event_type == 'start':
                if current_server and current_server != event.server:
                    # Call to next server
                    duration = f" ({event.duration_ms:.0f}ms)" if event.duration_ms else ""
                    diagram_lines.append(f"    {current_server}->>+{event.server}: Process{duration}")
                current_server = event.server
            
            elif event.event_type == 'end':
                if event.duration_ms:
                    # Processing time note
                    diagram_lines.append(f"    Note over {event.server}: Process {event.duration_ms:.0f}ms")
        
        # Response flow (reverse order)
        reverse_servers = list(reversed(servers))
        for i in range(len(reverse_servers) - 1):
            current = reverse_servers[i]
            next_server = reverse_servers[i + 1]
            diagram_lines.append(f"    {current}-->>-{next_server}: Response")
        
        # Final response to client
        if servers:
            last_server = servers[-1]
            total_time = trace.total_duration * 1000 if trace.total_duration else 0
            diagram_lines.append(f"    {servers[0]}-->>-{client}: Response ({total_time:.0f}ms total)")
        
        diagram_lines.append("```")
        
        return "\n".join(diagram_lines)
    
    def generate_parallel_diagram(self, pattern: str) -> str:
        """Generate diagram showing parallel processing."""
        
        pattern_traces = [
            trace for trace in self.tracer.traces.values() 
            if trace.pattern == pattern
        ]
        
        if not pattern_traces:
            return f"No traces found for pattern: {pattern}"
        
        trace = pattern_traces[0]
        
        # Detect parallel processing by looking for overlapping timestamps
        parallel_groups = self._detect_parallel_processing(trace)
        
        if not parallel_groups:
            return self.generate_pattern_diagram(pattern)  # Fall back to sequential
        
        diagram_lines = [
            "```mermaid",
            "sequenceDiagram", 
            f"    title {pattern.replace('_', ' ').title()} - Parallel Processing",
            ""
        ]
        
        # Add all servers as participants
        all_servers = set()
        for event in trace.events:
            all_servers.add(event.server)
        
        for server in sorted(all_servers):
            diagram_lines.append(f"    participant {server}")
        
        diagram_lines.append("")
        diagram_lines.append("    participant Client")
        diagram_lines.append("")
        
        # Generate sequence with parallel blocks
        servers = trace.get_path()
        if servers:
            diagram_lines.append(f"    Client->>+{servers[0]}: Request")
        
        # Show parallel processing
        for group in parallel_groups:
            if len(group) > 1:
                diagram_lines.append("    par Parallel Processing")
                for i, server in enumerate(group):
                    prefix = "    and" if i > 0 else "   "
                    diagram_lines.append(f"    {prefix} Processing on {server}")
                diagram_lines.append("    end")
            else:
                server = group[0]
                diagram_lines.append(f"    Note over {server}: Sequential Processing")
        
        if servers:
            diagram_lines.append(f"    {servers[0]}-->>-Client: Response")
        
        diagram_lines.append("```")
        
        return "\n".join(diagram_lines)
    
    def _detect_parallel_processing(self, trace: RequestTrace) -> List[List[str]]:
        """Detect parallel processing from overlapping events."""
        parallel_groups = []
        
        # Simple heuristic: events that overlap in time are parallel
        start_events = [e for e in trace.events if e.event_type == 'start']
        end_events = [e for e in trace.events if e.event_type == 'end']
        
        # Group events by timestamp proximity (within 10ms = parallel)
        current_group = []
        last_timestamp = None
        
        for event in start_events:
            if last_timestamp is None or abs(event.timestamp - last_timestamp) < 0.01:  # 10ms
                current_group.append(event.server)
            else:
                if current_group:
                    parallel_groups.append(current_group)
                current_group = [event.server]
            last_timestamp = event.timestamp
        
        if current_group:
            parallel_groups.append(current_group)
        
        return parallel_groups
    
    def generate_comparison_diagram(self, patterns: List[str]) -> str:
        """Generate comparison diagram for multiple patterns."""
        
        diagram_lines = [
            "```mermaid", 
            "graph TD",
            "    title Request Pattern Comparison",
            ""
        ]
        
        # Generate flowchart showing different paths
        for i, pattern in enumerate(patterns):
            pattern_traces = [
                trace for trace in self.tracer.traces.values() 
                if trace.pattern == pattern
            ]
            
            if pattern_traces:
                trace = pattern_traces[0]
                servers = trace.get_path()
                
                # Create flowchart nodes
                start_node = f"Start{i}"
                end_node = f"End{i}"
                
                diagram_lines.append(f"    {start_node}[{pattern}]")
                
                prev_node = start_node
                for j, server in enumerate(servers):
                    node_id = f"{pattern}_{j}"
                    diagram_lines.append(f"    {node_id}[{server}]")
                    diagram_lines.append(f"    {prev_node} --> {node_id}")
                    prev_node = node_id
                
                diagram_lines.append(f"    {end_node}[Response]")
                diagram_lines.append(f"    {prev_node} --> {end_node}")
                diagram_lines.append("")
        
        diagram_lines.append("```")
        
        return "\n".join(diagram_lines)
    
    def generate_bottleneck_diagram(self) -> str:
        """Generate diagram highlighting bottlenecks."""
        
        # Analyze processing times
        server_times = {}
        server_counts = {}
        
        for trace in self.tracer.traces.values():
            timing = trace.get_timing_summary()
            for server, duration in timing.items():
                if server not in server_times:
                    server_times[server] = 0
                    server_counts[server] = 0
                server_times[server] += duration
                server_counts[server] += 1
        
        # Calculate averages and identify bottlenecks
        server_avg = {}
        for server in server_times:
            server_avg[server] = server_times[server] / server_counts[server]
        
        bottlenecks = {k: v for k, v in server_avg.items() if v > 100}  # >100ms
        
        diagram_lines = [
            "```mermaid",
            "graph TD",
            "    title System Bottlenecks Analysis",
            ""
        ]
        
        # Color code servers by performance
        for server, avg_time in server_avg.items():
            if avg_time > 200:
                color = "fill:#ff9999"  # Red for slow
            elif avg_time > 100:
                color = "fill:#ffcc99"  # Orange for medium
            else:
                color = "fill:#99ff99"  # Green for fast
            
            diagram_lines.append(f"    {server}[{server}<br/>{avg_time:.1f}ms]")
            diagram_lines.append(f"    style {server} {color}")
        
        diagram_lines.append("")
        diagram_lines.append("    classDef bottleneck fill:#ff9999,stroke:#ff0000")
        diagram_lines.append("```")
        
        return "\n".join(diagram_lines)
    
    def generate_all_diagrams(self, output_file: str = "sequence_diagrams.md"):
        """Generate all diagrams and save to markdown file."""
        
        content = [
            "# Request Flow Sequence Diagrams",
            "",
            "Auto-generated from execution traces.",
            "",
        ]
        
        # Pattern-specific diagrams
        patterns = self.tracer.get_pattern_paths().keys()
        
        for pattern in patterns:
            content.extend([
                f"## {pattern.replace('_', ' ').title()} Pattern",
                "",
                self.generate_pattern_diagram(pattern),
                "",
            ])
        
        # Parallel processing diagrams
        content.extend([
            "## Parallel Processing Examples", 
            "",
        ])
        
        parallel_patterns = ["user_auth", "analytics", "file_upload"]
        for pattern in parallel_patterns:
            if pattern in patterns:
                content.extend([
                    f"### {pattern.replace('_', ' ').title()} Parallel Flow",
                    "",
                    self.generate_parallel_diagram(pattern),
                    "",
                ])
        
        # Comparison diagram
        content.extend([
            "## Pattern Comparison",
            "",
            self.generate_comparison_diagram(list(patterns)),
            "",
        ])
        
        # Bottleneck analysis
        content.extend([
            "## Bottleneck Analysis",
            "",
            self.generate_bottleneck_diagram(),
            "",
        ])
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        print(f"✅ Sequence diagrams generated: {output_file}")
        return output_file

# Integration with existing tracer
def create_sequence_generator(tracer: RequestTracer) -> SequenceDiagramGenerator:
    """Create sequence diagram generator from existing tracer."""
    return SequenceDiagramGenerator(tracer)

if __name__ == "__main__":
    # Example usage with existing tracer
    from tracing_demo import demo_pattern_flows
    
    print("🔄 Running demo to generate traces...")
    tracer = demo_pattern_flows()
    
    print("📊 Generating sequence diagrams...")
    generator = SequenceDiagramGenerator(tracer)
    generator.generate_all_diagrams("auto_sequence_diagrams.md")
    
    print("🎯 Done! Check auto_sequence_diagrams.md")