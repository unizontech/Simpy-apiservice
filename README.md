# 🚀 SimPy API Service - Microservice Simulation & Visualization

SimPyを使用したマイクロサービスシステムのシミュレーション with Real-time Visualization, Request Tracing, and Performance Analysis

[English](#english) | [日本語](#japanese)

## 📋 概要

このプロジェクトは、SimPyを使用してマイクロサービスアーキテクチャのパフォーマンスをシミュレートします。

### 主な機能
- マルチサーバー環境のシミュレーション（Nginx, App, Auth, Policy, Service, DB, Logger, S3等）
- CPU、メモリ、ディスク、ネットワークリソースの管理
- 並列処理と非同期処理のモデリング
- ボトルネック分析と性能評価
- スケーリング分析とSLO判定

## 🚀 セットアップ

### 1. リポジトリのクローン
```bash
git clone https://github.com/unizontech/Simpy-apiservice.git
cd Simpy-apiservice
```

### 2. 仮想環境の作成（推奨）
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. 依存関係のインストール
```bash
pip install -r requirements.txt
```

## 🎯 使い方

### 基本実行
```bash
python simpy_microservice.py
```

### 実行結果の例
```
🚀 SimPy マイクロサービス シミュレーション
============================================================
🔍 シミュレーション分析結果
============================================================

📊 全体性能
  総リクエスト数: 295
  完了リクエスト数: 290
  成功率: 98.3%
  平均レスポンス時間: 0.245秒
  P95レスポンス時間: 0.312秒

🖥️  各サーバー負荷分析
  Nginx        | リクエスト:290 | CPU使用率: 4.5% | RAM使用率: 12.5%
  APP1         | リクエスト:290 | CPU使用率: 10.9% | RAM使用率: 9.1%
  Auth         | リクエスト:290 | CPU使用率: 29.0% | RAM使用率: 9.1%
  ...
```

## 📊 分析できること

1. **ボトルネック特定**
   - どのサーバーがボトルネックになるか
   - CPU/Memory/Diskのどれが先に限界になるか

2. **キャパシティプランニング**
   - 何req/sまで処理できるか
   - SLOを満たすための必要台数

3. **アーキテクチャ評価**
   - 並列処理・非同期処理の効果
   - サービス間の依存関係の影響

## 🛠️ カスタマイズ

### サーバースペックの変更
```python
# simpy_microservice.py内で調整
self.nginx = Server(env, "Nginx", threads=8, ram_gb=16, net_mbps=40000)
```

### 負荷シナリオの変更
```python
scenarios = [
    {"rate": 1.0, "name": "軽負荷"},
    {"rate": 10.0, "name": "超高負荷"}  # 追加
]
```

## 📝 ライセンス

MIT License

## 🤝 コントリビューション

プルリクエストを歓迎します！

## 📧 お問い合わせ

masayuki@unizontech.jp