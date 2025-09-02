import simpy
import random
import statistics
import json
from collections import defaultdict
from datetime import datetime
from enum import Enum

class RequestType(Enum):
    """リクエストタイプの定義"""
    SIMPLE_READ = "simple_read"          # 軽量な読み取り処理
    USER_AUTH = "user_auth"              # ユーザー認証処理  
    DATA_PROCESSING = "data_processing"  # データ処理
    FILE_UPLOAD = "file_upload"          # ファイルアップロード
    ANALYTICS = "analytics"              # 分析処理
    ADMIN_TASK = "admin_task"           # 管理者タスク

class RequestPattern:
    """リクエストパターンの定義"""
    def __init__(self, req_type: RequestType, weight: float, description: str):
        self.req_type = req_type
        self.weight = weight  # 発生確率の重み
        self.description = description

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
        self.request_types = defaultdict(int)  # リクエストタイプ別カウント
        
        # 毎秒メトリクス
        self.per_second_metrics = defaultdict(lambda: {
            'cpu_usage': 0.0,
            'ram_used': 0.0,
            'disk_queue': 0,
            'active_requests': 0,
            'requests_started': 0,
            'requests_completed': 0,
            'request_types': defaultdict(int)
        })
    
    def process_request(self, cpu_ms=50, ram_gb=1, disk_mb=10, net_mb=5, req_type=None):
        start_time = self.env.now
        start_second = int(start_time)
        
        # リクエスト開始を記録
        self.per_second_metrics[start_second]['requests_started'] += 1
        self.per_second_metrics[start_second]['active_requests'] += 1
        if req_type:
            self.per_second_metrics[start_second]['request_types'][req_type.value] += 1
            self.request_types[req_type.value] += 1
        
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
        self.pattern_metrics = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'success_count': 0
        })

# パターン別処理フロー定義

def simple_read_flow(system, req_type):
    """軽量な読み取り処理 - 最小限の処理"""
    # Nginx → APP1 → Service → APP2
    yield system.env.process(system.nginx.process_request(cpu_ms=5, net_mb=0.5, req_type=req_type))
    yield system.env.process(system.app1.process_request(cpu_ms=20, ram_gb=1, req_type=req_type))
    yield system.env.process(system.service.process_request(cpu_ms=30, ram_gb=1, req_type=req_type))
    yield system.env.process(system.app2.process_request(cpu_ms=15, ram_gb=1, req_type=req_type))

def user_auth_flow(system, req_type):
    """ユーザー認証処理 - 認証重視"""
    # Nginx → APP1 → Auth + Policy (並列) → Service → APP2
    yield system.env.process(system.nginx.process_request(cpu_ms=10, net_mb=1, req_type=req_type))
    yield system.env.process(system.app1.process_request(cpu_ms=40, ram_gb=2, req_type=req_type))
    
    # 認証・認可処理（並列）
    auth_task = system.env.process(system.auth.process_request(cpu_ms=60, ram_gb=2, req_type=req_type))
    policy_task = system.env.process(system.policy.process_request(cpu_ms=45, ram_gb=1, req_type=req_type))
    yield system.env.all_of([auth_task, policy_task])
    
    yield system.env.process(system.service.process_request(cpu_ms=50, ram_gb=2, req_type=req_type))
    yield system.env.process(system.app2.process_request(cpu_ms=30, ram_gb=2, req_type=req_type))

def data_processing_flow(system, req_type):
    """データ処理 - DB重視"""
    # Nginx → APP1 → Service → DB → ServiceHub → APP2
    yield system.env.process(system.nginx.process_request(cpu_ms=10, net_mb=2, req_type=req_type))
    yield system.env.process(system.app1.process_request(cpu_ms=50, ram_gb=3, req_type=req_type))
    yield system.env.process(system.service.process_request(cpu_ms=100, ram_gb=4, req_type=req_type))
    
    # DB処理（必須）
    yield system.env.process(system.db.process_request(
        cpu_ms=200, ram_gb=8, disk_mb=100, net_mb=5, req_type=req_type
    ))
    
    yield system.env.process(system.servicehub.process_request(cpu_ms=80, ram_gb=3, req_type=req_type))
    yield system.env.process(system.app2.process_request(cpu_ms=60, ram_gb=3, req_type=req_type))

