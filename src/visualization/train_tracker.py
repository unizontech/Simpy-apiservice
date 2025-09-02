#!/usr/bin/env python3
"""
Real-time Train Position Tracker

For railway enthusiasts who want to know exactly where their trains are!
"""

import time
import threading
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import os

class TrainStatus(Enum):
    STOPPED = "🚏"
    RUNNING = "🚄"
    DELAYED = "⏰"
    EXPRESS = "🚅"
    LOCAL = "🚃"
    FREIGHT = "🚋"
    MAINTENANCE = "🔧"

class StationStatus(Enum):
    APPROACHING = "🔸"
    ARRIVING = "🟡"
    STOPPED = "🔴"
    DEPARTING = "🟢"
    PASSED = "⚫"

@dataclass
class Station:
    """Railway station."""
    name: str
    km_mark: float  # Distance from origin in km
    platform_count: int = 2
    is_express_stop: bool = False
    transfer_lines: List[str] = field(default_factory=list)

@dataclass
class TrainPosition:
    """Real-time train position."""
    train_id: str
    current_km: float
    speed_kmh: float
    next_station: str
    distance_to_next: float
    estimated_arrival: Optional[datetime] = None
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class Train:
    """Train information."""
    train_id: str
    train_type: str  # "Local", "Express", "Limited Express"
    line_name: str
    destination: str
    car_count: int
    status: TrainStatus = TrainStatus.STOPPED
    current_position: Optional[TrainPosition] = None
    schedule: List[Tuple[str, datetime]] = field(default_factory=list)  # (station, time)
    delay_minutes: int = 0

class RailwayLine:
    """Railway line with stations and trains."""
    
    def __init__(self, name: str, stations: List[Station]):
        self.name = name
        self.stations = sorted(stations, key=lambda s: s.km_mark)
        self.station_map = {station.name: station for station in self.stations}
        self.trains: Dict[str, Train] = {}
        
    def add_train(self, train: Train):
        """Add a train to this line."""
        self.trains[train.train_id] = train
    
    def get_station_by_km(self, km: float) -> Optional[Station]:
        """Find the nearest station to a km mark."""
        if not self.stations:
            return None
        
        # Find closest station
        closest = min(self.stations, key=lambda s: abs(s.km_mark - km))
        return closest
    
    def get_next_station(self, current_km: float, direction: str = "up") -> Optional[Station]:
        """Get the next station in the direction of travel."""
        if direction == "up":
            # Going towards higher km marks
            next_stations = [s for s in self.stations if s.km_mark > current_km]
            return min(next_stations, key=lambda s: s.km_mark) if next_stations else None
        else:
            # Going towards lower km marks  
            next_stations = [s for s in self.stations if s.km_mark < current_km]
            return max(next_stations, key=lambda s: s.km_mark) if next_stations else None

