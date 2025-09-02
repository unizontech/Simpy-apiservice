#!/usr/bin/env python3
"""
Real-time Processing Visualizer

Shows live progress of batch jobs, heavy processing, and system status.
"""

import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime, timedelta
import os
import sys

class ProcessStatus(Enum):
    WAITING = "⏳"
    RUNNING = "🔄" 
    COMPLETED = "✅"
    FAILED = "❌"
    BLOCKED = "🚫"
    RETRYING = "🔁"

@dataclass
class ProcessStep:
    """Individual step in a batch process."""
    name: str
    total_items: int = 0
    completed_items: int = 0
    status: ProcessStatus = ProcessStatus.WAITING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    current_item: str = ""
    error_message: str = ""
    estimated_completion: Optional[float] = None
    
    @property
    def progress_percent(self) -> float:
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100
    
    @property
    def elapsed_time(self) -> float:
        if not self.start_time:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def items_per_second(self) -> float:
        if self.elapsed_time == 0 or self.completed_items == 0:
            return 0.0
        return self.completed_items / self.elapsed_time
    
    @property
    def eta_seconds(self) -> float:
        if self.items_per_second == 0 or self.completed_items == self.total_items:
            return 0.0
        remaining_items = self.total_items - self.completed_items
        return remaining_items / self.items_per_second

@dataclass 
class BatchJob:
    """Complete batch job with multiple steps."""
    name: str
    steps: List[ProcessStep] = field(default_factory=list)
    status: ProcessStatus = ProcessStatus.WAITING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def current_step(self) -> Optional[ProcessStep]:
        for step in self.steps:
            if step.status == ProcessStatus.RUNNING:
                return step
        return None
    
    @property
    def overall_progress(self) -> float:
        if not self.steps:
            return 0.0
        
        total_progress = sum(step.progress_percent for step in self.steps)
        return total_progress / len(self.steps)
    
    @property
    def overall_eta(self) -> float:
        current = self.current_step
        if not current:
            return 0.0
        
        # Remaining time for current step + time for remaining steps
        current_eta = current.eta_seconds
        
        # Estimate remaining steps (rough approximation)
        remaining_steps = len([s for s in self.steps if s.status == ProcessStatus.WAITING])
        if remaining_steps > 0 and current.elapsed_time > 0:
            avg_step_time = current.elapsed_time  # Use current step as estimate
            remaining_eta = remaining_steps * avg_step_time
        else:
            remaining_eta = 0.0
            
        return current_eta + remaining_eta