def file_upload_flow(system, req_type):
    """ファイルアップロード - ストレージ重視"""
    # Nginx → APP1 → Auth → Service → S3 + Logger (並列)
    yield system.env.process(system.nginx.process_request(cpu_ms=15, net_mb=50, req_type=req_type))
    yield system.env.process(system.app1.process_request(cpu_ms=80, ram_gb=8, req_type=req_type))
    yield system.env.process(system.auth.process_request(cpu_ms=40, ram_gb=1, req_type=req_type))
    yield system.env.process(system.service.process_request(cpu_ms=120, ram_gb=6, req_type=req_type))
    
    # ストレージ処理（並列）
    s3_task = system.env.process(system.s3.process_request(
        cpu_ms=30, ram_gb=10, disk_mb=500, net_mb=100, req_type=req_type
    ))
    logger_task = system.env.process(system.logger.process_request(cpu_ms=25, ram_gb=2, req_type=req_type))
    yield system.env.all_of([s3_task, logger_task])
    
    yield system.env.process(system.app2.process_request(cpu_ms=40, ram_gb=4, req_type=req_type))

def analytics_flow(system, req_type):
    """分析処理 - 計算集約型"""
    # Nginx → APP1 → Service + DB (並列) → ServiceHub → APP2
    yield system.env.process(system.nginx.process_request(cpu_ms=10, net_mb=3, req_type=req_type))
    yield system.env.process(system.app1.process_request(cpu_ms=100, ram_gb=8, req_type=req_type))
    
    # 重い並列処理
    service_task = system.env.process(system.service.process_request(cpu_ms=300, ram_gb=12, req_type=req_type))
    db_task = system.env.process(system.db.process_request(
        cpu_ms=400, ram_gb=16, disk_mb=200, net_mb=10, req_type=req_type
    ))
    yield system.env.all_of([service_task, db_task])
    
    yield system.env.process(system.servicehub.process_request(cpu_ms=200, ram_gb=8, req_type=req_type))
    yield system.env.process(system.app2.process_request(cpu_ms=80, ram_gb=6, req_type=req_type))
    
    # 分析結果のログ（非同期）
    system.env.process(system.logger.process_request(cpu_ms=30, ram_gb=3, req_type=req_type))

def admin_task_flow(system, req_type):
    """管理者タスク - 全サーバー使用"""
    # 全サーバーを段階的に使用する重い処理
    yield system.env.process(system.nginx.process_request(cpu_ms=20, net_mb=5, req_type=req_type))
    yield system.env.process(system.app1.process_request(cpu_ms=150, ram_gb=10, req_type=req_type))
    
    # 認証・認可（管理者権限チェック）
    auth_task = system.env.process(system.auth.process_request(cpu_ms=80, ram_gb=3, req_type=req_type))
    policy_task = system.env.process(system.policy.process_request(cpu_ms=120, ram_gb=4, req_type=req_type))
    yield system.env.all_of([auth_task, policy_task])
    
    # メインタスク処理
    yield system.env.process(system.service.process_request(cpu_ms=250, ram_gb=8, req_type=req_type))
    yield system.env.process(system.db.process_request(
        cpu_ms=300, ram_gb=20, disk_mb=150, net_mb=8, req_type=req_type
    ))
    yield system.env.process(system.servicehub.process_request(cpu_ms=180, ram_gb=6, req_type=req_type))
    
    # 結果保存（並列）
    s3_task = system.env.process(system.s3.process_request(
        cpu_ms=50, ram_gb=8, disk_mb=300, net_mb=50, req_type=req_type
    ))
    logger_task = system.env.process(system.logger.process_request(cpu_ms=40, ram_gb=4, req_type=req_type))
    yield system.env.all_of([s3_task, logger_task])
    
    yield system.env.process(system.app2.process_request(cpu_ms=100, ram_gb=8, req_type=req_type))