class TrainTracker:
    """Real-time train tracking system."""
    
    def __init__(self, update_interval: float = 5.0):
        self.lines: Dict[str, RailwayLine] = {}
        self.update_interval = update_interval
        self._running = False
        self._tracker_thread: Optional[threading.Thread] = None
        self.tracking_history: Dict[str, List[TrainPosition]] = {}
    
    def add_line(self, line: RailwayLine):
        """Add a railway line to track."""
        self.lines[line.name] = line
    
    def update_train_position(self, line_name: str, train_id: str, current_km: float, 
                            speed_kmh: float, direction: str = "up"):
        """Update a train's position."""
        if line_name not in self.lines:
            return
        
        line = self.lines[line_name]
        if train_id not in line.trains:
            return
        
        train = line.trains[train_id]
        
        # Find next station
        next_station = line.get_next_station(current_km, direction)
        next_station_name = next_station.name if next_station else "終点"
        distance_to_next = abs(next_station.km_mark - current_km) if next_station else 0
        
        # Calculate ETA
        eta = None
        if speed_kmh > 0 and distance_to_next > 0:
            hours_to_arrival = distance_to_next / speed_kmh
            eta = datetime.now() + timedelta(hours=hours_to_arrival)
        
        # Update position
        position = TrainPosition(
            train_id=train_id,
            current_km=current_km,
            speed_kmh=speed_kmh,
            next_station=next_station_name,
            distance_to_next=distance_to_next,
            estimated_arrival=eta
        )
        
        train.current_position = position
        
        # Update train status based on speed
        if speed_kmh == 0:
            train.status = TrainStatus.STOPPED
        elif speed_kmh > 100:
            train.status = TrainStatus.EXPRESS
        else:
            train.status = TrainStatus.RUNNING
        
        # Store history
        if train_id not in self.tracking_history:
            self.tracking_history[train_id] = []
        self.tracking_history[train_id].append(position)
        
        # Keep only last 100 positions
        if len(self.tracking_history[train_id]) > 100:
            self.tracking_history[train_id] = self.tracking_history[train_id][-100:]
    
    def start_tracking(self):
        """Start real-time tracking."""
        if self._running:
            return
        
        self._running = True
        self._tracker_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._tracker_thread.start()
    
    def stop_tracking(self):
        """Stop real-time tracking."""
        self._running = False
        if self._tracker_thread:
            self._tracker_thread.join()
    
    def _tracking_loop(self):
        """Main tracking loop."""
        while self._running:
            self._render_dashboard()
            time.sleep(self.update_interval)
    
    def _render_dashboard(self):
        """Render the railway tracking dashboard."""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("🚄 Real-time Railway Tracker Dashboard")
        print("=" * 80)
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')} | Lines: {len(self.lines)} | Update: {self.update_interval}s")
        print()
        
        # Show each line
        for line_name, line in self.lines.items():
            self._render_line(line)
            print()
    
    def _render_line(self, line: RailwayLine):
        """Render a single railway line."""
        print(f"🚉 {line.name} Line")
        print("-" * 60)
        
        if not line.trains:
            print("   No active trains")
            return
        
        # Show line map with train positions
        self._render_line_map(line)
        print()
        
        # Show detailed train information
        for train in line.trains.values():
            self._render_train_details(train)
    
    def _render_line_map(self, line: RailwayLine):
        """Render a visual line map with train positions."""
        print("   Line Map:")
        
        # Create a simple text-based map
        total_distance = line.stations[-1].km_mark - line.stations[0].km_mark
        map_width = 60
        
        # Station positions on the map
        station_positions = {}
        for station in line.stations:
            relative_pos = (station.km_mark - line.stations[0].km_mark) / total_distance
            map_pos = int(relative_pos * map_width)
            station_positions[station.name] = map_pos
        
        # Create map line
        map_line = ['-'] * map_width
        
        # Add stations
        for station_name, pos in station_positions.items():
            if pos < len(map_line):
                map_line[pos] = '|'
        
        # Add trains
        train_symbols = []
        for train in line.trains.values():
            if train.current_position:
                relative_pos = (train.current_position.current_km - line.stations[0].km_mark) / total_distance
                map_pos = int(relative_pos * map_width)
                if 0 <= map_pos < map_width:
                    symbol = train.status.value
                    map_line[map_pos] = symbol
                    train_symbols.append((map_pos, train.train_id, symbol))
        
        print(f"   {''.join(map_line)}")
        
        # Station labels
        labels = [' '] * map_width
        for i, (station_name, pos) in enumerate(station_positions.items()):
            if pos < len(labels) and i % 2 == 0:  # Show every other station to avoid crowding
                short_name = station_name[:3] if len(station_name) > 3 else station_name
                for j, char in enumerate(short_name):
                    if pos + j < len(labels):
                        labels[pos + j] = char
        
        print(f"   {''.join(labels)}")
    
    def _render_train_details(self, train: Train):
        """Render detailed train information."""
        status_icon = train.status.value
        
        print(f"   {status_icon} {train.train_id} ({train.train_type})")
        print(f"      Destination: {train.destination}")
        
        if train.current_position:
            pos = train.current_position
            print(f"      Position: {pos.current_km:.1f}km")
            print(f"      Speed: {pos.speed_kmh:.0f} km/h")
            print(f"      Next Station: {pos.next_station} ({pos.distance_to_next:.1f}km)")
            
            if pos.estimated_arrival:
                eta_str = pos.estimated_arrival.strftime('%H:%M:%S')
                print(f"      ETA: {eta_str}")
            
            if train.delay_minutes != 0:
                delay_str = f"+{train.delay_minutes}min" if train.delay_minutes > 0 else f"{train.delay_minutes}min"
                print(f"      Delay: {delay_str}")
        
        print()
    
    def get_train_journey(self, train_id: str) -> Optional[List[TrainPosition]]:
        """Get the journey history of a train."""
        return self.tracking_history.get(train_id, [])
    
    def export_positions(self, filename: str):
        """Export current positions to JSON."""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'lines': {}
        }
        
        for line_name, line in self.lines.items():
            export_data['lines'][line_name] = {
                'stations': [
                    {
                        'name': station.name,
                        'km_mark': station.km_mark,
                        'is_express_stop': station.is_express_stop
                    }
                    for station in line.stations
                ],
                'trains': {}
            }
            
            for train_id, train in line.trains.items():
                train_data = {
                    'train_type': train.train_type,
                    'destination': train.destination,
                    'car_count': train.car_count,
                    'status': train.status.name,
                    'delay_minutes': train.delay_minutes
                }
                
                if train.current_position:
                    pos = train.current_position
                    train_data['position'] = {
                        'current_km': pos.current_km,
                        'speed_kmh': pos.speed_kmh,
                        'next_station': pos.next_station,
                        'distance_to_next': pos.distance_to_next,
                        'estimated_arrival': pos.estimated_arrival.isoformat() if pos.estimated_arrival else None
                    }
                
                export_data['lines'][line_name]['trains'][train_id] = train_data
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"🚄 Train positions exported to {filename}")

