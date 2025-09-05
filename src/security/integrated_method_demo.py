#!/usr/bin/env python3
"""
既存シミュレーションとの統合デモ
- 複数穴あけ手法の動的切り替え
- パフォーマンス比較分析
- 最適手法の自動選択
"""

import sys
sys.path.append('.')

# 既存のシミュレーションをインポート
from src.security.nat_hole_punching_simulation import (
    HolePunchingSystem, NetworkClient, NATType, TrustLevel,
    run_hole_punching_simulation, generate_clients
)

# 新しい拡張をインポート  
from src.security.hole_punching_methods_extension import (
    AdaptiveHolePunchingSystem, HolePunchingMethod, 
    HolePunchingMethodRegistry, ConnectionQuality
)

import simpy
import json
from collections import defaultdict

class EnhancedHolePunchingSystem(HolePunchingSystem):
    """拡張された穴あけシステム - 複数手法対応"""
    
    def __init__(self, env):
        super().__init__(env)
        self.adaptive_system = AdaptiveHolePunchingSystem(env)
        self.method_comparison_stats = defaultdict(lambda: {
            'attempts': 0, 'successes': 0, 'total_time': 0, 'costs': 0
        })
        
        # 手法切り替え設定
        self.method_switching_enabled = True
        self.fallback_enabled = True
        
    def enhanced_hole_punch_attempt(self, client: NetworkClient, target_port: int, 
                                  preferred_method: HolePunchingMethod = None):
        """拡張された穴あけ試行"""
        
        if not preferred_method:
            preferred_method = self.adaptive_system.select_method_for_client(client)
        
        # 第一選択手法で試行
        result = yield self.env.process(
            self.adaptive_system.attempt_connection(client, target_port, preferred_method)
        )
        
        self._record_method_result(preferred_method, result)
        
        # 失敗時のフォールバック処理
        if not result["success"] and self.fallback_enabled:
            result = yield self.env.process(
                self._try_fallback_methods(client, target_port, preferred_method)
            )
        
        return result
    
    def _try_fallback_methods(self, client: NetworkClient, target_port: int, 
                            failed_method: HolePunchingMethod):
        """フォールバック手法の試行"""
        
        # フォールバック優先順位
        fallback_priority = [
            HolePunchingMethod.STUN_TURN_ICE,    # 高成功率
            HolePunchingMethod.RELAY_SERVER,     # 確実だが低品質
            HolePunchingMethod.VPN_TUNNEL        # 最後の手段
        ]
        
        for method in fallback_priority:
            if method == failed_method:
                continue
                
            result = yield self.env.process(
                self.adaptive_system.attempt_connection(client, target_port, method)
            )
            
            self._record_method_result(method, result, is_fallback=True)
            
            if result["success"]:
                return result
        
        # すべて失敗
        return {"success": False, "method": None, "setup_time": 0}
    
    def _record_method_result(self, method: HolePunchingMethod, result: dict, is_fallback=False):
        """手法別結果を記録"""
        stats = self.method_comparison_stats[method.value]
        stats['attempts'] += 1
        
        if result["success"]:
            stats['successes'] += 1
        
        stats['total_time'] += result.get("setup_time", 0)
        
        # コスト計算（インフラ + CPU）
        spec = self.adaptive_system.registry.get_method_spec(method)
        stats['costs'] += spec.infrastructure_cost + spec.cpu_cost
        
        if is_fallback:
            stats['fallback_attempts'] = stats.get('fallback_attempts', 0) + 1

def run_method_comparison_simulation():
    """複数手法の比較シミュレーション"""
    
    print("=" * 80)
    print("Enhanced Hole Punching Methods Comparison Simulation")
    print("=" * 80)
    
    # シミュレーション設定
    env = simpy.Environment() 
    enhanced_system = EnhancedHolePunchingSystem(env)
    clients = generate_clients(100)
    
    # 各手法でのテスト実行
    test_methods = [
        HolePunchingMethod.STUN_BASED,
        HolePunchingMethod.UPNP_IGD,
        HolePunchingMethod.STUN_TURN_ICE,
        HolePunchingMethod.WEBRTC_DATACHANNEL,
        HolePunchingMethod.RELAY_SERVER,
        HolePunchingMethod.FALLBACK_CASCADE
    ]
    
    print(f"\nTesting {len(test_methods)} methods with {len(clients)} clients")
    
    def test_method_process(method: HolePunchingMethod):
        """特定手法のテストプロセス"""
        for i, client in enumerate(clients[:20]):  # 20クライアントでテスト
            target_port = 8000 + i
            result = yield env.process(
                enhanced_system.enhanced_hole_punch_attempt(
                    client, target_port, method
                )
            )
            
            if result["success"]:
                print(f"Time {env.now:.2f}: {method.value} - Client {client.client_id} success "
                      f"({result['setup_time']:.3f}s)")
    
    # 各手法を並列実行
    for method in test_methods:
        env.process(test_method_process(method))
    
    # シミュレーション実行
    env.run(until=60)  # 60秒シミュレーション
    
    # 結果分析
    analyze_method_performance(enhanced_system)
    
    return enhanced_system

