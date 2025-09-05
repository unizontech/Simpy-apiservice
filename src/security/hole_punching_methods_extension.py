#!/usr/bin/env python3
"""
穴あけ手法の拡張デザイン - 複数手法の動的切り替え

既存のnat_hole_punching_simulation.pyに追加可能な拡張モジュール
"""

from enum import Enum
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
import random
import simpy

class HolePunchingMethod(Enum):
    """穴あけ手法の種類"""
    # 基本的な手法
    STUN_BASED = "stun_based"                    # 現在実装済み
    UPNP_IGD = "upnp_igd"                        # UPnP Internet Gateway Device
    
    # 高度な手法  
    STUN_TURN_ICE = "stun_turn_ice"              # WebRTC標準スタック
    TCP_HOLE_PUNCHING = "tcp_hole_punching"      # TCP穴あけ
    UDP_HOLE_PUNCHING = "udp_hole_punching"      # UDP穴あけ
    
    # リレー・トンネル手法
    RELAY_SERVER = "relay_server"                # リレーサーバー経由
    VPN_TUNNEL = "vpn_tunnel"                    # VPNトンネル
    SSH_TUNNEL = "ssh_tunnel"                    # SSHトンネル
    
    # 次世代手法
    WEBRTC_DATACHANNEL = "webrtc_datachannel"    # WebRTCデータチャネル
    QUIC_CONNECTION = "quic_connection"          # QUIC over UDP
    IPV6_DIRECT = "ipv6_direct"                  # IPv6直接接続
    
    # ハイブリッド手法
    MULTI_PATH = "multi_path"                    # 複数経路同時
    FALLBACK_CASCADE = "fallback_cascade"        # 段階的フォールバック

class ConnectionQuality(Enum):
    """接続品質レベル"""
    DIRECT = "direct"           # 直接接続 - 最高品質
    NAT_TRAVERSAL = "nat_traversal"  # NAT越え - 高品質
    RELAY = "relay"            # リレー経由 - 中品質  
    TUNNEL = "tunnel"          # トンネル経由 - 低品質
    FAILED = "failed"          # 失敗 - 品質なし

@dataclass
class HolePunchingMethodSpec:
    """穴あけ手法の仕様"""
    method: HolePunchingMethod
    success_rates: Dict[str, float]      # NAT種別ごとの成功率
    setup_time_range: Tuple[float, float]  # セットアップ時間範囲(秒)
    quality: ConnectionQuality
    bandwidth_efficiency: float          # 帯域効率 (0.0-1.0)
    cpu_cost: float                     # CPU負荷コスト
    infrastructure_cost: float          # インフラコスト
    security_level: float              # セキュリティレベル (0.0-1.0)
    reliability: float                 # 信頼性 (0.0-1.0)