# Demo setup for a realistic railway line
def create_demo_yamanote_line():
    """Create a demo Yamanote Line (山手線) setup."""
    
    # Yamanote Line stations (simplified)
    stations = [
        Station("東京", 0.0, 10, True),
        Station("有楽町", 1.0, 4),
        Station("新橋", 2.3, 6, True),
        Station("浜松町", 3.6, 4),
        Station("田町", 5.2, 4),
        Station("品川", 6.8, 12, True, ["東海道線", "京急線"]),
        Station("大崎", 9.2, 6, True),
        Station("五反田", 11.0, 4),
        Station("目黒", 12.9, 6, True, ["南北線", "三田線"]),
        Station("恵比寿", 14.6, 6, True),
        Station("渋谷", 16.7, 10, True, ["銀座線", "半蔵門線"]),
        Station("原宿", 18.3, 4),
        Station("代々木", 19.7, 4),
        Station("新宿", 21.3, 16, True, ["中央線", "小田急線"]),
        Station("新大久保", 23.0, 4),
        Station("高田馬場", 24.2, 6, True, ["西武新宿線"]),
        Station("目白", 25.5, 4),
        Station("池袋", 27.0, 14, True, ["丸ノ内線", "東武東上線"]),
        Station("大塚", 29.4, 4),
        Station("巣鴨", 31.2, 4),
        Station("駒込", 32.8, 4),
        Station("田端", 34.5, 4),
        Station("西日暮里", 36.2, 6, True),
        Station("日暮里", 37.8, 6, True, ["京成線"]),
        Station("鶯谷", 39.5, 4),
        Station("上野", 41.1, 12, True, ["銀座線", "東北新幹線"]),
        Station("御徒町", 42.6, 4),
        Station("秋葉原", 44.2, 10, True, ["総武線", "つくばエクスプレス"]),
        Station("神田", 46.0, 6),
        Station("東京", 47.8, 10, True)  # Back to start
    ]
    
    line = RailwayLine("山手線", stations[:-1])  # Remove duplicate Tokyo station
    
    return line

def demo_train_tracking():
    """Demo showing real-time train tracking."""
    
    # Create railway line
    yamanote = create_demo_yamanote_line()
    
    # Create trains
    trains = [
        Train("Y001", "各駅停車", "山手線", "外回り", 11, TrainStatus.RUNNING),
        Train("Y002", "各駅停車", "山手線", "内回り", 11, TrainStatus.RUNNING),
        Train("Y003", "各駅停車", "山手線", "外回り", 11, TrainStatus.RUNNING),
        Train("E001", "特急", "山手線", "品川", 10, TrainStatus.EXPRESS)
    ]
    
    for train in trains:
        yamanote.add_train(train)
    
    # Create tracker
    tracker = TrainTracker(update_interval=2.0)
    tracker.add_line(yamanote)
    
    # Start tracking
    tracker.start_tracking()
    
    # Simulate train movement
    def simulate_trains():
        positions = {
            "Y001": 5.0,   # Start at different positions
            "Y002": 25.0,
            "Y003": 40.0,
            "E001": 0.0
        }
        
        speeds = {
            "Y001": 45,    # km/h
            "Y002": 42,
            "Y003": 40,
            "E001": 65     # Express is faster
        }
        
        while tracker._running:
            for train_id in positions:
                # Update position (simplified simulation)
                positions[train_id] += speeds[train_id] * (2.0 / 3600)  # 2 second intervals
                
                # Loop around the line
                if positions[train_id] > 47.8:
                    positions[train_id] = 0.0
                
                tracker.update_train_position("山手線", train_id, positions[train_id], speeds[train_id])
                
                # Add some randomness to speeds
                speeds[train_id] += (-2 + 4 * time.time() % 1) * 0.1  # Small speed variations
                speeds[train_id] = max(20, min(80, speeds[train_id]))  # Keep within reasonable bounds
            
            time.sleep(2.0)
    
    # Start simulation
    sim_thread = threading.Thread(target=simulate_trains, daemon=True)
    sim_thread.start()
    
    # Let it run for a while
    try:
        time.sleep(30)  # Run for 30 seconds
    except KeyboardInterrupt:
        pass
    finally:
        tracker.stop_tracking()
        tracker.export_positions("yamanote_positions.json")

if __name__ == "__main__":
    print("🚄 Starting Railway Real-time Tracker Demo...")
    print("山手線 (Yamanote Line) simulation starting...")
    demo_train_tracking()