import simpy
import random
import statistics
import json
from collections import defaultdict
from datetime import datetime

class Server:
    def __init__(self, env, name, threads=4, ram_gb=32, disk_q=16, net_mbps=1000):
        self.env = env
        self.name = name
        self.cpu = simpy.PreemptiveResource(env, capacity=threads)
        self.ram = simpy.Container(env, capacity=ram_gb, init=ram_gb)
        self.disk = simpy.Resource(env, capacity=disk_q)
        self.net_mbps = net_mbps
        
        # メトリクス
        self.total_requests = 0
        self.cpu_time = 0
        self.ram_usage = []
        self.response_times = []
        
        # 毎秒メトリクス
        self.per_second_metrics = defaultdict(lambda: {
            'cpu_usage': 0.0,
            'ram_used': 0.0,
            'disk_queue': 0,
            'active_requests': 0,
            'requests_started': 0,
            'requests_completed': 0
        })
    
    def process_request(self, cpu_ms=50, ram_gb=1, disk_mb=10, net_mb=5):
        start_time = self.env.now
        start_second = int(start_time)
        
        # リクエスト開始を記録
        self.per_second_metrics[start_second]['requests_started'] += 1
        self.per_second_metrics[start_second]['active_requests'] += 1
        
        # メモリ確保
        yield self.ram.get(ram_gb)
        
        try:
            # CPU処理
            with self.cpu.request() as req:
                yield req
                cpu_time = cpu_ms / 1000.0  # ms to seconds
                yield self.env.timeout(cpu_time)
                self.cpu_time += cpu_time
                
                # CPU使用量を記録
                current_second = int(self.env.now)
                self.per_second_metrics[current_second]['cpu_usage'] += cpu_time
            
            # Disk I/O（必要な場合）
            if disk_mb > 0:
                with self.disk.request() as dreq:
                    yield dreq
                    # Disk待機中はキュー長を記録
                    queue_second = int(self.env.now)
                    self.per_second_metrics[queue_second]['disk_queue'] = len(self.disk.queue)
                    yield self.env.timeout(disk_mb / 500)  # 500MB/s assumed
            
            # Network処理時間
            if net_mb > 0:
                yield self.env.timeout(net_mb / (self.net_mbps / 8))
                
        finally:
            # メモリ解放
            yield self.ram.put(ram_gb)
            
        # リクエスト完了を記録
        end_time = self.env.now
        end_second = int(end_time)
        self.per_second_metrics[end_second]['requests_completed'] += 1
        self.per_second_metrics[end_second]['active_requests'] -= 1
        self.per_second_metrics[end_second]['ram_used'] = self.ram.capacity - self.ram.level
        
        # メトリクス記録
        self.total_requests += 1
        self.response_times.append(end_time - start_time)
        self.ram_usage.append(self.ram.level)

class MicroserviceSystem:
    def __init__(self, env):
        self.env = env
        # サーバー定義（threads: 論理プロセッサ数）
        self.nginx = Server(env, "Nginx", threads=8, ram_gb=16, net_mbps=40000)
        self.app1 = Server(env, "APP1", threads=16, ram_gb=64)
        self.auth = Server(env, "Auth", threads=4, ram_gb=32)
        self.policy = Server(env, "Policy", threads=8, ram_gb=32)
        self.service = Server(env, "Service", threads=16, ram_gb=64)
        self.db = Server(env, "DB", threads=32, ram_gb=128, disk_q=64)
        self.logger = Server(env, "Logger", threads=4, ram_gb=16)
        self.s3 = Server(env, "S3", threads=4, ram_gb=32, disk_q=128)
        self.servicehub = Server(env, "ServiceHub", threads=16, ram_gb=64)
        self.app2 = Server(env, "APP2", threads=16, ram_gb=64)
        
        # 全体メトリクス
        self.total_requests = 0
        self.completed_requests = 0
        self.end_to_end_times = []

def service_with_db_flow(system):
    """Service→DB依存処理"""
    # Service処理
    yield system.env.process(system.service.process_request(cpu_ms=80, ram_gb=2))
    
    # 30%の確率でDB必要
    if random.random() < 0.3:
        yield system.env.process(system.db.process_request(
            cpu_ms=120, ram_gb=4, disk_mb=50, net_mb=2
        ))

def logger_to_s3_flow(system):
    """Logger→S3非同期処理"""
    yield system.env.process(system.logger.process_request(cpu_ms=20, ram_gb=1))
    yield system.env.process(system.s3.process_request(
        cpu_ms=10, ram_gb=2, disk_mb=100, net_mb=20
    ))

