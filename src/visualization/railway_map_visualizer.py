#!/usr/bin/env python3
"""
Railway Map Visualizer

Create detailed ASCII art railway maps showing train positions.
"""

from train_tracker import TrainTracker, RailwayLine, Train, Station
from typing import Dict, List, Tuple
import math
import time

class RailwayMapVisualizer:
    """Advanced railway map visualization."""
    
    def __init__(self, tracker: TrainTracker):
        self.tracker = tracker
        self.map_width = 120
        self.map_height = 30
    
    def create_detailed_line_map(self, line_name: str) -> List[str]:
        """Create a detailed ASCII art map of a railway line."""
        if line_name not in self.tracker.lines:
            return ["Line not found"]
        
        line = self.tracker.lines[line_name]
        map_lines = []
        
        # Header
        map_lines.append(f"🚉 {line_name} Detailed Map")
        map_lines.append("=" * self.map_width)
        
        # Create horizontal track representation
        total_distance = line.stations[-1].km_mark - line.stations[0].km_mark if line.stations else 1
        
        # Main track line
        track_line = ['═'] * self.map_width
        station_line = [' '] * self.map_width
        train_line = [' '] * self.map_width
        info_line = [' '] * self.map_width
        
        # Add stations to map
        station_positions = {}
        for station in line.stations:
            if total_distance > 0:
                relative_pos = (station.km_mark - line.stations[0].km_mark) / total_distance
                map_pos = int(relative_pos * (self.map_width - 1))
                
                # Station marker
                if map_pos < len(track_line):
                    if station.is_express_stop:
                        track_line[map_pos] = '◉'  # Express stop
                    else:
                        track_line[map_pos] = '○'  # Regular stop
                    
                    station_positions[station.name] = map_pos
                    
                    # Station name (abbreviated)
                    station_short = station.name[:6]
                    for i, char in enumerate(station_short):
                        if map_pos + i < len(station_line):
                            station_line[map_pos + i] = char
        
        # Add trains to map
        for train in line.trains.values():
            if train.current_position and total_distance > 0:
                relative_pos = (train.current_position.current_km - line.stations[0].km_mark) / total_distance
                map_pos = int(relative_pos * (self.map_width - 1))
                
                if 0 <= map_pos < len(train_line):
                    # Train symbol based on status
                    symbol = train.status.value
                    train_line[map_pos] = symbol
                    
                    # Train ID below
                    train_id_short = train.train_id[:4]
                    for i, char in enumerate(train_id_short):
                        if map_pos + i < len(info_line):
                            info_line[map_pos + i] = char
        
        # Build the map
        map_lines.append(''.join(track_line))
        map_lines.append(''.join(station_line))
        map_lines.append(''.join(train_line))
        map_lines.append(''.join(info_line))
        map_lines.append("")
        
        return map_lines
    
    def create_train_timetable(self, line_name: str) -> List[str]:
        """Create a real-time timetable."""
        if line_name not in self.tracker.lines:
            return ["Line not found"]
        
        line = self.tracker.lines[line_name]
        timetable_lines = []
        
        timetable_lines.append("📋 Real-time Timetable")
        timetable_lines.append("-" * 80)
        timetable_lines.append(f"{'Train':<8} {'Type':<12} {'Position':<10} {'Speed':<8} {'Next Station':<15} {'ETA':<8} {'Status':<10}")
        timetable_lines.append("-" * 80)
        
        for train in sorted(line.trains.values(), key=lambda t: t.train_id):
            if train.current_position:
                pos = train.current_position
                eta_str = pos.estimated_arrival.strftime('%H:%M') if pos.estimated_arrival else "--:--"
                
                timetable_lines.append(
                    f"{train.train_id:<8} {train.train_type:<12} {pos.current_km:<10.1f} "
                    f"{pos.speed_kmh:<8.0f} {pos.next_station[:14]:<15} {eta_str:<8} "
                    f"{train.status.name:<10}"
                )
        
        return timetable_lines
    
    def create_station_board(self, station_name: str) -> List[str]:
        """Create a station departure board."""
        board_lines = []
        board_lines.append(f"🚉 {station_name} Station - Departure Board")
        board_lines.append("=" * 60)
        
        # Find trains approaching this station
        approaching_trains = []
        for line_name, line in self.tracker.lines.items():
            if station_name in line.station_map:
                station = line.station_map[station_name]
                
                for train in line.trains.values():
                    if train.current_position:
                        distance = abs(train.current_position.current_km - station.km_mark)
                        # Show trains within 10km
                        if distance <= 10.0:
                            approaching_trains.append({
                                'train': train,
                                'distance': distance,
                                'line': line_name
                            })
        
        # Sort by distance
        approaching_trains.sort(key=lambda x: x['distance'])
        
        if not approaching_trains:
            board_lines.append("No trains approaching")
            return board_lines
        
        board_lines.append(f"{'Line':<10} {'Train':<8} {'Type':<12} {'Distance':<10} {'ETA':<8} {'Status':<10}")
        board_lines.append("-" * 60)
        
        for entry in approaching_trains[:10]:  # Show first 10 trains
            train = entry['train']
            distance = entry['distance']
            line = entry['line']
            
            if train.current_position:
                eta_str = train.current_position.estimated_arrival.strftime('%H:%M') if train.current_position.estimated_arrival else "--:--"
                
                board_lines.append(
                    f"{line[:9]:<10} {train.train_id:<8} {train.train_type:<12} "
                    f"{distance:<10.1f} {eta_str:<8} {train.status.name:<10}"
                )
        
        return board_lines
    
    def render_full_dashboard(self, focus_line: str = None, focus_station: str = None):
        """Render a complete railway dashboard."""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("🚄 Railway Otaku Dashboard")
        print("=" * 120)
        print(f"⏰ Current Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # If focusing on a specific line
        if focus_line and focus_line in self.tracker.lines:
            # Detailed line map
            map_lines = self.create_detailed_line_map(focus_line)
            for line in map_lines:
                print(line)
            
            # Timetable
            timetable_lines = self.create_train_timetable(focus_line)
            for line in timetable_lines:
                print(line)
            print()
        
        # If focusing on a specific station
        if focus_station:
            station_board = self.create_station_board(focus_station)
            for line in station_board:
                print(line)
            print()
        
        # Overview of all lines
        print("🌐 System Overview")
        print("-" * 60)
        for line_name, line in self.tracker.lines.items():
            active_trains = len([t for t in line.trains.values() if t.current_position])
            total_trains = len(line.trains)
            
            # Calculate average speed
            speeds = [t.current_position.speed_kmh for t in line.trains.values() 
                     if t.current_position and t.current_position.speed_kmh > 0]
            avg_speed = sum(speeds) / len(speeds) if speeds else 0
            
            print(f"{line_name:<20} | Trains: {active_trains}/{total_trains} | Avg Speed: {avg_speed:.0f} km/h")

# Demo with enhanced visualization
def demo_enhanced_railway_tracking():
    """Demo with enhanced visualization features."""
    
    from train_tracker import create_demo_yamanote_line, demo_train_tracking
    import threading
    
    # Create the setup (same as before)
    yamanote = create_demo_yamanote_line()
    
    trains = [
        Train("Y001E", "各駅停車", "山手線", "外回り", 11),
        Train("Y002N", "各駅停車", "山手線", "内回り", 11),  
        Train("Y003E", "各駅停車", "山手線", "外回り", 11),
        Train("E001", "快速", "山手線", "新宿方面", 10),
        Train("E002", "特急", "山手線", "品川方面", 8)
    ]
    
    for train in trains:
        yamanote.add_train(train)
    
    tracker = TrainTracker(update_interval=3.0)
    tracker.add_line(yamanote)
    
    # Create enhanced visualizer
    visualizer = RailwayMapVisualizer(tracker)
    
    # Simulate train positions
    positions = {"Y001E": 5.0, "Y002N": 25.0, "Y003E": 35.0, "E001": 15.0, "E002": 45.0}
    speeds = {"Y001E": 45, "Y002N": 42, "Y003E": 48, "E001": 65, "E002": 70}
    
    def simulate_movement():
        while tracker._running:
            for train_id in positions:
                positions[train_id] += speeds[train_id] * (3.0 / 3600)
                if positions[train_id] > 47.8:
                    positions[train_id] = 0.0
                
                tracker.update_train_position("山手線", train_id, positions[train_id], speeds[train_id])
            time.sleep(3.0)
    
    # Start simulation
    tracker._running = True
    sim_thread = threading.Thread(target=simulate_movement, daemon=True)
    sim_thread.start()
    
    # Display modes
    print("🚄 Enhanced Railway Visualization Demo")
    print("Switching between different views...")
    
    try:
        for i in range(15):  # 15 iterations, 3 seconds each = 45 seconds total
            if i % 5 == 0:
                # Full line view
                visualizer.render_full_dashboard(focus_line="山手線")
            elif i % 5 == 2:
                # Station focus
                stations = ["新宿", "渋谷", "東京", "品川", "池袋"]
                focus_station = stations[i // 5]
                visualizer.render_full_dashboard(focus_station=focus_station)
            else:
                # Overview
                visualizer.render_full_dashboard()
            
            time.sleep(3.0)
            
    except KeyboardInterrupt:
        pass
    finally:
        tracker._running = False
        tracker.export_positions("enhanced_railway_tracking.json")
        print("\n🚄 Demo completed! Data exported to enhanced_railway_tracking.json")

if __name__ == "__main__":
    print("🚄 Starting Enhanced Railway Visualization...")
    demo_enhanced_railway_tracking()