# パターン定義
REQUEST_PATTERNS = [
    RequestPattern(RequestType.SIMPLE_READ, 40.0, "軽量読み取り - キャッシュヒット等"),
    RequestPattern(RequestType.USER_AUTH, 25.0, "ユーザー認証 - ログイン・権限確認"),
    RequestPattern(RequestType.DATA_PROCESSING, 20.0, "データ処理 - 計算・変換処理"),
    RequestPattern(RequestType.FILE_UPLOAD, 8.0, "ファイルアップロード - 画像・ドキュメント"),
    RequestPattern(RequestType.ANALYTICS, 5.0, "分析処理 - レポート生成・統計"),
    RequestPattern(RequestType.ADMIN_TASK, 2.0, "管理者タスク - システム管理・メンテナンス")
]

def select_request_pattern():
    """重みに基づいてリクエストパターンを選択"""
    total_weight = sum(pattern.weight for pattern in REQUEST_PATTERNS)
    rand = random.uniform(0, total_weight)
    
    cumulative = 0
    for pattern in REQUEST_PATTERNS:
        cumulative += pattern.weight
        if rand <= cumulative:
            return pattern.req_type
    
    return RequestType.SIMPLE_READ  # デフォルト

def request_handler(system, request_id):
    """パターンに応じたリクエスト処理"""
    start_time = system.env.now
    req_type = select_request_pattern()
    
    try:
        # パターンに応じた処理フロー実行
        if req_type == RequestType.SIMPLE_READ:
            yield system.env.process(simple_read_flow(system, req_type))
        elif req_type == RequestType.USER_AUTH:
            yield system.env.process(user_auth_flow(system, req_type))
        elif req_type == RequestType.DATA_PROCESSING:
            yield system.env.process(data_processing_flow(system, req_type))
        elif req_type == RequestType.FILE_UPLOAD:
            yield system.env.process(file_upload_flow(system, req_type))
        elif req_type == RequestType.ANALYTICS:
            yield system.env.process(analytics_flow(system, req_type))
        elif req_type == RequestType.ADMIN_TASK:
            yield system.env.process(admin_task_flow(system, req_type))
        
        # 成功メトリクス記録
        system.completed_requests += 1
        end_time = system.env.now
        response_time = end_time - start_time
        system.end_to_end_times.append(response_time)
        
        # パターン別メトリクス
        system.pattern_metrics[req_type.value]['count'] += 1
        system.pattern_metrics[req_type.value]['total_time'] += response_time
        system.pattern_metrics[req_type.value]['success_count'] += 1
        
    except Exception as e:
        # エラーメトリクス記録
        system.pattern_metrics[req_type.value]['count'] += 1
        print(f"Request {request_id} failed: {e}")

def request_generator(system, arrival_rate=2.0, sim_time=100):
    """リクエスト生成プロセス"""
    request_id = 0
    while system.env.now < sim_time:
        system.total_requests += 1
        system.env.process(request_handler(system, f"req_{request_id}"))
        request_id += 1
        yield system.env.timeout(random.expovariate(arrival_rate))