def analyze_method_performance(system: EnhancedHolePunchingSystem):
    """手法別性能分析"""
    
    print(f"\n{'='*80}")
    print("METHOD PERFORMANCE ANALYSIS")
    print(f"{'='*80}")
    
    print(f"{'Method':<25} | {'Attempts':>8} | {'Success':>7} | {'Rate':>6} | {'Avg Time':>9} | {'Total Cost':>10}")
    print("-" * 85)
    
    for method_name, stats in system.method_comparison_stats.items():
        attempts = stats['attempts']
        successes = stats['successes'] 
        success_rate = (successes / attempts * 100) if attempts > 0 else 0
        avg_time = (stats['total_time'] / attempts) if attempts > 0 else 0
        total_cost = stats['costs']
        
        print(f"{method_name:<25} | {attempts:>8} | {successes:>7} | {success_rate:>5.1f}% | "
              f"{avg_time:>8.3f}s | {total_cost:>9.2f}")
    
    # 推奨手法
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}")
    
    # 最高成功率
    best_success_rate = max(
        [(name, stats['successes'] / max(stats['attempts'], 1)) 
         for name, stats in system.method_comparison_stats.items()],
        key=lambda x: x[1]
    )
    print(f"Best Success Rate: {best_success_rate[0]} ({best_success_rate[1]*100:.1f}%)")
    
    # 最速手法
    fastest_method = min(
        [(name, stats['total_time'] / max(stats['attempts'], 1)) 
         for name, stats in system.method_comparison_stats.items()],
        key=lambda x: x[1]
    )
    print(f"Fastest Method: {fastest_method[0]} ({fastest_method[1]:.3f}s avg)")
    
    # 最低コスト
    cheapest_method = min(
        [(name, stats['costs'] / max(stats['attempts'], 1)) 
         for name, stats in system.method_comparison_stats.items()],
        key=lambda x: x[1]
    )
    print(f"Most Cost-Effective: {cheapest_method[0]} (cost: {cheapest_method[1]:.3f})")

def demonstrate_adaptive_selection():
    """適応的手法選択のデモンストレーション"""
    
    print(f"\n{'='*80}")
    print("ADAPTIVE METHOD SELECTION DEMONSTRATION")  
    print(f"{'='*80}")
    
    registry = HolePunchingMethodRegistry()
    
    # 異なるNAT環境での最適手法
    nat_types = ["full_cone", "restricted_cone", "port_restricted", "symmetric"]
    priorities = ["success_rate", "speed", "cost", "security"]
    
    for nat_type in nat_types:
        print(f"\nNAT Type: {nat_type.upper()}")
        print("-" * 40)
        
        for priority in priorities:
            optimal_method = registry.select_optimal_method(nat_type, priority)
            spec = registry.get_method_spec(optimal_method)
            success_rate = spec.success_rates.get(nat_type, 0) * 100
            
            print(f"  {priority:<12}: {optimal_method.value:<25} ({success_rate:>5.1f}% success)")

def export_method_comparison_results(system: EnhancedHolePunchingSystem):
    """手法比較結果のエクスポート"""
    
    # 適応システムの性能レポート
    performance_report = system.adaptive_system.get_method_performance_report()
    
    # 手法比較統計
    comparison_data = {
        "method_comparison_stats": dict(system.method_comparison_stats),
        "adaptive_system_report": performance_report,
        "simulation_config": {
            "method_switching_enabled": system.method_switching_enabled,
            "fallback_enabled": system.fallback_enabled,
            "total_methods_tested": len(system.method_comparison_stats)
        }
    }
    
    # JSON出力
    filename = "hole_punching_methods_comparison.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nMethod comparison results exported to {filename}")

if __name__ == "__main__":
    print("Multi-Method Hole Punching Simulation")
    
    # メイン比較シミュレーション
    enhanced_system = run_method_comparison_simulation()
    
    # 適応的選択のデモ
    demonstrate_adaptive_selection()
    
    # 結果エクスポート
    export_method_comparison_results(enhanced_system)
    
    print(f"\n{'='*80}")
    print("Multi-Method Simulation Complete")
    print("Check JSON export for detailed performance comparison")
    print(f"{'='*80}")