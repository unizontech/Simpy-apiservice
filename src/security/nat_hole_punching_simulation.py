#!/usr/bin/env python3
"""
IP&Port穴あけ制御シミュレーション - SimPy ベース
NAT穴あけ、ファイアウォール制御、ゼロトラスト認証の論理モデル

作成日: 2025-09-05
目的: ネットワークセキュリティ制御の性能分析とボトルネック特定
"""

import simpy
import random
import statistics
import json
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import ipaddress

class NATType(Enum):
    """NAT タイプの定義"""
    FULL_CONE = "full_cone"              # 最も穴あけしやすい
    RESTRICTED_CONE = "restricted_cone"   # IP制限あり  
    PORT_RESTRICTED = "port_restricted"   # IP+Port制限あり
    SYMMETRIC = "symmetric"              # 最も厳しい

class TrustLevel(Enum):
    """ゼロトラスト信頼レベル"""
    UNTRUSTED = "untrusted"      # 0% - 初回アクセス
    LOW = "low"                  # 25% - 基本認証済み
    MEDIUM = "medium"            # 50% - デバイス認証済み  
    HIGH = "high"                # 75% - 多要素認証済み
    VERIFIED = "verified"        # 95% - 完全検証済み

@dataclass
class NetworkClient:
    """ネットワーククライアント"""
    client_id: str
    internal_ip: str
    nat_type: NATType
    trust_level: TrustLevel = TrustLevel.UNTRUSTED
    active_holes: List[int] = field(default_factory=list)
    failed_attempts: int = 0
    last_success_time: Optional[float] = None

@dataclass 
class FirewallRule:
    """ファイアウォールルール"""
    src_ip: str
    dst_port: int
    created_time: float
    expires_time: float
    rule_type: str = "hole_punch"
    active: bool = True

class STUNServer:
    """STUN サーバーシミュレータ"""
    def __init__(self, env, processing_capacity=1000):
        self.env = env
        self.cpu = simpy.Resource(env, capacity=processing_capacity)
        self.total_requests = 0
        self.response_times = []
        
    def process_stun_request(self, client: NetworkClient):
        """STUN リクエスト処理"""
        with self.cpu.request() as req:
            yield req
            
            # STUN処理時間（NAT複雑さに依存）
            processing_time = {
                NATType.FULL_CONE: 0.01,
                NATType.RESTRICTED_CONE: 0.02, 
                NATType.PORT_RESTRICTED: 0.05,
                NATType.SYMMETRIC: 0.1
            }[client.nat_type]
            
            # ネットワーク遅延を追加
            network_delay = random.uniform(0.005, 0.05)
            total_time = processing_time + network_delay
            
            yield self.env.timeout(total_time)
            
            self.total_requests += 1
            self.response_times.append(total_time)
            
            # 外部IPとポートを「発見」
            external_port = random.randint(10000, 65535)
            return f"203.0.113.{random.randint(1,254)}", external_port

class NATSimulator:
    """NAT 穴あけシミュレータ"""
    def __init__(self, env):
        self.env = env
        self.nat_table: Dict[str, Dict] = {}
        self.port_pool = set(range(10000, 65535))
        self.stats = {
            'hole_punches_attempted': 0,
            'hole_punches_successful': 0,
            'holes_active': 0,
            'port_exhaustion_events': 0
        }
    
    def attempt_hole_punch(self, client: NetworkClient, target_port: int) -> Tuple[bool, Optional[int]]:
        """NAT穴あけ試行"""
        self.stats['hole_punches_attempted'] += 1
        
        # NAT タイプ別成功率
        success_rates = {
            NATType.FULL_CONE: 0.95,
            NATType.RESTRICTED_CONE: 0.85,
            NATType.PORT_RESTRICTED: 0.65,
            NATType.SYMMETRIC: 0.25
        }
        
        # ポート枯渇チェック
        if len(self.port_pool) < 100:
            self.stats['port_exhaustion_events'] += 1
            return False, None
            
        # 成功判定
        success_rate = success_rates[client.nat_type]
        if random.random() < success_rate:
            # ポート割り当て
            allocated_port = self.port_pool.pop() if self.port_pool else None
            if allocated_port:
                self.nat_table[client.client_id] = {
                    'external_port': allocated_port,
                    'internal_port': target_port,
                    'created_time': self.env.now,
                    'nat_type': client.nat_type
                }
                self.stats['hole_punches_successful'] += 1
                self.stats['holes_active'] += 1
                client.active_holes.append(allocated_port)
                client.last_success_time = self.env.now
                return True, allocated_port
        
        client.failed_attempts += 1
        return False, None
    
    def close_hole(self, client_id: str, port: int):
        """穴あけクローズ（ポート解放）"""
        if client_id in self.nat_table:
            self.port_pool.add(port)
            del self.nat_table[client_id]
            self.stats['holes_active'] -= 1

