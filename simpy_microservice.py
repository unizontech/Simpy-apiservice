import simpy
import random
import statistics
from collections import defaultdict

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
    
    def process_request(self, cpu_ms=50, ram_gb=1, disk_mb=10, net_mb=5):
        start_time = self.env.now
        
        # メモリ確保
        yield self.ram.get(ram_gb)
        
        try:
            # CPU処理
            with self.cpu.request() as req:
                yield req
                cpu_time = cpu_ms / 1000.0  # ms to seconds
                yield self.env.timeout(cpu_time)
                self.cpu_time += cpu_time
            
            # Disk I/O（必要な場合）
            if disk_mb > 0:
                with self.disk.request() as dreq:
                    yield dreq
                    yield self.env.timeout(disk_mb / 500)  # 500MB/s assumed
            
            # Network処理時間
            if net_mb > 0:
                yield self.env.timeout(net_mb / (self.net_mbps / 8))
                
        finally:
            # メモリ解放
            yield self.ram.put(ram_gb)
            
        # メトリクス記録
        self.total_requests += 1
        self.response_times.append(self.env.now - start_time)
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

def run_simulation(arrival_rate=2.0, sim_time=100):
    """シミュレーション実行と結果分析"""
    env = simpy.Environment()
    system = MicroserviceSystem(env)
    
    # リクエスト生成開始
    env.process(request_generator(system, arrival_rate, sim_time))
    
    # シミュレーション実行
    env.run(until=sim_time)
    
    # === 結果分析：「何がわかるか」 ===
    print("=" * 60)
    print("🔍 シミュレーション分析結果")
    print("=" * 60)
    
    # 全体性能
    if system.end_to_end_times:
        print(f"\n📊 全体性能")
        print(f"  総リクエスト数: {system.total_requests}")
        print(f"  完了リクエスト数: {system.completed_requests}")
        print(f"  成功率: {system.completed_requests/system.total_requests*100:.1f}%")
        print(f"  平均レスポンス時間: {statistics.mean(system.end_to_end_times):.3f}秒")
        if len(system.end_to_end_times) > 1:
            sorted_times = sorted(system.end_to_end_times)
            p95_idx = int(len(sorted_times) * 0.95)
            print(f"  P95レスポンス時間: {sorted_times[p95_idx]:.3f}秒")
    
    # 各サーバーの負荷分析
    print(f"\n🖥️  各サーバー負荷分析")
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
                  f"リクエスト:{server.total_requests:3} | "
                  f"CPU使用率:{cpu_util:5.1f}% | "
                  f"RAM使用率:{ram_util:5.1f}%")
            
            # ボトルネック判定
            if cpu_util > 70:
                bottlenecks.append(f"{server.name}(CPU:{cpu_util:.1f}%)")
            if ram_util > 80:
                bottlenecks.append(f"{server.name}(RAM:{ram_util:.1f}%)")
    
    # ボトルネック特定
    print(f"\n⚠️  ボトルネック特定")
    if bottlenecks:
        print(f"  検出されたボトルネック: {', '.join(bottlenecks)}")
        print(f"  💡 改善提案: ボトルネックサーバーのスケールアップ/アウト検討")
    else:
        print(f"  ✅ 現在の負荷では問題なし")
        print(f"  💡 さらに負荷を上げてキャパシティ限界を特定可能")
    
    # 処理パターン分析
    print(f"\n🔄 処理パターン分析")
    print(f"  並列処理効果: Auth/Policy/Serviceの同時実行")
    print(f"  非同期効果: Logger→S3がメイン処理に影響せず")
    print(f"  依存関係: Service→DB (30%確率) の条件付き処理")
    
    return system

# 複数シナリオでのボトルネック特定
def analyze_scaling():
    """負荷を変えてボトルネックを特定"""
    print("\n" + "=" * 60)
    print("📈 スケーリング分析")
    print("=" * 60)
    
    scenarios = [
        {"rate": 1.0, "name": "軽負荷"},
        {"rate": 3.0, "name": "中負荷"}, 
        {"rate": 5.0, "name": "高負荷"},
        {"rate": 8.0, "name": "超高負荷"}
    ]
    
    for scenario in scenarios:
        print(f"\n🎯 {scenario['name']} (到着率: {scenario['rate']} req/s)")
        system = run_simulation(arrival_rate=scenario['rate'], sim_time=60)
        
        if system.end_to_end_times:
            avg_response = statistics.mean(system.end_to_end_times)
            print(f"   → 平均レスポンス: {avg_response:.3f}秒")
            
            # SLO判定（例：300ms以下）
            slo_ok = avg_response < 0.3
            print(f"   → SLO(300ms): {'✅ OK' if slo_ok else '❌ NG'}")

if __name__ == "__main__":
    print("🚀 SimPy マイクロサービス シミュレーション")
    
    # 基本シナリオ実行
    system = run_simulation(arrival_rate=3.0, sim_time=100)
    
    # スケーリング分析
    analyze_scaling()
    
    print("\n" + "=" * 60)
    print("✨ シミュレーション完了")
    print("💡 わかること:")
    print("  - どのサーバーがボトルネックになるか")
    print("  - 何req/sまで処理できるか") 
    print("  - CPU/Memory/Diskのどれが先に限界になるか")
    print("  - 並列処理・非同期処理の効果")
    print("  - SLOを満たすための必要台数")
    print("=" * 60)