def request_handler(system, request_id):
    """メインリクエスト処理フロー"""
    start_time = system.env.now
    
    # 1. Nginx処理
    yield system.env.process(system.nginx.process_request(cpu_ms=10, net_mb=1))
    
    # 2. APP1処理開始
    yield system.env.process(system.app1.process_request(cpu_ms=60, ram_gb=2))
    
    # 3. 並列処理（Auth + Policy + Service）
    auth_task = system.env.process(system.auth.process_request(cpu_ms=40, ram_gb=1))
    policy_task = system.env.process(system.policy.process_request(cpu_ms=30, ram_gb=1))
    service_task = system.env.process(service_with_db_flow(system))
    
    # Auth/Policy完了待ち（必須）
    yield system.env.all_of([auth_task, policy_task])
    
    # Service完了待ち
    yield service_task
    
    # 非同期ログ開始（待たない）
    system.env.process(logger_to_s3_flow(system))
    
    # 4. ServiceHub処理
    yield system.env.process(system.servicehub.process_request(cpu_ms=50, ram_gb=1))
    
    # 5. APP2最終処理
    yield system.env.process(system.app2.process_request(cpu_ms=40, ram_gb=2))
    
    # 全体メトリクス記録
    system.completed_requests += 1
    system.end_to_end_times.append(system.env.now - start_time)

def request_generator(system, arrival_rate=2.0, sim_time=100):
    """リクエスト生成プロセス"""
    request_id = 0
    while system.env.now < sim_time:
        system.total_requests += 1
        system.env.process(request_handler(system, f"req_{request_id}"))
        request_id += 1
        yield system.env.timeout(random.expovariate(arrival_rate))

def export_per_second_data(system, arrival_rate, sim_time):
    """毎秒データをJSON形式で出力"""
    servers = [system.nginx, system.app1, system.auth, system.policy, 
              system.service, system.db, system.logger, system.s3, 
              system.servicehub, system.app2]
    
    # データ構造準備
    export_data = {
        'scenario': {
            'arrival_rate': arrival_rate,
            'simulation_time': sim_time,
            'timestamp': datetime.now().isoformat()
        },
        'servers': {}
    }
    
    for server in servers:
        export_data['servers'][server.name] = {
            'specs': {
                'threads': server.cpu.capacity,
                'ram_gb': server.ram.capacity,
                'disk_queue_capacity': server.disk.capacity if hasattr(server.disk, 'capacity') else 'unlimited',
                'net_mbps': server.net_mbps
            },
            'per_second_data': {}
        }
        
        # 毎秒データを整理
        for second in range(int(sim_time) + 1):
            metrics = server.per_second_metrics.get(second, {
                'cpu_usage': 0.0,
                'ram_used': 0.0,
                'disk_queue': 0,
                'active_requests': 0,
                'requests_started': 0,
                'requests_completed': 0
            })
            
            # CPU使用率を計算（%）
            cpu_utilization = (metrics['cpu_usage'] / server.cpu.capacity) * 100
            
            # RAM使用率を計算（%）
            ram_utilization = (metrics['ram_used'] / server.ram.capacity) * 100
            
            export_data['servers'][server.name]['per_second_data'][str(second)] = {
                'cpu_usage_seconds': round(metrics['cpu_usage'], 3),
                'cpu_utilization_percent': round(cpu_utilization, 2),
                'ram_used_gb': round(metrics['ram_used'], 2),
                'ram_utilization_percent': round(ram_utilization, 2),
                'disk_queue_length': metrics['disk_queue'],
                'active_requests': metrics['active_requests'],
                'requests_started': metrics['requests_started'],
                'requests_completed': metrics['requests_completed']
            }
    
    return export_data