class FirewallSimulator:
    """ファイアウォール制御シミュレータ"""
    def __init__(self, env, max_concurrent_rules=10000):
        self.env = env
        self.rule_processor = simpy.Resource(env, capacity=100)  # 並列ルール処理
        self.active_rules: Dict[Tuple[str, int], FirewallRule] = {}
        self.max_rules = max_concurrent_rules
        self.stats = {
            'rules_created': 0,
            'rules_expired': 0,
            'rule_creation_failures': 0,
            'cpu_utilization': []
        }
    
    def create_rule_process(self, src_ip: str, dst_port: int, duration: float, priority: str = "normal"):
        """ファイアウォールルール作成プロセス"""
        with self.rule_processor.request() as req:
            yield req
            
            # ルール作成処理時間（優先度による）
            processing_times = {
                "high": 0.001,    # 緊急
                "normal": 0.005,  # 通常
                "low": 0.01       # 低優先度
            }
            
            yield self.env.timeout(processing_times.get(priority, 0.005))
            
            # ルール容量チェック
            if len(self.active_rules) >= self.max_rules:
                self.stats['rule_creation_failures'] += 1
                return False
            
            # ルール作成
            rule_key = (src_ip, dst_port)
            rule = FirewallRule(
                src_ip=src_ip,
                dst_port=dst_port,
                created_time=self.env.now,
                expires_time=self.env.now + duration
            )
            
            self.active_rules[rule_key] = rule
            self.stats['rules_created'] += 1
            
            # 自動期限切れプロセス
            self.env.process(self._rule_expiration_process(rule_key, duration))
            
            return True
    
    def _rule_expiration_process(self, rule_key: Tuple[str, int], duration: float):
        """ルール自動削除プロセス"""
        yield self.env.timeout(duration)
        
        if rule_key in self.active_rules:
            del self.active_rules[rule_key]
            self.stats['rules_expired'] += 1

class ZeroTrustAuthenticator:
    """ゼロトラスト認証システム"""
    def __init__(self, env, auth_capacity=500):
        self.env = env
        self.auth_processor = simpy.Resource(env, capacity=auth_capacity)
        self.risk_engine = simpy.Resource(env, capacity=100)
        self.stats = {
            'auth_requests': 0,
            'auth_successes': 0,
            'risk_assessments': 0,
            'trust_escalations': 0
        }
    
    def authenticate_process(self, client: NetworkClient, requested_resource: str):
        """ゼロトラスト認証プロセス"""
        with self.auth_processor.request() as auth_req:
            yield auth_req
            
            self.stats['auth_requests'] += 1
            
            # 信頼レベル別認証時間
            auth_times = {
                TrustLevel.UNTRUSTED: random.uniform(2.0, 5.0),  # 初回認証
                TrustLevel.LOW: random.uniform(1.0, 2.0),        # 基本認証
                TrustLevel.MEDIUM: random.uniform(0.5, 1.0),     # デバイス認証済み
                TrustLevel.HIGH: random.uniform(0.1, 0.5),       # MFA済み
                TrustLevel.VERIFIED: random.uniform(0.05, 0.1)   # 完全認証済み
            }
            
            auth_time = auth_times[client.trust_level]
            yield self.env.timeout(auth_time)
            
            # リスク評価（並列処理）
            risk_assessment = self.env.process(self._risk_assessment_process(client, requested_resource))
            yield risk_assessment
            
            # 認証成功判定（信頼レベルに基づく）
            success_rates = {
                TrustLevel.UNTRUSTED: 0.7,   # 初回は70%
                TrustLevel.LOW: 0.85,
                TrustLevel.MEDIUM: 0.95,
                TrustLevel.HIGH: 0.98,
                TrustLevel.VERIFIED: 0.99
            }
            
            if random.random() < success_rates[client.trust_level]:
                self.stats['auth_successes'] += 1
                # 信頼レベル向上の可能性
                if random.random() < 0.3 and client.trust_level != TrustLevel.VERIFIED:
                    self._escalate_trust_level(client)
                return True
            
            return False
    
    def _risk_assessment_process(self, client: NetworkClient, resource: str):
        """リスク評価プロセス"""
        with self.risk_engine.request() as risk_req:
            yield risk_req
            
            # リスク評価時間（複雑性による）
            assessment_time = random.uniform(0.05, 0.2)
            yield self.env.timeout(assessment_time)
            
            self.stats['risk_assessments'] += 1
            
            # リスクスコア計算（簡易版）
            risk_factors = [
                client.failed_attempts * 0.1,   # 失敗回数
                (self.env.now - (client.last_success_time or 0)) * 0.001,  # 最終成功からの時間
                random.uniform(0, 0.2)  # ランダム要因
            ]
            
            risk_score = min(sum(risk_factors), 1.0)
            return risk_score
    
    def _escalate_trust_level(self, client: NetworkClient):
        """信頼レベル向上"""
        trust_levels = list(TrustLevel)
        current_index = trust_levels.index(client.trust_level)
        if current_index < len(trust_levels) - 1:
            client.trust_level = trust_levels[current_index + 1]
            self.stats['trust_escalations'] += 1

