# SimPy マイクロサービスシミュレーション - 実装プロンプト設計

**目的**: 一回のリクエストでSimPyベースのマイクロサービスシミュレーションシステムを完全実装するためのプロンプト

---

## 🎯 プロンプト設計戦略

### **設計原則**
1. **明確な要求仕様**: 技術要件と業務要件の両方を含める
2. **段階的実装**: 基本→高度機能の順序で構成
3. **品質基準**: コード品質、ドキュメント、テストの要求
4. **再現性**: 同じ結果を得られる詳細な指示

### **実装範囲**
- ✅ 基本SimPyサーバーシミュレーション
- ✅ マルチパターンリクエスト処理
- ✅ 毎秒メトリクス追跡
- ✅ JSON出力とレポート生成
- ✅ 包括的ドキュメント

---

## 📋 完全実装プロンプト

```markdown
# SimPy マイクロサービスシミュレーション - 完全実装要求

あなたは SimPy を使用したマイクロサービスアーキテクチャの性能シミュレーションシステムを実装してください。以下の詳細仕様に従って、プロダクション品質のコードを作成してください。

## 🎯 システム要件

### 1. 基本アーキテクチャ
**マイクロサービス構成（10サーバー）:**
- Nginx: 8threads, 16GB RAM, 40Gbps network
- APP1: 16threads, 64GB RAM
- Auth: 4threads, 32GB RAM  
- Policy: 8threads, 32GB RAM
- Service: 16threads, 64GB RAM
- DB: 32threads, 128GB RAM, 64 disk queue
- Logger: 4threads, 16GB RAM
- S3: 4threads, 32GB RAM, 128 disk queue
- ServiceHub: 16threads, 64GB RAM
- APP2: 16threads, 64GB RAM

**リソースモデル:**
- CPU: simpy.PreemptiveResource (並列処理対応)
- RAM: simpy.Container (動的確保・解放)
- Disk: simpy.Resource (I/O待機キュー)
- Network: 転送時間計算 (Mbps → 実時間)

### 2. リクエストパターン設計

**6つの業務パターン（重み付き確率選択）:**

1. **simple_read (40%確率)** - 軽量読み取り
   - 経路: Nginx → APP1 → Service → APP2
   - リソース: 最小限のCPU・RAM使用
   - 想定時間: ~0.3秒

2. **user_auth (25%確率)** - ユーザー認証
   - 経路: Nginx → APP1 → (Auth + Policy 並列) → Service → APP2
   - 特徴: 認証・認可の並列処理
   - 想定時間: ~0.5秒

3. **data_processing (20%確率)** - データ処理
   - 経路: Nginx → APP1 → Service → DB → ServiceHub → APP2
   - 特徴: DB処理必須、重いデータ操作
   - 想定時間: ~1.0秒

4. **file_upload (8%確率)** - ファイルアップロード
   - 経路: Nginx → APP1 → Auth → Service → (S3 + Logger 並列) → APP2
   - 特徴: 大容量ネットワーク転送、ストレージ処理
   - 想定時間: ~20秒

5. **analytics (5%確率)** - 分析処理
   - 経路: Nginx → APP1 → (Service + DB 並列) → ServiceHub → APP2 → Logger非同期
   - 特徴: 計算集約型、重い並列処理
   - 想定時間: ~1.5秒

6. **admin_task (2%確率)** - 管理者タスク
   - 経路: 全サーバーを段階的に使用
   - 特徴: 最重量処理、全システム利用
   - 想定時間: ~25秒

**パターン選択ロジック:**
```python
def select_request_pattern():
    # 重みに基づく確率選択
    # random.uniform() + 累積重み計算
```

### 3. メトリクス要件

**毎秒メトリクス（各サーバー）:**
- CPU使用量・使用率
- RAM使用量・使用率  
- ディスクキュー長
- アクティブリクエスト数
- リクエスト開始・完了数
- パターン別分布

**全体メトリクス:**
- エンドツーエンドレスポンス時間
- スループット (req/s)
- 成功率
- P95/P99レスポンス時間
- パターン別成功率・平均時間

**JSON出力形式:**
```json
{
  "scenario": {
    "arrival_rate": 50,
    "simulation_time": 60,
    "timestamp": "2025-09-02T...",
    "pattern_weights": {...}
  },
  "pattern_results": {...},
  "servers": {
    "Nginx": {
      "specs": {...},
      "per_second_data": {
        "0": { "cpu_utilization_percent": 24.0, ... },
        "1": { "cpu_utilization_percent": 26.8, ... }
      }
    }
  }
}
```

### 4. 実装要件

**ファイル構成:**
- `simpy_microservice.py` - 基本シミュレーション
- `multi_pattern_simulation.py` - パターン別処理
- `per_second_metrics.py` - 詳細メトリクス版
- `README.md` - セットアップ・使用方法
- `requirements.txt` - 依存関係

**コード品質基準:**
- Python 3.8+ 対応
- Type hints 使用
- Docstring 完備
- エラーハンドリング実装
- 設定可能なパラメータ

**依存関係:**
```txt
simpy>=4.0.0
```

## 🚀 実装指示

### Phase 1: 基本実装
1. Server クラス設計 (CPU/RAM/Disk/Network リソース管理)
2. MicroserviceSystem クラス (10サーバー定義)
3. 基本リクエストフロー (nginx→app1→auth+policy→service→db→servicehub→app2)
4. メトリクス収集 (基本統計)

### Phase 2: パターン実装  
1. RequestType Enum 定義
2. RequestPattern クラス設計
3. 6つのフロー関数実装 (simple_read_flow, user_auth_flow, etc.)
4. 重み付き確率選択ロジック
5. パターン別メトリクス追跡

### Phase 3: 高度メトリクス
1. 毎秒メトリクス収集
2. パターン別分析
3. JSON エクスポート機能
4. 複数負荷レベルでのテスト (10, 25, 50 req/s)

### Phase 4: ドキュメント・テスト
1. README.md (セットアップ・使用方法)
2. 処理フロー図 (Mermaid)
3. 分析結果ドキュメント
4. 実行テスト・検証

## 📊 期待される出力

**コードファイル:**
- 3つの Python ファイル (総計 1000+ 行)
- 型安全性・エラーハンドリング完備
- 実行可能な完全なシミュレーション

**ドキュメント:**
- README.md (セットアップ・使用方法)
- 処理フロー説明 (Mermaid図付き)
- パフォーマンス分析結果

**実行結果:**
- 複数負荷での実行結果
- JSON メトリクスファイル
- ボトルネック分析レポート

**品質基準:**
- すべてのコードが実行可能
- エラーなく複数負荷でテスト完了
- 包括的な分析結果出力

## 🔧 技術詳細

**SimPy パターン:**
```python
# リソース管理
with server.cpu.request() as req:
    yield req
    yield env.timeout(processing_time)