class RealtimeVisualizer:
    """Real-time visualization of batch processes."""
    
    def __init__(self, update_interval: float = 1.0):
        self.jobs: Dict[str, BatchJob] = {}
        self.update_interval = update_interval
        self._running = False
        self._display_thread: Optional[threading.Thread] = None
        self._clear_screen = os.name == 'nt' and 'cls' or 'clear'
    
    def create_job(self, job_name: str, steps: List[str], step_totals: List[int] = None) -> BatchJob:
        """Create a new batch job."""
        if step_totals is None:
            step_totals = [100] * len(steps)  # Default 100 items per step
        
        job_steps = []
        for i, step_name in enumerate(steps):
            total = step_totals[i] if i < len(step_totals) else 100
            job_steps.append(ProcessStep(name=step_name, total_items=total))
        
        job = BatchJob(name=job_name, steps=job_steps)
        self.jobs[job_name] = job
        return job
    
    def start_job(self, job_name: str):
        """Start a batch job."""
        if job_name in self.jobs:
            job = self.jobs[job_name]
            job.status = ProcessStatus.RUNNING
            job.start_time = time.time()
            
            # Start first step
            if job.steps:
                job.steps[0].status = ProcessStatus.RUNNING
                job.steps[0].start_time = time.time()
    
    def start_step(self, job_name: str, step_name: str):
        """Start a specific step."""
        job = self.jobs.get(job_name)
        if not job:
            return
        
        for step in job.steps:
            if step.name == step_name:
                step.status = ProcessStatus.RUNNING
                step.start_time = time.time()
                break
    
    def update_progress(self, job_name: str, step_name: str, completed: int, current_item: str = ""):
        """Update progress for a specific step."""
        job = self.jobs.get(job_name)
        if not job:
            return
        
        for step in job.steps:
            if step.name == step_name:
                step.completed_items = completed
                step.current_item = current_item
                
                # Auto-complete step if finished
                if step.completed_items >= step.total_items:
                    step.status = ProcessStatus.COMPLETED
                    step.end_time = time.time()
                    
                    # Start next step automatically
                    current_idx = job.steps.index(step)
                    if current_idx + 1 < len(job.steps):
                        next_step = job.steps[current_idx + 1]
                        next_step.status = ProcessStatus.RUNNING
                        next_step.start_time = time.time()
                    else:
                        # Job completed
                        job.status = ProcessStatus.COMPLETED
                        job.end_time = time.time()
                break
    
    def fail_step(self, job_name: str, step_name: str, error: str):
        """Mark a step as failed."""
        job = self.jobs.get(job_name)
        if not job:
            return
        
        for step in job.steps:
            if step.name == step_name:
                step.status = ProcessStatus.FAILED
                step.error_message = error
                step.end_time = time.time()
                job.status = ProcessStatus.FAILED
                break
    
    def start_visualization(self):
        """Start real-time visualization."""
        if self._running:
            return
        
        self._running = True
        self._display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self._display_thread.start()
    
    def stop_visualization(self):
        """Stop real-time visualization."""
        self._running = False
        if self._display_thread:
            self._display_thread.join()
    
    def _display_loop(self):
        """Main display loop."""
        while self._running:
            self._render_dashboard()
            time.sleep(self.update_interval)
    
    def _render_dashboard(self):
        """Render the real-time dashboard."""
        # Clear screen
        os.system(self._clear_screen)
        
        print("🚀 Real-time Processing Dashboard")
        print("=" * 70)
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')} | Jobs: {len(self.jobs)} | Update: {self.update_interval}s")
        print()
        
        if not self.jobs:
            print("📭 No active jobs")
            return
        
        # Show each job
        for job_name, job in self.jobs.items():
            self._render_job(job)
            print()
    
    def _render_job(self, job: BatchJob):
        """Render a single job."""
        status_icon = job.status.value
        
        print(f"{status_icon} {job.name}")
        print(f"   Overall Progress: {job.overall_progress:.1f}%")
        
        if job.overall_eta > 0:
            eta_str = self._format_duration(job.overall_eta)
            print(f"   ETA: {eta_str}")
        
        if job.start_time:
            elapsed = self._format_duration(time.time() - job.start_time)
            print(f"   Elapsed: {elapsed}")
        
        print()
        
        # Show each step
        for i, step in enumerate(job.steps, 1):
            self._render_step(step, i)
    
    def _render_step(self, step: ProcessStep, step_num: int):
        """Render a single step."""
        status_icon = step.status.value
        progress_bar = self._create_progress_bar(step.progress_percent, width=30)
        
        print(f"   {step_num}. {status_icon} {step.name}")
        print(f"      {progress_bar} {step.progress_percent:.1f}%")
        print(f"      Progress: {step.completed_items:,} / {step.total_items:,}")
        
        if step.status == ProcessStatus.RUNNING:
            if step.current_item:
                print(f"      Current: {step.current_item}")
            
            if step.items_per_second > 0:
                print(f"      Speed: {step.items_per_second:.1f} items/sec")
            
            if step.eta_seconds > 0:
                eta_str = self._format_duration(step.eta_seconds)
                print(f"      ETA: {eta_str}")
        
        elif step.status == ProcessStatus.FAILED:
            print(f"      ❌ Error: {step.error_message}")
        
        elif step.status == ProcessStatus.COMPLETED:
            duration = self._format_duration(step.elapsed_time)
            print(f"      ✅ Completed in {duration}")
    
    def _create_progress_bar(self, percent: float, width: int = 30) -> str:
        """Create a visual progress bar."""
        filled = int(width * percent / 100)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def export_status(self, filename: str):
        """Export current status to JSON."""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'jobs': {}
        }
        
        for job_name, job in self.jobs.items():
            export_data['jobs'][job_name] = {
                'name': job.name,
                'status': job.status.name,
                'overall_progress': job.overall_progress,
                'overall_eta': job.overall_eta,
                'start_time': job.start_time,
                'end_time': job.end_time,
                'steps': [
                    {
                        'name': step.name,
                        'status': step.status.name,
                        'progress_percent': step.progress_percent,
                        'completed_items': step.completed_items,
                        'total_items': step.total_items,
                        'current_item': step.current_item,
                        'items_per_second': step.items_per_second,
                        'eta_seconds': step.eta_seconds,
                        'elapsed_time': step.elapsed_time,
                        'error_message': step.error_message
                    }
                    for step in job.steps
                ]
            }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"📊 Status exported to {filename}")

# Integration helpers
def create_visualizer(jobs_config: Dict[str, Dict]) -> RealtimeVisualizer:
    """Create visualizer with job configurations."""
    visualizer = RealtimeVisualizer()
    
    for job_name, config in jobs_config.items():
        steps = config['steps']
        totals = config.get('totals', [100] * len(steps))
        visualizer.create_job(job_name, steps, totals)
    
    return visualizer

# Example usage functions
def demo_batch_processing():
    """Demo showing batch processing visualization."""
    
    visualizer = RealtimeVisualizer(update_interval=0.5)
    
    # Create demo jobs
    visualizer.create_job(
        "Data Migration", 
        ["Extract Data", "Transform Data", "Load to DB", "Validate"],
        [1000, 1000, 1000, 500]
    )
    
    visualizer.create_job(
        "Report Generation",
        ["Collect Metrics", "Process Analytics", "Generate Charts", "Export PDF"],
        [200, 150, 100, 50]
    )
    
    # Start visualization
    visualizer.start_visualization()
    
    # Simulate processing
    simulate_batch_job(visualizer, "Data Migration")
    simulate_batch_job(visualizer, "Report Generation") 
    
    # Keep dashboard running for a bit
    time.sleep(10)
    
    visualizer.stop_visualization()
    visualizer.export_status("batch_status.json")

def simulate_batch_job(visualizer: RealtimeVisualizer, job_name: str):
    """Simulate a batch job running."""
    def run_job():
        visualizer.start_job(job_name)
        job = visualizer.jobs[job_name]
        
        for step in job.steps:
            for i in range(step.total_items + 1):
                visualizer.update_progress(
                    job_name, 
                    step.name, 
                    i,
                    f"Processing item {i}/{step.total_items}"
                )
                time.sleep(0.01)  # Simulate processing time
    
    # Run in background thread
    threading.Thread(target=run_job, daemon=True).start()

if __name__ == "__main__":
    print("🎯 Starting Real-time Processing Visualizer Demo...")
    demo_batch_processing()