class HolePunchingSystem:
    """統合穴あけ制御システム"""
    def __init__(self, env):
        self.env = env
        self.stun_server = STUNServer(env)
        self.nat_simulator = NATSimulator(env)
        self.firewall = FirewallSimulator(env)
        self.zero_trust = ZeroTrustAuthenticator(env)
        
        # システム全体統計
        self.system_stats = {
            'total_sessions': 0,
            'successful_sessions': 0,
            'session_durations': [],
            'end_to_end_times': []
        }

def hole_punch_session_process(system: HolePunchingSystem, client: NetworkClient, target_resource: str, session_duration: float):
    """完全な穴あけセッションプロセス"""
    session_start = system.env.now
    system.system_stats['total_sessions'] += 1
    
    try:
        # Phase 1: ゼロトラスト認証
        auth_success = yield system.env.process(
            system.zero_trust.authenticate_process(client, target_resource)
        )
        
        if not auth_success:
            print(f"Time {system.env.now:.3f}: Client {client.client_id} - Auth failed")
            return False
        
        # Phase 2: STUN discovery
        external_ip, external_port = yield system.env.process(
            system.stun_server.process_stun_request(client)
        )
        
        # Phase 3: NAT 穴あけ試行
        target_port = random.randint(8000, 9000)
        hole_success, allocated_port = system.nat_simulator.attempt_hole_punch(client, target_port)
        
        if not hole_success:
            print(f"Time {system.env.now:.3f}: Client {client.client_id} - NAT hole punch failed")
            return False
        
        # Phase 4: ファイアウォールルール作成
        rule_success = yield system.env.process(
            system.firewall.create_rule_process(
                external_ip, allocated_port, session_duration, "normal"
            )
        )
        
        if not rule_success:
            print(f"Time {system.env.now:.3f}: Client {client.client_id} - Firewall rule creation failed")
            system.nat_simulator.close_hole(client.client_id, allocated_port)
            return False
        
        # セッション成功
        end_to_end_time = system.env.now - session_start
        system.system_stats['successful_sessions'] += 1
        system.system_stats['end_to_end_times'].append(end_to_end_time)
        
        print(f"Time {system.env.now:.3f}: Client {client.client_id} - Session established (E2E: {end_to_end_time:.3f}s, Port: {allocated_port})")
        
        # セッション維持
        yield system.env.timeout(session_duration)
        
        # クリーンアップ
        system.nat_simulator.close_hole(client.client_id, allocated_port)
        system.system_stats['session_durations'].append(session_duration)
        
        return True
        
    except Exception as e:
        print(f"Time {system.env.now:.3f}: Client {client.client_id} - Session error: {e}")
        return False