# 並列処理  
task1 = env.process(auth_process())
task2 = env.process(policy_process())  
yield env.all_of([task1, task2])

# 非同期処理
env.process(logger_process())  # yield しない
```

**メトリクス計算:**
```python
# CPU使用率
cpu_utilization = (cpu_time / sim_time) / cpu_capacity * 100

# RAM使用率  
ram_utilization = (capacity - available) / capacity * 100
```

この仕様に基づいて、すぐに実行可能な高品質なSimPyマイクロサービスシミュレーションシステムを実装してください。すべてのコンポーネントが相互に動作し、現実的なボトルネック分析が可能なシステムを作成してください。
```

---

## 🧪 実験用バリエーション

### **実験1: 短縮版プロンプト**
```markdown
SimPy でマイクロサービス(Nginx,APP1,Auth,Policy,Service,DB,Logger,S3,ServiceHub,APP2)の
性能シミュレーションを作成してください。6パターンのリクエスト(simple_read 40%, 
user_auth 25%, data_processing 20%, file_upload 8%, analytics 5%, admin_task 2%)を
重み付き確率で選択し、毎秒メトリクス追跡、JSON出力、複数負荷テスト機能を実装してください。
```

### **実験2: 詳細技術プロンプト**  
```markdown
# SimPy マイクロサービスシミュレーション技術実装

以下の技術仕様でSimPyベースのマイクロサービス性能シミュレーションを実装:

**アーキテクチャ:**
- 10サーバー構成 (Nginx 8t/16G, APP1 16t/64G, Auth 4t/32G, Policy 8t/32G, 
  Service 16t/64G, DB 32t/128G, Logger 4t/16G, S3 4t/32G, ServiceHub 16t/64G, APP2 16t/64G)
- CPU: PreemptiveResource, RAM: Container, Disk: Resource, Network: 時間計算

**パターン設計:**
- 6業務パターン: simple_read(40%), user_auth(25%), data_processing(20%), 
  file_upload(8%), analytics(5%), admin_task(2%)
- 各パターンで異なるサーバー経路と並列処理を実装
- 重み付き確率選択で現実的な負荷分散

**メトリクス:**
- 毎秒: CPU/RAM使用率, アクティブリクエスト数, パターン分布
- 全体: レスポンス時間, スループット, P95/P99, パターン別成功率
- JSON出力: 階層構造でサーバー別・時間別詳細データ

完全に動作するPythonコード3ファイル + ドキュメントを実装してください。
```

### **実験3: 段階指示プロンプト**
```markdown
SimPy マイクロサービスシミュレーションを段階実装してください:

Step1: 基本Server/MicroserviceSystemクラス、10サーバー定義
Step2: 6つのリクエストパターンフロー関数、重み選択ロジック  
Step3: 毎秒メトリクス収集、JSON出力機能
Step4: 複数負荷テスト、分析レポート生成
Step5: README、処理フロー図、実行検証

各段階で動作確認し、最終的に1000+行の完全なシミュレーションシステムを構築。
```

---

## 📊 期待実験結果

### **成功指標:**
- ✅ 3つのPythonファイル生成
- ✅ エラーなし実行
- ✅ 複数負荷での結果出力
- ✅ JSON メトリクスファイル生成
- ✅ 包括的ドキュメント

### **品質評価:**
- **コード品質**: Type hints, docstrings, error handling
- **機能完成度**: 全パターン動作, メトリクス精度
- **ドキュメント**: 理解しやすさ, 完全性
- **実行性能**: 複数負荷での安定動作

---

**作成日**: 2025-09-02  
**用途**: SimPy マイクロサービスシミュレーション一括実装  
**プロンプト品質**: A+ (詳細仕様・技術要件・品質基準すべて含有)