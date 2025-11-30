# CDK Mail to Slack

AWS CDK (Python) を使用して、Amazon SES で受信した Email を Amazon S3 に保存し、それをトリガーに AWS Lambda が Slack へ通知を行うシステムです。

詳細な設計ドキュメントは [docs/README_ja.md](docs/README_ja.md) を参照してください。

**English Version:** [README.md](README.md)

## プロジェクト構成

```
cdk-mail-to-slack/
├── app.py                      # CDK App のエントリーポイント
├── config.py                   # 環境設定ファイル (gitignore対象)
├── config.py.example           # 設定ファイルのテンプレート
├── cdk.context.json            # CDK コンテキストキャッシュ (gitignore対象)
├── cdk_mail_to_slack/          # CDK スタック定義
│   └── cdk_mail_to_slack_stack.py
├── source/
│   └── email_handler/          # Lambda 関数
│       ├── main.py
│       └── requirements.txt
├── tests/                      # テストコード
│   ├── unit/
│   └── snapshot/
└── .vscode/                    # VSCode設定 (プロジェクト共通)
    └── settings.json           # CDK型チェック抑制など
```

## セットアップ

### 1. 仮想環境の作成と依存関係のインストール

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### 2. 設定ファイルの作成

```bash
cp config.py.example config.py
```

`config.py` を編集して、以下の値を設定してください:

**必須設定:**
- `DOMAIN_NAME`: メール受信用のドメイン名
- `HOSTED_ZONE_NAME`: Route 53 のホストゾーン名
- `SLACK_ERROR_CHANNEL`: エラー通知用の Slack チャンネル名
- `CREATE_MX_RECORD`: MXレコードを自動作成するか（True/False）
  - `True`: CDKがRoute 53にMXレコードを自動作成
  - `False`: MXレコードが既に存在する場合や外部で管理する場合
- `USE_EXISTING_RULE_SET`: 既存のSESルールセットを使用するか（True/False）
  - `True`: 既存のルールセットにルールを追加
  - `False`: 新しいルールセットを作成

**オプション設定:**
- `EXISTING_RULE_SET_NAME`: 既存ルールセット名（`USE_EXISTING_RULE_SET=True`の場合に必須）
- `INSERT_AFTER_RULE`: ルールを挿入する位置（既存ルール名を指定、未指定の場合は先頭に追加）
- `ENABLE_XRAY_TRACING`: AWS X-Rayトレーシングを有効化（デフォルト: True）
- `SENTRY_DSN`: Sentryエラートラッキング用DSN（未指定の場合はSentry無効）

### 3. Slack Bot の作成とトークンの準備

#### 3.1. Slack Appの作成

