# システム設計ドキュメント

## 概要

Amazon SESで受信したメールをAmazon S3に保存し、AWS Lambdaが自動的にSlackへ通知するシステムです。

## システム構成図

```
┌─────────────┐
│   Email     │
│  Sender     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Amazon SES                      │
│  - TLS強制 (TlsPolicy: Require)        │
│  - スパム/ウイルススキャン有効          │
│  - ReceiptRule: ドメイン宛メール受信   │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Amazon S3                       │
│  - ses-emails/ プレフィックス           │
│  - 30日後自動削除                       │
│  - SSL強制                              │
│  - アクセスログ (90日保持)              │
└──────┬──────────────────────────────────┘
       │ (S3 Event Notification)
       ▼
┌─────────────────────────────────────────┐
│         AWS Lambda                      │
│  - Python 3.14                          │
│  - メモリ: 128MB                        │
│  - タイムアウト: 30秒                   │
│  - 同時実行数: 10                       │
│  - X-Ray トレーシング (オプション)      │
│  - Sentry エラートラッキング (オプション)│
└──────┬──────────────────────────────────┘
       │
       ├─→ AWS Secrets Manager (Slack Token取得)
       │
       └─→ Slack API (chat.postMessage)
              │
              ▼
         ┌─────────────┐
         │   Slack     │
         │  Channel    │
         └─────────────┘
```

## 主要コンポーネント

### 1. Amazon SES (Simple Email Service)

**役割:**
- 指定ドメイン宛のメール受信
- S3への自動保存

**セキュリティ設定:**
- **TLS強制**: 暗号化されていない接続を拒否
- **スパム/ウイルススキャン**: 悪意のあるメールを自動ブロック

**設定:**
- ReceiptRuleSet: 新規作成または既存利用
- Recipients: `config.DOMAIN_NAME`で指定したドメイン
- Actions: S3保存 (`ses-emails/`プレフィックス)

### 2. Amazon S3

**バケット構成:**

1. **メール保存バケット**
   - プレフィックス: `ses-emails/`
   - ライフサイクル: 30日後自動削除
   - 暗号化: S3マネージド (SSE-S3)
   - SSL強制: バケットポリシーで実装

2. **アクセスログバケット**
   - ライフサイクル: 90日後自動削除
   - 監査目的で長期保持

### 3. AWS Lambda

**実行環境:**
- ランタイム: Python 3.14
- メモリ: 128MB
- タイムアウト: 30秒
- 同時実行数: 10 (Slack APIレート制限対策)

**環境変数:**
- `DOMAIN_NAME`: メール受信ドメイン
- `SLACK_BOT_TOKEN_SECRET_NAME`: Secrets Managerのシークレット名
- `SLACK_ERROR_CHANNEL`: エラー通知先チャンネル
- `LOG_LEVEL`: ログレベル (INFO)
- `POWERTOOLS_SERVICE_NAME`: サービス名
- `ENABLE_XRAY_TRACING`: X-Rayトレーシング有効化 (オプション)
- `SENTRY_DSN`: Sentry DSN (オプション)

**使用ライブラリ:**
- `aws-lambda-powertools`: ロギング、トレーシング
- `slack-sdk`: Slack API連携
- `sentry-sdk`: エラートラッキング (オプション)

### 4. AWS Secrets Manager

**保存内容:**
- Slack Bot Token (`xoxb-...`)
- JSON形式: `{"SLACK_BOT_TOKEN": "xoxb-..."}`

**セキュリティ:**
- Lambda実行ロールに最小権限付与
- 自動ローテーション非対応 (手動管理)

### 5. Amazon Route 53

**管理レコード:**
- MXレコード: `10 inbound-smtp.{region}.amazonaws.com` (オプション)
- DKIMレコード: SES Identity検証用 (手動設定)

## 処理フロー

### 通常フロー

1. **メール受信**
   - `channel-name@domain.com`宛にメール送信
   - SESがTLS/スキャンチェック実施

2. **S3保存**
   - SESがメールをS3に保存
   - キー: `ses-emails/{message-id}`

