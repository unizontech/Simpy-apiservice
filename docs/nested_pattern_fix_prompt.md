# SimPy マイクロサービス - 入れ子パターン修正プロンプト

**目的**: 既存のSimPyマイクロサービスシミュレーションに、リアルなAPI呼び出し制御パターン（入れ子リソース管理）を適用する

---

## 🎯 修正指示プロンプト

```markdown
# SimPy マイクロサービス - 入れ子リソース管理修正

既存のSimPyマイクロサービスシミュレーションコードを修正して、現実的なAPI呼び出しパターンを実装してください。

## 🔧 現在の問題

**現在の実装（非現実的）:**
```python
def user_auth_flow(system, req_type):
    # 各サーバーが独立してセッションを保持 - 非現実的
    yield system.env.process(system.nginx.process_request(...))
    yield system.env.process(system.app1.process_request(...))
    yield system.env.process(system.auth.process_request(...))
    yield system.env.process(system.db.process_request(...))
```

**問題点:**
- 各マイクロサービスが独立してセッション/コネクションを保持
- 実際のAPI呼び出しパターンと異なる
- リソース使用効率が悪い

## 🎯 修正要求

### 1. **セッション管理の分離**

**Server クラスに追加:**
```python
class Server:
    def __init__(self, env, name, threads=4, ram_gb=32, disk_q=16, net_mbps=1000):
        # 既存のリソース
        self.cpu = simpy.PreemptiveResource(env, capacity=threads)
        self.ram = simpy.Container(env, capacity=ram_gb, init=ram_gb)
        self.disk = simpy.Resource(env, capacity=disk_q)
        
        # 追加: セッション管理用リソース（入れ子パターン対応）
        self.sessions = simpy.Resource(env, capacity=threads * 2)
    
    def acquire_session(self):
        """セッション/接続スロットを取得 - リクエスト終了まで保持"""
        return self.sessions.request()
        
    def cpu_burst(self, cpu_ms=50, ram_gb=1, disk_mb=10, net_mb=5, req_type=None):
        """CPU処理バースト - 即座に取得/解放（入れ子パターン用）"""
        # 既存のprocess_request内容をバースト処理として実装
        # メモリ確保 → CPU処理 → ディスクI/O → メモリ解放
```

### 2. **リアルなAPI呼び出しフロー実装**

**修正対象フロー:**
- `user_auth_flow` - ユーザー認証処理
- `data_processing_flow` - データ処理 
- `file_upload_flow` - ファイルアップロード
- `analytics_flow` - 分析処理

**実装パターン例 (user_auth_flow):**
```python
def user_auth_flow(system, req_type):
    """ユーザー認証処理 - 現実的なAPI制御パターン"""
    # APP1がメインセッションを保持し、他サービスは短期呼び出し
    with system.app1.acquire_session() as app1_session:
        yield app1_session
        
        # Nginx: ロードバランサー処理（バースト）
        yield system.env.process(system.nginx.cpu_burst(cpu_ms=10, net_mb=1, req_type=req_type))
        
        # APP1: メイン処理（セッション保持中）
        yield system.env.process(system.app1.cpu_burst(cpu_ms=40, ram_gb=2, req_type=req_type))
        
        # 認証・認可サービス呼び出し（並列バースト）
        auth_task = system.env.process(system.auth.cpu_burst(cpu_ms=60, ram_gb=2, req_type=req_type))
        policy_task = system.env.process(system.policy.cpu_burst(cpu_ms=45, ram_gb=1, req_type=req_type))
        yield system.env.all_of([auth_task, policy_task])
        
        # 後続サービス呼び出し（バースト）
        yield system.env.process(system.service.cpu_burst(cpu_ms=50, ram_gb=2, req_type=req_type))
        yield system.env.process(system.app2.cpu_burst(cpu_ms=30, ram_gb=2, req_type=req_type))
    
    # withブロック終了時にAPP1セッション自動解放
```

### 3. **制御パターン適用指針**

**リソース保持方針:**
- **長期保持**: API Gateway (Nginx), メインアプリ (APP1, APP2) → `acquire_session()`
- **短期呼び出し**: Auth, DB, Policy, Service, Logger, S3 → `cpu_burst()`

**並列処理活用:**
- 独立処理: `env.all_of([task1, task2])` で並列実行
- 非同期処理: Logger等は `env.process()` のみ（yieldしない）

### 4. **修正対象ファイル**

修正すべきファイル:
- `src/simulations/multi_pattern_simulation.py` - メイン修正対象
- `src/simulations/per_second_metrics.py` - 同様修正適用
- `src/simulations/simpy_microservice.py` - 基本版も修正

## 📊 期待する改善効果

**リソース効率改善:**
- 不要な長期セッション削減 → スループット向上
- 現実的なリソース競合パターン

**シミュレーション精度向上:**
- 実際のマイクロサービス制御パターンに合致
- ボトルネック特定精度の向上
- キャパシティプランニング精度向上

## ✅ 修正完了の確認項目

1. **動作検証**: 修正コードがエラーなく実行される
2. **パフォーマンス**: 修正前後のメトリクス比較
3. **パターン確認**: 全6パターンで入れ子制御が適用されている
4. **コメント追加**: 修正箇所に「修正: 入れ子パターン対応」コメント

この修正により、SimPyシミュレーションが実際のマイクロサービス環境により近い動作をするようになります。
```

---

## 🧪 テスト用バリエーション

### **短縮版プロンプト**
```
SimPyマイクロサービスコードを修正してください。各サーバーが独立セッション保持している問題を解決し、
APP1がメインセッション保持、他サービス(Auth,DB,Policy等)は短期cpu_burst()呼び出しパターンに変更。
現実的なAPI制御フローを実装してください。
```

### **技術重視プロンプト**
```
SimPy Resource管理を修正: 
1) Server.sessions = Resource(capacity=threads*2) 追加
2) acquire_session()メソッド実装 
3) cpu_burst()で短期リソース取得/解放
4) user_auth_flow等でwith文によるセッション管理
実際のマイクロサービス制御パターンに合致させてください。
```

---

**作成日**: 2025-09-05  
**用途**: 入れ子パターン修正の差分プロンプトテスト  
**対象**: 既存SimPyマイクロサービスシミュレーションコードの改善