class HolePunchingMethodRegistry:
    """穴あけ手法のレジストリ"""
    
    def __init__(self):
        self.methods = self._initialize_methods()
    
    def _initialize_methods(self) -> Dict[HolePunchingMethod, HolePunchingMethodSpec]:
        """手法仕様の初期化"""
        return {
            # === 基本手法 ===
            HolePunchingMethod.STUN_BASED: HolePunchingMethodSpec(
                method=HolePunchingMethod.STUN_BASED,
                success_rates={
                    "full_cone": 0.95,
                    "restricted_cone": 0.85, 
                    "port_restricted": 0.65,
                    "symmetric": 0.25
                },
                setup_time_range=(0.1, 0.5),
                quality=ConnectionQuality.NAT_TRAVERSAL,
                bandwidth_efficiency=0.95,
                cpu_cost=0.1,
                infrastructure_cost=0.2,
                security_level=0.7,
                reliability=0.8
            ),
            
            HolePunchingMethod.UPNP_IGD: HolePunchingMethodSpec(
                method=HolePunchingMethod.UPNP_IGD,
                success_rates={
                    "full_cone": 0.90,      # UPnP対応ルーター
                    "restricted_cone": 0.85,
                    "port_restricted": 0.80,
                    "symmetric": 0.15       # 多くは無効
                },
                setup_time_range=(0.05, 0.2),
                quality=ConnectionQuality.DIRECT,
                bandwidth_efficiency=1.0,
                cpu_cost=0.05,
                infrastructure_cost=0.0,  # クライアントのみ
                security_level=0.6,       # ローカルネットワーク依存
                reliability=0.7
            ),
            
            # === 高度手法 ===
            HolePunchingMethod.STUN_TURN_ICE: HolePunchingMethodSpec(
                method=HolePunchingMethod.STUN_TURN_ICE,
                success_rates={
                    "full_cone": 0.98,
                    "restricted_cone": 0.95,
                    "port_restricted": 0.90,
                    "symmetric": 0.80       # TURN経由でカバー
                },
                setup_time_range=(0.3, 1.2),
                quality=ConnectionQuality.NAT_TRAVERSAL,
                bandwidth_efficiency=0.90,
                cpu_cost=0.3,
                infrastructure_cost=0.8,  # TURNサーバー必要
                security_level=0.85,
                reliability=0.95
            ),
            
            HolePunchingMethod.TCP_HOLE_PUNCHING: HolePunchingMethodSpec(
                method=HolePunchingMethod.TCP_HOLE_PUNCHING,
                success_rates={
                    "full_cone": 0.85,
                    "restricted_cone": 0.70,
                    "port_restricted": 0.50,
                    "symmetric": 0.15       # TCP穴あけは困難
                },
                setup_time_range=(0.2, 0.8),
                quality=ConnectionQuality.NAT_TRAVERSAL,
                bandwidth_efficiency=0.85,  # TCPオーバーヘッド
                cpu_cost=0.2,
                infrastructure_cost=0.1,
                security_level=0.8,        # TCP信頼性
                reliability=0.9
            ),
            
            # === リレー手法 ===
            HolePunchingMethod.RELAY_SERVER: HolePunchingMethodSpec(
                method=HolePunchingMethod.RELAY_SERVER,
                success_rates={
                    "full_cone": 0.99,      # ほぼ確実
                    "restricted_cone": 0.99,
                    "port_restricted": 0.99,
                    "symmetric": 0.99
                },
                setup_time_range=(0.05, 0.15),
                quality=ConnectionQuality.RELAY,
                bandwidth_efficiency=0.70,  # リレーオーバーヘッド
                cpu_cost=0.1,
                infrastructure_cost=1.0,   # 専用サーバー必要
                security_level=0.6,       # 中継点のリスク
                reliability=0.95
            ),
            
            HolePunchingMethod.VPN_TUNNEL: HolePunchingMethodSpec(
                method=HolePunchingMethod.VPN_TUNNEL,
                success_rates={
                    "full_cone": 0.95,
                    "restricted_cone": 0.95,
                    "port_restricted": 0.95,
                    "symmetric": 0.95
                },
                setup_time_range=(1.0, 3.0),  # VPN接続時間
                quality=ConnectionQuality.TUNNEL,
                bandwidth_efficiency=0.75,
                cpu_cost=0.4,              # 暗号化コスト
                infrastructure_cost=0.6,
                security_level=0.95,       # 最高セキュリティ
                reliability=0.90
            ),
            
            # === 次世代手法 ===
            HolePunchingMethod.WEBRTC_DATACHANNEL: HolePunchingMethodSpec(
                method=HolePunchingMethod.WEBRTC_DATACHANNEL,
                success_rates={
                    "full_cone": 0.90,
                    "restricted_cone": 0.85,
                    "port_restricted": 0.75,
                    "symmetric": 0.60       # STUNフォールバック
                },
                setup_time_range=(0.5, 1.5),
                quality=ConnectionQuality.NAT_TRAVERSAL,
                bandwidth_efficiency=0.88,
                cpu_cost=0.25,
                infrastructure_cost=0.3,
                security_level=0.85,      # DTLS暗号化
                reliability=0.85
            ),
            
            HolePunchingMethod.IPV6_DIRECT: HolePunchingMethodSpec(
                method=HolePunchingMethod.IPV6_DIRECT,
                success_rates={
                    "full_cone": 0.98,      # IPv6では直接接続
                    "restricted_cone": 0.98,
                    "port_restricted": 0.98,
                    "symmetric": 0.98
                },
                setup_time_range=(0.02, 0.1),
                quality=ConnectionQuality.DIRECT,
                bandwidth_efficiency=1.0,
                cpu_cost=0.02,
                infrastructure_cost=0.0,
                security_level=0.7,
                reliability=0.85,         # IPv6普及率依存
            ),
            
            # === ハイブリッド手法 ===
            HolePunchingMethod.FALLBACK_CASCADE: HolePunchingMethodSpec(
                method=HolePunchingMethod.FALLBACK_CASCADE,
                success_rates={
                    "full_cone": 0.99,      # 段階的に試行
                    "restricted_cone": 0.98,
                    "port_restricted": 0.95,
                    "symmetric": 0.90
                },
                setup_time_range=(0.1, 2.5),  # 最大フォールバック時間
                quality=ConnectionQuality.NAT_TRAVERSAL,  # 最良結果
                bandwidth_efficiency=0.85,   # 平均効率
                cpu_cost=0.3,               # 複数試行コスト
                infrastructure_cost=0.4,     # 複数インフラ
                security_level=0.8,         # 最良手法採用
                reliability=0.95
            )
        }
    
    def get_method_spec(self, method: HolePunchingMethod) -> HolePunchingMethodSpec:
        """手法仕様を取得"""
        return self.methods[method]
    
    def get_available_methods(self) -> List[HolePunchingMethod]:
        """利用可能な手法一覧"""
        return list(self.methods.keys())
    
    def select_optimal_method(self, 
                            nat_type: str, 
                            priority: str = "success_rate",
                            constraints: Dict = None) -> HolePunchingMethod:
        """最適手法を選択"""
        
        constraints = constraints or {}
        max_cost = constraints.get("max_infrastructure_cost", float('inf'))
        min_security = constraints.get("min_security_level", 0.0)
        max_setup_time = constraints.get("max_setup_time", float('inf'))
        
        best_method = None
        best_score = -1
        
        for method, spec in self.methods.items():
            # 制約チェック
            if (spec.infrastructure_cost > max_cost or 
                spec.security_level < min_security or 
                spec.setup_time_range[1] > max_setup_time):
                continue
            
            # 優先度別スコア計算
            if priority == "success_rate":
                score = spec.success_rates.get(nat_type, 0)
            elif priority == "speed":
                score = 1.0 - (spec.setup_time_range[0] / 10.0)  # 正規化
            elif priority == "cost":
                score = 1.0 - (spec.infrastructure_cost / 2.0)    # 正規化
            elif priority == "security":
                score = spec.security_level
            elif priority == "quality":
                quality_scores = {
                    ConnectionQuality.DIRECT: 1.0,
                    ConnectionQuality.NAT_TRAVERSAL: 0.8,
                    ConnectionQuality.RELAY: 0.6,
                    ConnectionQuality.TUNNEL: 0.4
                }
                score = quality_scores.get(spec.quality, 0)
            else:
                # 総合スコア
                score = (spec.success_rates.get(nat_type, 0) * 0.4 +
                        spec.reliability * 0.3 +
                        spec.security_level * 0.2 +
                        (1.0 - spec.infrastructure_cost / 2.0) * 0.1)
            
            if score > best_score:
                best_score = score
                best_method = method
        
        return best_method or HolePunchingMethod.STUN_BASED