def generate_clients(num_clients: int) -> List[NetworkClient]:
    """クライアント群生成"""
    clients = []
    
    nat_distribution = {
        NATType.FULL_CONE: 0.15,      # 15%
        NATType.RESTRICTED_CONE: 0.35, # 35%  
        NATType.PORT_RESTRICTED: 0.35, # 35%
        NATType.SYMMETRIC: 0.15        # 15%
    }
    
    trust_distribution = {
        TrustLevel.UNTRUSTED: 0.4,     # 40%
        TrustLevel.LOW: 0.3,           # 30%
        TrustLevel.MEDIUM: 0.2,        # 20%
        TrustLevel.HIGH: 0.08,         # 8%
        TrustLevel.VERIFIED: 0.02      # 2%
    }
    
    for i in range(num_clients):
        # NAT タイプをランダム選択
        rand_val = random.random()
        cumulative = 0
        selected_nat = NATType.FULL_CONE
        
        for nat_type, probability in nat_distribution.items():
            cumulative += probability
            if rand_val <= cumulative:
                selected_nat = nat_type
                break
        
        # 信頼レベルをランダム選択
        rand_val = random.random()
        cumulative = 0
        selected_trust = TrustLevel.UNTRUSTED
        
        for trust_level, probability in trust_distribution.items():
            cumulative += probability
            if rand_val <= cumulative:
                selected_trust = trust_level
                break
        
        client = NetworkClient(
            client_id=f"client_{i:04d}",
            internal_ip=f"192.168.1.{i % 254 + 1}",
            nat_type=selected_nat,
            trust_level=selected_trust
        )
        clients.append(client)
    
    return clients

def client_generator(env, system: HolePunchingSystem, clients: List[NetworkClient], arrival_rate: float, sim_time: float):
    """クライアントリクエスト生成器"""
    client_index = 0
    
    while env.now < sim_time and client_index < len(clients):
        # 次のリクエストまでの間隔
        inter_arrival = random.expovariate(arrival_rate)
        yield env.timeout(inter_arrival)
        
        if env.now >= sim_time:
            break
        
        # クライアント選択
        client = clients[client_index % len(clients)]
        client_index += 1
        
        # セッション時間（用途による）
        session_duration = random.uniform(30, 300)  # 30秒～5分
        
        # リソース選択
        target_resources = ["webapp", "api", "database", "fileserver", "analytics"]
        target_resource = random.choice(target_resources)
        
        # 穴あけセッション開始
        env.process(hole_punch_session_process(system, client, target_resource, session_duration))

def run_hole_punching_simulation(arrival_rate: float = 2.0, sim_time: float = 300, num_clients: int = 500):
    """穴あけ制御シミュレーション実行"""
    
    print(f"\n{'='*80}")
    print(f"IP&Port Hole Punching Control Simulation")
    print(f"Arrival Rate: {arrival_rate} req/s, Simulation Time: {sim_time}s, Clients: {num_clients}")
    print(f"{'='*80}")
    
    # シミュレーション環境初期化
    env = simpy.Environment()
    system = HolePunchingSystem(env)
    clients = generate_clients(num_clients)
    
    # クライアント分布表示
    nat_counts = defaultdict(int)
    trust_counts = defaultdict(int)
    for client in clients:
        nat_counts[client.nat_type] += 1
        trust_counts[client.trust_level] += 1
    
    print(f"\nClient Distribution:")
    print(f"NAT Types: {dict(nat_counts)}")
    print(f"Trust Levels: {dict(trust_counts)}")
    
    # クライアント生成プロセス開始
    env.process(client_generator(env, system, clients, arrival_rate, sim_time))
    
    # シミュレーション実行
    print(f"\nRunning Simulation...")
    env.run(until=sim_time)
    
    # 結果分析
    print_simulation_results(system, clients)
    
    # データエクスポート
    export_data = export_hole_punching_data(system, clients, arrival_rate, sim_time)
    filename = f"hole_punching_metrics_{arrival_rate:.1f}rps_{sim_time:.0f}s.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to {filename}")
    
    return system, clients