def run_pattern_simulation(arrival_rate, sim_time=60):
    """パターン別シミュレーション実行"""
    print(f"\n{'='*70}")
    print(f"🚀 マルチパターンシミュレーション: {arrival_rate} req/s")
    print(f"{'='*70}")
    
    env = simpy.Environment()
    system = MicroserviceSystem(env)
    
    # リクエスト生成開始
    env.process(request_generator(system, arrival_rate, sim_time))
    
    # シミュレーション実行
    env.run(until=sim_time)
    
    # === パターン別分析 ===
    print(f"\n📊 パターン別処理結果")
    print(f"{'パターン':20} | {'件数':>6} | {'成功率':>8} | {'平均時間':>10} | {'説明'}")
    print("-" * 80)
    
    for pattern in REQUEST_PATTERNS:
        metrics = system.pattern_metrics[pattern.req_type.value]
        if metrics['count'] > 0:
            success_rate = (metrics['success_count'] / metrics['count']) * 100
            avg_time = metrics['total_time'] / metrics['success_count'] if metrics['success_count'] > 0 else 0
            print(f"{pattern.req_type.value:20} | {metrics['count']:>6} | {success_rate:>6.1f}% | {avg_time:>8.3f}s | {pattern.description}")
    
    # === 全体性能 ===
    print(f"\n📈 全体性能結果")
    print(f"  総リクエスト数: {system.total_requests}")
    print(f"  完了リクエスト数: {system.completed_requests}")
    if system.total_requests > 0:
        success_rate = system.completed_requests / system.total_requests * 100
        print(f"  全体成功率: {success_rate:.1f}%")
        
        if system.end_to_end_times:
            avg_response = statistics.mean(system.end_to_end_times)
            print(f"  平均レスポンス時間: {avg_response:.3f}秒")
            if len(system.end_to_end_times) > 1:
                sorted_times = sorted(system.end_to_end_times)
                p95_idx = int(len(sorted_times) * 0.95)
                print(f"  P95レスポンス時間: {sorted_times[p95_idx]:.3f}秒")
    
    # === サーバー別リクエストタイプ分析 ===
    print(f"\n🖥️ サーバー別リクエストタイプ分布")
    servers = [system.nginx, system.app1, system.auth, system.policy, 
              system.service, system.db, system.logger, system.s3, 
              system.servicehub, system.app2]
    
    for server in servers:
        if server.total_requests > 0:
            print(f"\n{server.name}: {server.total_requests}件")
            for req_type, count in server.request_types.items():
                percentage = (count / server.total_requests) * 100
                print(f"  {req_type:20}: {count:>4}件 ({percentage:>5.1f}%)")
    
    # JSONデータ出力
    export_data = export_pattern_data(system, arrival_rate, sim_time)
    filename = f"pattern_metrics_{arrival_rate}rps_{sim_time}s.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 パターン別メトリクスを {filename} に保存しました")
    
    return system

def export_pattern_data(system, arrival_rate, sim_time):
    """パターン別データをJSON形式で出力"""
    servers = [system.nginx, system.app1, system.auth, system.policy, 
              system.service, system.db, system.logger, system.s3, 
              system.servicehub, system.app2]
    
    export_data = {
        'scenario': {
            'arrival_rate': arrival_rate,
            'simulation_time': sim_time,
            'timestamp': datetime.now().isoformat(),
            'pattern_weights': {pattern.req_type.value: pattern.weight for pattern in REQUEST_PATTERNS}
        },
        'pattern_results': {},
        'servers': {}
    }
    
    # パターン別結果
    for pattern_name, metrics in system.pattern_metrics.items():
        if metrics['count'] > 0:
            export_data['pattern_results'][pattern_name] = {
                'request_count': metrics['count'],
                'success_count': metrics['success_count'],
                'success_rate_percent': (metrics['success_count'] / metrics['count']) * 100,
                'total_time_seconds': round(metrics['total_time'], 3),
                'average_time_seconds': round(metrics['total_time'] / metrics['success_count'], 3) if metrics['success_count'] > 0 else 0
            }
    
    # サーバー別データ
    for server in servers:
        export_data['servers'][server.name] = {
            'total_requests': server.total_requests,
            'request_type_distribution': dict(server.request_types),
            'resource_usage': {
                'cpu_utilization_percent': (server.cpu_time / sim_time) * 100 / server.cpu.capacity,
                'average_ram_usage_gb': statistics.mean(server.ram_usage) if server.ram_usage else 0,
                'average_response_time_seconds': statistics.mean(server.response_times) if server.response_times else 0
            }
        }
    
    return export_data

if __name__ == "__main__":
    print("🚀 SimPy マルチパターン マイクロサービス シミュレーション")
    print("=" * 70)
    
    print("\n📋 定義されたリクエストパターン:")
    for i, pattern in enumerate(REQUEST_PATTERNS, 1):
        print(f"{i}. {pattern.req_type.value:20} (重み: {pattern.weight:4.1f}%) - {pattern.description}")
    
    # 複数負荷でテスト
    test_rates = [10, 25, 50]
    
    for rate in test_rates:
        run_pattern_simulation(rate, sim_time=60)
    
    print(f"\n{'='*70}")
    print("✨ マルチパターンシミュレーション完了")
    print("📊 各パターンの処理特性とボトルネックを確認してください")
    print("=" * 70)