3. **Lambda起動**
   - S3イベント通知でLambda起動
   - メールファイルをS3から取得

4. **メール解析**
   - Toアドレスからチャンネル名抽出
   - MIME形式のメールをパース
   - RFC 2047エンコード済み件名をデコード

5. **Slack通知**
   - Secrets ManagerからBot Token取得
   - Slack APIで指定チャンネルに投稿

### エラーハンドリング

**Slack APIエラー時:**
- エラーをキャッチ
- `SLACK_ERROR_CHANNEL`にエラー内容を通知
- 元のチャンネル名とエラーメッセージを含む

**AWS SESセットアップ通知:**
- 送信元が`no-reply-aws@amazon.com`
- 件名が`Amazon SES Setup Notification`
- → 静かにスキップ (ログのみ出力)

**その他の例外:**
- ログに記録
- Sentryに送信 (設定時)
- Lambda例外として再スロー

## セキュリティ設計

### 最小権限の原則

**Lambda実行ロール:**
```
- S3読み取り: ses-emails/*のみ
- Secrets Manager読み取り: 特定シークレットのみ
- CloudWatch Logs書き込み
- X-Ray書き込み (有効時)
```

### データ保護

1. **転送中の暗号化**
   - SES: TLS強制
   - S3: SSL強制 (バケットポリシー)
   - Secrets Manager: TLS

2. **保管中の暗号化**
   - S3: SSE-S3
   - Secrets Manager: AWS KMS

3. **データ保持**
   - メール: 30日後自動削除
   - アクセスログ: 90日後自動削除

### 監視とトレーシング

**AWS X-Ray (オプション):**
- Lambda実行トレース
- boto3 SDK呼び出し自動トレース
- `get_slack_token()`は除外 (トークン漏洩防止)

**Sentry (オプション):**
- エラー自動キャプチャ
- スタックトレース記録
- アラート通知

**CloudWatch Logs:**
- 構造化ログ (JSON)
- Lambda Powertools Logger使用
- 1週間保持

## スケーラビリティ

### 制約

1. **SESメールサイズ制限**
   - 最大10MB (ヘッダー含む)
   - Base64エンコード後約13MB

2. **Slack APIレート制限**
   - Tier 3: 50+ req/min
   - Lambda同時実行数10で緩和

3. **Lambda同時実行**
   - 予約済み同時実行数: 10
   - 大量メール受信時はキューイング

### 拡張性

**将来的な改善案:**
- SQSキューイング導入
- DynamoDB重複排除
- Step Functions複雑フロー対応
- SNS複数通知先対応

## 運用考慮事項

### デプロイ

**必須手順:**
1. Route 53ホストゾーン作成
2. SES Identity検証 (DKIM設定)
3. Slack Bot Token設定
4. CDKデプロイ
5. SES RuleSet有効化
6. Slack Botチャンネル招待

**オプション手順:**
- SESサンドボックス解除 (本番環境)
- Sentry設定
- X-Ray有効化

### 監視

**推奨メトリクス:**
- Lambda実行エラー率
- Lambda実行時間
- S3バケットサイズ
- Slack API呼び出し失敗率

**アラート設定例:**
- エラー率 > 5% (5分間)
- 連続3回エラー発生

### トラブルシューティング

**メールが届かない:**
1. SES RuleSetが有効か確認
2. MXレコードが正しいか確認
3. SES Identity検証完了確認
4. CloudWatch Logsでエラー確認

**Slack通知が届かない:**
1. Bot Tokenが正しいか確認
2. Botがチャンネルに招待されているか確認
3. チャンネル名が正しいか確認
4. CloudWatch Logsでエラー確認

## コスト見積もり

**月間1,000通のメール受信想定:**

- SES: $0.10 (受信)
- S3: $0.02 (ストレージ) + $0.01 (リクエスト)
- Lambda: $0.20 (実行時間)
- Secrets Manager: $0.40 (シークレット保管)
- Route 53: $0.50 (ホストゾーン)

**合計: 約$1.23/月**

※実際のコストは使用量により変動します