def run_high_load_simulation(arrival_rate, sim_time=60):
    """高負荷シミュレーション実行"""
    print(f"\n{'='*60}")
    print(f"🚀 高負荷シミュレーション: {arrival_rate} req/s")
    print(f"{'='*60}")
    
    env = simpy.Environment()
    system = MicroserviceSystem(env)
    
    # リクエスト生成開始
    env.process(request_generator(system, arrival_rate, sim_time))
    
    # シミュレーション実行
    env.run(until=sim_time)
    
    # === 結果分析 ===
    print(f"\n📊 全体性能結果")
    print(f"  総リクエスト数: {system.total_requests}")
    print(f"  完了リクエスト数: {system.completed_requests}")
    if system.total_requests > 0:
        success_rate = system.completed_requests / system.total_requests * 100
        print(f"  成功率: {success_rate:.1f}%")
        
        if system.end_to_end_times:
            avg_response = statistics.mean(system.end_to_end_times)
            print(f"  平均レスポンス時間: {avg_response:.3f}秒")
            if len(system.end_to_end_times) > 1:
                sorted_times = sorted(system.end_to_end_times)
                p95_idx = int(len(sorted_times) * 0.95)
                p99_idx = int(len(sorted_times) * 0.99)
                print(f"  P95レスポンス時間: {sorted_times[p95_idx]:.3f}秒")
                print(f"  P99レスポンス時間: {sorted_times[p99_idx]:.3f}秒")
            
            # SLO判定
            slo_ok = avg_response < 0.3
            print(f"  SLO(300ms): {'✅ OK' if slo_ok else '❌ NG'}")
    
    # サーバー負荷サマリー
    print(f"\n🖥️  サーバー負荷サマリー")
    servers = [system.nginx, system.app1, system.auth, system.policy, 
              system.service, system.db, system.logger, system.s3, 
              system.servicehub, system.app2]
    
    bottlenecks = []
    for server in servers:
        if server.total_requests > 0:
            cpu_util = (server.cpu_time / sim_time) * 100 / server.cpu.capacity
            avg_ram = statistics.mean(server.ram_usage) if server.ram_usage else 0
            ram_util = (server.ram.capacity - avg_ram) / server.ram.capacity * 100
            
            print(f"  {server.name:12} | "
                  f"Req:{server.total_requests:4} | "
                  f"CPU:{cpu_util:5.1f}% | "
                  f"RAM:{ram_util:5.1f}%")
            
            # ボトルネック判定
            if cpu_util > 70:
                bottlenecks.append(f"{server.name}(CPU:{cpu_util:.1f}%)")
            if ram_util > 80:
                bottlenecks.append(f"{server.name}(RAM:{ram_util:.1f}%)")
    
    if bottlenecks:
        print(f"\n⚠️  ボトルネック: {', '.join(bottlenecks)}")
    else:
        print(f"\n✅ 現在の負荷では問題なし")
    
    # JSONデータ出力
    per_second_data = export_per_second_data(system, arrival_rate, sim_time)
    filename = f"per_second_metrics_{arrival_rate}rps_{sim_time}s.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(per_second_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 毎秒メトリクスを {filename} に保存しました")
    
    return system, per_second_data

def analyze_high_loads():
    """高負荷でのボトルネック分析"""
    print("🚀 SimPy 高負荷マイクロサービス シミュレーション")
    print("=" * 80)
    
    # 高負荷シナリオ
    scenarios = [50, 100, 200]
    
    results = {}
    for rate in scenarios:
        system, data = run_high_load_simulation(rate, sim_time=60)
        results[rate] = {
            'system': system,
            'data': data
        }
    
    # 全体比較
    print(f"\n{'='*80}")
    print("📈 高負荷比較分析")
    print(f"{'='*80}")
    
    print(f"\n{'Scenario':>12} | {'Success Rate':>12} | {'Avg Response':>13} | {'P95 Response':>13} | {'SLO':>5}")
    print("-" * 80)
    
    for rate in scenarios:
        system = results[rate]['system']
        if system.end_to_end_times and system.total_requests > 0:
            success_rate = system.completed_requests / system.total_requests * 100
            avg_response = statistics.mean(system.end_to_end_times)
            sorted_times = sorted(system.end_to_end_times)
            p95_idx = int(len(sorted_times) * 0.95)
            p95_response = sorted_times[p95_idx]
            slo_status = "✅" if avg_response < 0.3 else "❌"
            
            print(f"{rate:>9} rps | {success_rate:>10.1f}% | {avg_response:>10.3f}s | {p95_response:>10.3f}s | {slo_status:>3}")
    
    print(f"\n💡 結果分析:")
    print(f"  - 各シナリオの毎秒メトリクスがJSONファイルに保存されました")
    print(f"  - CPU/RAM/Disk使用量の時系列データを確認できます")
    print(f"  - ボトルネック特定とスケーリング計画に活用してください")

if __name__ == "__main__":
    # 高負荷分析実行
    analyze_high_loads()
    
    print(f"\n{'='*80}")
    print("✨ 高負荷シミュレーション完了")
    print("📊 生成されたファイル:")
    print("  - per_second_metrics_50rps_60s.json")
    print("  - per_second_metrics_100rps_60s.json") 
    print("  - per_second_metrics_200rps_60s.json")
    print("=" * 80)