1. [Slack API](https://api.slack.com/apps) にアクセス
2. "Create New App" をクリック
3. "From scratch" を選択
4. App Name（例: `Mail Notifier`）とワークスペースを選択して作成

#### 3.2. Bot Token Scopesの設定

1. 左メニューから "OAuth & Permissions" を選択
2. "Scopes" セクションの "Bot Token Scopes" で以下を追加:
   - `chat:write` - メッセージをポストする権限

#### 3.3. Appのインストール

1. "OAuth & Permissions" ページ上部の "Install to Workspace" をクリック
2. 権限を確認して "Allow" をクリック
3. "Bot User OAuth Token" (`xoxb-` で始まる文字列) をコピー

### 4. Sentry の設定（オプション）

エラートラッキングにSentryを使用する場合:

1. [Sentry](https://sentry.io/) でアカウントを作成（無料プランあり）
2. 新しいプロジェクトを作成（Platform: Python）
3. DSN（Data Source Name）をコピー
4. `config.py`に`SENTRY_DSN`を設定:
   ```python
   SENTRY_DSN = "https://your-key@sentry.io/your-project-id"
   ```

Sentryを使用しない場合は、`config.py`で`SENTRY_DSN`を未定義のままにしてください。

### 5. テストの実行

```bash
pytest
```

### 6. デプロイ

```bash
# 初回のみ
cdk bootstrap

# スタックのデプロイ
cdk deploy
```

## デプロイ後の手動セットアップ

CDKでは管理されない、手動で作成・設定が必要なリソースがあります。

### 1. Slack Bot Tokenの更新

**必要な理由:** CDKで作成されたSecretにはプレースホルダー値が設定されているため

**更新方法:**

AWS CLIで更新:
```bash
aws secretsmanager update-secret \
  --secret-id MailSlack/SlackBotToken \
  --secret-string '{"SLACK_BOT_TOKEN":"xoxb-your-actual-token-here"}'
```

または、AWSコンソールから:
1. AWS Secrets Manager > Secrets > `MailSlack/SlackBotToken`
2. "Retrieve secret value" をクリック
3. "Edit" をクリック
4. `SLACK_BOT_TOKEN` の値を実際のBot Tokenに更新
5. "Save" をクリック

### 2. Route 53 ホストゾーン

**必要な理由:** SESでメールを受信するドメインのDNS管理に必要

**作成方法:**
```bash
# AWS CLIで作成する場合
aws route53 create-hosted-zone \
  --name example.com \
  --caller-reference $(date +%s)
```

または、AWSコンソールから:
1. Route 53 > ホストゾーン > ホストゾーンの作成
2. ドメイン名を入力（例: `example.com`）
3. タイプ: パブリックホストゾーン

**注意:** ドメインレジストラでネームサーバーをRoute 53のNSレコードに変更する必要があります

### 3. SES Email Identity（ドメイン検証）

**必要な理由:** SESでメールを受信するためにドメインの所有権を証明

**作成方法:**

AWSコンソールから:
1. Amazon SES > Identities > Create identity
2. Identity type: Domain
3. Domain: `example.com`（`config.py`の`DOMAIN_NAME`と同じ）
4. DKIM signatures: Enabled（デフォルト）
5. 表示されるDKIMのCNAMEレコード（3つ）をRoute 53に追加

**必要なDNSレコード:**
- DKIMレコード: 3つのCNAMEレコード（ドメイン検証とメール認証に使用）
- MXレコード: `10 inbound-smtp.{region}.amazonaws.com`（`CREATE_MX_RECORD=True`の場合は自動作成）

**注意:** DKIMレコードの追加後、検証完了まで最大72時間かかる場合があります

### 4. SES Receipt Rule Setの有効化

**必要な理由:** CDKで作成したルールセットはデフォルトでは無効

**設定方法:**
```bash
# AWS CLIで有効化
aws ses set-active-receipt-rule-set \
  --rule-set-name MailSlackRuleSet
```

または、AWSコンソールから:
1. Amazon SES > Email receiving > Rule sets
2. `MailSlackRuleSet` を選択
3. "Set as active" をクリック

### 5. SESサンドボックスの解除（本番環境）

**必要な理由:** サンドボックス環境では検証済みメールアドレスからのみ受信可能

**申請方法:**
1. Amazon SES > Account dashboard
2. "Request production access" をクリック
3. 使用目的などを記入して申請

**注意:** 承認には通常1営業日程度かかります

### 6. Slack Botのチャンネル招待

**必要な理由:** Botがメッセージをポストするにはチャンネルのメンバーである必要がある

**設定方法:**
1. 通知先のSlackチャンネルを開く
2. `/invite @your-bot-name` を実行
3. エラー通知用チャンネル（`config.py`の`SLACK_ERROR_CHANNEL`）にも同様に招待

## 利用方法

### メール送信によるSlack通知

このシステムは、メールアドレスの**ローカル部分**（@より前）をSlackチャンネル名として解釈します。

#### 基本的な使い方

**メールアドレスの形式:**
```
<チャンネル名>@<DOMAIN_NAME>
```

**例:**
- `config.py`で`DOMAIN_NAME = "mail.example.com"`と設定している場合
- `general@mail.example.com`にメールを送信 → `#general`チャンネルに通知
- `dev-team@mail.example.com`にメールを送信 → `#dev-team`チャンネルに通知
- `random@mail.example.com`にメールを送信 → `#random`チャンネルに通知

#### 通知内容

Slackに投稿されるメッセージには以下の情報が含まれます:
- 送信者（From）
- 件名（Subject）
- メール本文

#### エラー時の動作

以下の場合、`config.py`で設定した`SLACK_ERROR_CHANNEL`にエラー通知が送信されます:
- 指定されたチャンネルが存在しない
- Botがチャンネルに招待されていない
- Slack APIでエラーが発生した

#### 注意事項

- チャンネル名に`#`は不要です（自動的に付与されます）
- Botを事前にチャンネルに招待しておく必要があります
- プライベートチャンネルの場合も、Botの招待が必要です

## 開発

### VSCode設定

`.vscode/settings.json`にプロジェクト共通の設定が含まれています:
- AWS CDKのJSII生成型定義に関するPylance警告の抑制
- これらの警告は実行時に影響せず、CDKの既知の問題です

### コードフォーマット

```bash
black .
isort .
```

### リンター

```bash
flake8
mypy .
```

### テストカバレッジ

```bash
pytest --cov
```

## アーキテクチャ

詳細なシステム設計については、[docs/design_ja.md](docs/design_ja.md)を参照してください。

**主要コンポーネント:**
- Amazon SES: メール受信
- Amazon S3: メール保存
- AWS Lambda: メール処理とSlack通知
- AWS Secrets Manager: Slack Bot Token保管
- Amazon Route 53: DNS管理

## セキュリティ

- **TLS強制**: SESは暗号化されていない接続を拒否
- **スパム/ウイルススキャン**: 悪意のあるメールを自動ブロック
- **最小権限**: Lambda実行ロールは必要最小限の権限のみ
- **シークレット管理**: SlackトークンはSecrets Managerに保管
- **データ保持**: メールは30日後に自動削除

## 監視

- **CloudWatch Logs**: Lambda実行ログ（1週間保持）
- **X-Ray トレーシング**: 実行フローの可視化（オプション）
- **Sentry**: エラートラッキングとアラート（オプション）

## コスト

月間1,000通のメール受信を想定した推定コスト:
- SES: $0.10
- S3: $0.03
- Lambda: $0.20
- Secrets Manager: $0.40
- Route 53: $0.50

**合計: 約$1.23/月**

*実際のコストは使用量により変動します

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## コントリビューション

プルリクエストを歓迎します。大きな変更の場合は、まずIssueを開いて変更内容を議論してください。
