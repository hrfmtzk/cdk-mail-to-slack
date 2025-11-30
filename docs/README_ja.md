# ドキュメント

このディレクトリには、CDK Mail to Slackプロジェクトの技術ドキュメントが含まれています。

## ドキュメント一覧

### 人間向けドキュメント

#### [システム設計 (design.md)](./design.md)
システムのアーキテクチャ、コンポーネント構成、処理フロー、セキュリティ設計などを詳細に説明しています。

**主な内容:**
- システム構成図
- 主要コンポーネントの説明
- 処理フロー（通常フロー、エラーハンドリング）
- セキュリティ設計
- スケーラビリティと制約
- 運用考慮事項
- コスト見積もり

**対象読者:**
- システムアーキテクト
- 開発者
- 運用担当者

#### [コーディング規約 (coding-standards.md)](./coding-standards.md)
プロジェクトで使用するコーディング規約、ツール設定、テスト要件などを定義しています。

**主な内容:**
- Pythonコーディング規約
- コードフォーマット（Black、isort）
- リンター（flake8、mypy）
- テスト規約とカバレッジ要件
- CDKコーディング規約
- Lambdaコーディング規約
- Git規約
- CI/CD推奨設定
- コードレビュー基準

**対象読者:**
- 開発者
- コードレビュアー
- 新規参加者

### AIエージェント向けドキュメント

#### [AIエージェントガイドライン (ai-agent-guidelines.md)](./ai-agent-guidelines.md)
AIエージェント（GitHub Copilot、Amazon Q Developerなど）がコード生成や変更提案を行う際の行動規範とガイドラインです。

**主な内容:**
- コード生成の原則
- セキュリティガイドライン
- テスト要件
- CDKリソース生成ルール
- コード変更時のチェックリスト
- 特殊なケースの対応方法
- パフォーマンス考慮事項
- ドキュメント更新ルール

**対象読者:**
- AIコード生成ツール
- AI支援開発を行う開発者

## クイックリファレンス

### 新規開発者向け

1. **まず読むべきドキュメント:**
   - [プロジェクトREADME](../README.md) - セットアップ手順
   - [システム設計](./design.md) - アーキテクチャ理解
   - [コーディング規約](./coding-standards.md) - 開発ルール

2. **開発開始前のチェック:**
   ```bash
   # 依存関係インストール
   pip install -r requirements.txt -r requirements-dev.txt
   
   # テスト実行
   pytest
   
   # コード品質チェック
   black --check .
   isort --check .
   flake8
   mypy .
   ```

### AI支援開発を行う場合

1. **AIエージェント設定:**
   - [AIエージェントガイドライン](./ai-agent-guidelines.md)を参照
   - プロジェクトのコンテキストとして提供

2. **コード生成時の注意:**
   - 最小限の実装
   - セキュリティ要件の遵守
   - テストの同時生成

### トラブルシューティング

**問題が発生した場合:**

1. **メール受信の問題:**
   - [システム設計 - トラブルシューティング](./design.md#トラブルシューティング)を参照

2. **コード品質の問題:**
   - [コーディング規約](./coding-standards.md)を確認
   - リンター/フォーマッターを実行

3. **デプロイの問題:**
   - [プロジェクトREADME - デプロイ](../README.md#6-デプロイ)を参照

## ドキュメント更新ガイドライン

### 更新が必要な場合

以下の変更を行った場合は、関連ドキュメントを更新してください：

- **新機能追加** → design.md、README.md
- **設定パラメータ追加** → README.md、design.md
- **コーディング規約変更** → coding-standards.md
- **アーキテクチャ変更** → design.md
- **セキュリティ要件変更** → design.md、ai-agent-guidelines.md

### 更新手順

1. 該当ドキュメントを編集
2. 変更内容をコミットメッセージに記載
3. プルリクエストで変更内容を説明

## 関連リンク

### 外部ドキュメント

- [AWS CDK Python Reference](https://docs.aws.amazon.com/cdk/api/v2/python/)
- [AWS Lambda Powertools Python](https://docs.powertools.aws.dev/lambda/python/)
- [Slack API Documentation](https://api.slack.com/)
- [Amazon SES Developer Guide](https://docs.aws.amazon.com/ses/latest/dg/)

### プロジェクトリソース

- [GitHub Repository](https://github.com/hrfmtzk/cdk-mail-to-slack)
- [Issue Tracker](https://github.com/hrfmtzk/cdk-mail-to-slack/issues)

## フィードバック

ドキュメントの改善提案や誤りの報告は、[GitHub Issues](https://github.com/hrfmtzk/cdk-mail-to-slack/issues)またはプルリクエストでお願いします。

---

**最終更新:** 2025-11-30