def print_simulation_results(system: HolePunchingSystem, clients: List[NetworkClient]):
    """シミュレーション結果表示"""
    
    print(f"\nOverall System Results:")
    total_sessions = system.system_stats['total_sessions']
    successful_sessions = system.system_stats['successful_sessions']
    
    if total_sessions > 0:
        success_rate = (successful_sessions / total_sessions) * 100
        print(f"  Total Sessions: {total_sessions}")
        print(f"  Successful Sessions: {successful_sessions}")
        print(f"  Success Rate: {success_rate:.1f}%")
        
        if system.system_stats['end_to_end_times']:
            e2e_times = system.system_stats['end_to_end_times']
            print(f"  Avg E2E Time: {statistics.mean(e2e_times):.3f}s")
            print(f"  P95 E2E Time: {sorted(e2e_times)[int(len(e2e_times) * 0.95)]:.3f}s")
    
    print(f"\nSTUN Server:")
    print(f"  Requests Processed: {system.stun_server.total_requests}")
    if system.stun_server.response_times:
        print(f"  Avg Response Time: {statistics.mean(system.stun_server.response_times):.3f}s")
    
    print(f"\nNAT Statistics:")
    nat_stats = system.nat_simulator.stats
    print(f"  Hole Punch Attempts: {nat_stats['hole_punches_attempted']}")
    print(f"  Hole Punch Successes: {nat_stats['hole_punches_successful']}")
    if nat_stats['hole_punches_attempted'] > 0:
        nat_success_rate = (nat_stats['hole_punches_successful'] / nat_stats['hole_punches_attempted']) * 100
        print(f"  NAT Success Rate: {nat_success_rate:.1f}%")
    print(f"  Active Holes: {nat_stats['holes_active']}")
    print(f"  Port Exhaustion Events: {nat_stats['port_exhaustion_events']}")
    
    print(f"\nFirewall:")
    fw_stats = system.firewall.stats
    print(f"  Rules Created: {fw_stats['rules_created']}")
    print(f"  Rules Expired: {fw_stats['rules_expired']}")
    print(f"  Creation Failures: {fw_stats['rule_creation_failures']}")
    print(f"  Active Rules: {len(system.firewall.active_rules)}")
    
    print(f"\nZero Trust Authentication:")
    zt_stats = system.zero_trust.stats
    print(f"  Auth Requests: {zt_stats['auth_requests']}")
    print(f"  Auth Successes: {zt_stats['auth_successes']}")
    if zt_stats['auth_requests'] > 0:
        auth_success_rate = (zt_stats['auth_successes'] / zt_stats['auth_requests']) * 100
        print(f"  Auth Success Rate: {auth_success_rate:.1f}%")
    print(f"  Risk Assessments: {zt_stats['risk_assessments']}")
    print(f"  Trust Escalations: {zt_stats['trust_escalations']}")

def export_hole_punching_data(system: HolePunchingSystem, clients: List[NetworkClient], arrival_rate: float, sim_time: float) -> dict:
    """シミュレーション結果エクスポート"""
    
    return {
        "simulation_config": {
            "arrival_rate": arrival_rate,
            "simulation_time": sim_time,
            "num_clients": len(clients),
            "timestamp": datetime.now().isoformat()
        },
        "system_performance": {
            "total_sessions": system.system_stats['total_sessions'],
            "successful_sessions": system.system_stats['successful_sessions'],
            "success_rate_percent": (system.system_stats['successful_sessions'] / max(system.system_stats['total_sessions'], 1)) * 100,
            "avg_e2e_time": statistics.mean(system.system_stats['end_to_end_times']) if system.system_stats['end_to_end_times'] else 0,
            "p95_e2e_time": sorted(system.system_stats['end_to_end_times'])[int(len(system.system_stats['end_to_end_times']) * 0.95)] if system.system_stats['end_to_end_times'] else 0
        },
        "component_stats": {
            "stun_server": {
                "total_requests": system.stun_server.total_requests,
                "avg_response_time": statistics.mean(system.stun_server.response_times) if system.stun_server.response_times else 0
            },
            "nat_simulator": system.nat_simulator.stats,
            "firewall": system.firewall.stats,
            "zero_trust": system.zero_trust.stats
        },
        "client_distribution": {
            "nat_types": {nat_type.value: sum(1 for c in clients if c.nat_type == nat_type) for nat_type in NATType},
            "trust_levels": {trust_level.value: sum(1 for c in clients if c.trust_level == trust_level) for trust_level in TrustLevel}
        }
    }

if __name__ == "__main__":
    print("SimPy IP&Port Hole Punching Control Simulation")
    print("=" * 80)
    
    # 複数シナリオでのテスト実行
    scenarios = [
        {"arrival_rate": 1.0, "sim_time": 180, "num_clients": 200},
        {"arrival_rate": 2.0, "sim_time": 300, "num_clients": 500}, 
        {"arrival_rate": 5.0, "sim_time": 180, "num_clients": 800}
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\nScenario {i}/3")
        run_hole_punching_simulation(**scenario)
    
    print(f"\n{'='*80}")
    print("Hole Punching Control Simulation Complete")
    print("Please check NAT types, trust levels, and security control performance characteristics")
    print("=" * 80)