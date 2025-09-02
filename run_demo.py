#!/usr/bin/env python3
"""
Quick Demo Runner for SimPy API Service

Run various demos easily after reorganization.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def run_simulation_demo():
    """Run basic microservice simulation."""
    from simulations.simpy_microservice import main
    print("🚀 Running Basic Microservice Simulation...")
    main()

def run_train_tracker():
    """Run railway tracking demo."""
    from visualization.train_tracker import demo_train_tracking
    print("🚄 Starting Railway Tracker Demo...")
    demo_train_tracking()

def run_realtime_visualizer():
    """Run real-time progress visualization."""
    from visualization.realtime_visualizer import demo_batch_processing
    print("📊 Starting Real-time Progress Visualization...")
    demo_batch_processing()

def run_sequence_diagram():
    """Generate sequence diagrams from traces."""
    from tracing.sequence_diagram_generator import demo_pattern_flows, SequenceDiagramGenerator
    print("📈 Generating Sequence Diagrams...")
    tracer = demo_pattern_flows()
    generator = SequenceDiagramGenerator(tracer)
    generator.generate_all_diagrams("auto_sequence_diagrams.md")
    print("✅ Diagrams saved to auto_sequence_diagrams.md")

def main():
    """Main menu for demo selection."""
    print("\n" + "="*60)
    print("🚀 SimPy API Service - Demo Runner")
    print("="*60)
    print("\nChoose a demo to run:")
    print("1. Basic Microservice Simulation")
    print("2. Railway Tracking System (Fun!)")
    print("3. Real-time Progress Visualization")
    print("4. Generate Sequence Diagrams")
    print("5. Exit")
    print("-"*60)
    
    try:
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            run_simulation_demo()
        elif choice == "2":
            run_train_tracker()
        elif choice == "3":
            run_realtime_visualizer()
        elif choice == "4":
            run_sequence_diagram()
        elif choice == "5":
            print("👋 Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid choice. Please try again.")
            main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()