class AdaptiveHolePunchingSystem:
    """適応的穴あけシステム"""
    
    def __init__(self, env):
        self.env = env
        self.registry = HolePunchingMethodRegistry()
        self.success_history = {}  # 手法別成功履歴
        self.method_stats = {}     # 手法別統計
        
        # 現在の手法選択戦略
        self.selection_strategy = "adaptive"  # adaptive, static, round_robin
        self.current_method = HolePunchingMethod.STUN_BASED
    
    def attempt_connection(self, client, target, method: HolePunchingMethod = None):
        """接続試行（手法指定可能）"""
        
        if method is None:
            method = self.select_method_for_client(client)
        
        spec = self.registry.get_method_spec(method)
        
        # セットアップ時間シミュレート
        setup_time = random.uniform(*spec.setup_time_range)
        yield self.env.timeout(setup_time)
        
        # 成功判定
        nat_type = client.nat_type.value
        success_rate = spec.success_rates.get(nat_type, 0.5)
        success = random.random() < success_rate
        
        # 統計更新
        self._update_method_stats(method, success, setup_time, spec)
        
        return {
            "success": success,
            "method": method,
            "setup_time": setup_time,
            "quality": spec.quality,
            "bandwidth_efficiency": spec.bandwidth_efficiency
        }
    
    def select_method_for_client(self, client) -> HolePunchingMethod:
        """クライアントに最適な手法を選択"""
        
        if self.selection_strategy == "static":
            return self.current_method
        
        elif self.selection_strategy == "adaptive":
            # 過去の成功率を考慮
            nat_type = client.nat_type.value
            trust_level = client.trust_level
            
            # 信頼レベル別の制約
            constraints = {}
            if trust_level.value in ["high", "verified"]:
                constraints["min_security_level"] = 0.8
            if client.failed_attempts > 3:
                constraints["max_setup_time"] = 0.5  # 高速手法優先
            
            return self.registry.select_optimal_method(
                nat_type, 
                priority="balanced",
                constraints=constraints
            )
        
        elif self.selection_strategy == "round_robin":
            methods = self.registry.get_available_methods()
            index = hash(client.client_id) % len(methods)
            return methods[index]
        
        return HolePunchingMethod.STUN_BASED
    
    def _update_method_stats(self, method: HolePunchingMethod, success: bool, setup_time: float, spec):
        """手法統計を更新"""
        if method not in self.method_stats:
            self.method_stats[method] = {
                "attempts": 0,
                "successes": 0,
                "total_setup_time": 0,
                "avg_setup_time": 0,
                "success_rate": 0
            }
        
        stats = self.method_stats[method]
        stats["attempts"] += 1
        if success:
            stats["successes"] += 1
        stats["total_setup_time"] += setup_time
        stats["avg_setup_time"] = stats["total_setup_time"] / stats["attempts"]
        stats["success_rate"] = stats["successes"] / stats["attempts"]
    
    def get_method_performance_report(self) -> Dict:
        """手法別性能レポート"""
        return {
            "method_stats": self.method_stats,
            "registry_specs": {method.value: {
                "success_rates": spec.success_rates,
                "quality": spec.quality.value,
                "infrastructure_cost": spec.infrastructure_cost,
                "security_level": spec.security_level
            } for method, spec in self.registry.methods.items()},
            "selection_strategy": self.selection_strategy
        }

# === 使用例 ===
def demonstrate_method_switching():
    """手法切り替えのデモンストレーション"""
    
    # シミュレーション環境
    env = simpy.Environment()
    adaptive_system = AdaptiveHolePunchingSystem(env)
    
    # 異なる戦略でのテスト
    strategies = ["static", "adaptive", "round_robin"]
    
    for strategy in strategies:
        print(f"\n=== Strategy: {strategy} ===")
        adaptive_system.selection_strategy = strategy
        
        # 各手法での結果比較
        for method in [HolePunchingMethod.STUN_BASED, 
                      HolePunchingMethod.UPNP_IGD,
                      HolePunchingMethod.WEBRTC_DATACHANNEL]:
            print(f"\nMethod: {method.value}")
            spec = adaptive_system.registry.get_method_spec(method)
            print(f"  Success rates: {spec.success_rates}")
            print(f"  Setup time: {spec.setup_time_range[0]:.3f}-{spec.setup_time_range[1]:.3f}s")
            print(f"  Quality: {spec.quality.value}")
            print(f"  Infrastructure cost: {spec.infrastructure_cost:.2f}")
            print(f"  Security level: {spec.security_level:.2f}")

if __name__ == "__main__":
    demonstrate_method_switching()