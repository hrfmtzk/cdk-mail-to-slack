# コーディング規約

## 概要

このプロジェクトでは、コードの品質と保守性を保つため、以下の規約とツールを使用します。

## Python コーディング規約

### 基本方針

- **PEP 8準拠**: Pythonの標準スタイルガイドに従う
- **型ヒント必須**: すべての関数に型アノテーションを付ける
- **docstring推奨**: 公開関数にはdocstringを記述

### コードフォーマット

#### Black

**設定 (`pyproject.toml`):**
```toml
[tool.black]
line-length = 88
target-version = ['py314']
exclude = '''
/(
    \.git
  | \.venv
  | cdk\.out
  | \.cdk\.staging
)/
'''
```

**実行:**
```bash
black .
```

#### isort

**設定 (`pyproject.toml`):**
```toml
[tool.isort]
profile = "black"
line_length = 88
combine_as_imports = true
pythonpath = ["source/email_handler"]
skip_gitignore = true
```

**実行:**
```bash
isort .
```

### リンター

#### flake8

**設定 (`pyproject.toml`):**
```toml
[tool.flake8]
max-line-length = 88
extend-ignore = ["E203", "W503"]
exclude = [
    ".git",
    ".venv",
    "cdk.out",
    ".cdk.staging",
]
```

**実行:**
```bash
flake8
```

#### mypy

**設定 (`pyproject.toml`):**
```toml
[tool.mypy]
python_version = "3.14"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
exclude = [
    "cdk.out",
    ".cdk.staging",
]
```

**実行:**
```bash
mypy .
```

## テスト規約

### テストカバレッジ

**目標: 80%以上**

**設定 (`pyproject.toml`):**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["source/email_handler"]
addopts = "--cov --cov-report=html --cov-report=term --cov-fail-under=80"
```

**実行:**
```bash
pytest
pytest --cov  # カバレッジレポート付き
```

### テストの種類

#### 1. ユニットテスト

**場所:** `tests/unit/`

**対象:**
- Lambda関数のビジネスロジック
- CDKスタックのリソース構成

**モック:**
- AWS SDK呼び出し (`boto3`)
- Slack SDK呼び出し
- 環境変数

**例:**
```python
@patch("main.s3_client")
@patch("main.secrets_client")
@patch("main.WebClient")
def test_handler_success(
    mock_webclient: MagicMock,
    mock_secrets: MagicMock,
    mock_s3: MagicMock,
    s3_event: dict[str, Any],
    sample_email: bytes,
    lambda_context: MagicMock,
) -> None:
    # テストロジック
    pass
```

#### 2. スナップショットテスト

**場所:** `tests/snapshot/`

**対象:**
- CDKスタックのCloudFormationテンプレート

**目的:**
- 意図しないインフラ変更の検出

#### 3. 統合テスト

**現状:** 手動実施

**将来的な自動化検討項目:**
- 実際のメール送信
- Slack通知確認
- E2Eフロー検証

### テスト命名規則

```python
def test_<対象>_<条件>_<期待結果>():
    pass

# 例:
def test_handler_success()
def test_handler_slack_error_fallback()
def test_extract_channel_invalid_format()
```

## CDK コーディング規約

### リソース命名

**プレフィックス:** `MailSlack`

**例:**
```python
s3.Bucket(self, "MailSlackS3Bucket", ...)
lambda_.Function(self, "MailSlackLambdaFunction", ...)
```

### CDK Nag対応

**必須:** すべてのセキュリティ警告に対応

**抑制時の要件:**
- 明確な理由を記述
- `applies_to`で対象を限定

**例:**
```python
NagSuppressions.add_resource_suppressions(
    resource,
    [
        NagPackSuppression(
            id="AwsSolutions-IAM5",
            reason="Wildcard permissions are required for X-Ray tracing",
            applies_to=["Resource::*"],
        ),
    ],
)
```

### 設定の外部化

**必須:** 環境固有の値は`config.py`で管理

**禁止:** ハードコードされた値

**例:**
```python
# Good
domain_name = config.DOMAIN_NAME

# Bad
domain_name = "example.com"
```

## Lambda コーディング規約

### AWS Lambda Powertools使用

**必須ツール:**
- `Logger`: 構造化ログ
- `Tracer`: X-Rayトレーシング

**推奨パターン:**
```python
from aws_lambda_powertools import Logger, Tracer

logger = Logger()
tracer = Tracer()

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    logger.info("Processing event", extra={"event": event})
    # 処理
    return {"statusCode": 200}

@tracer.capture_method
def some_function():
    # X-Rayでトレースされる
    pass
```

### エラーハンドリング

**原則:**
1. 予期されるエラーは適切にキャッチ
2. 予期しないエラーは再スロー
3. すべてのエラーをログに記録

**例:**
```python
try:
    # メイン処理
    post_to_slack(client, channel, from_addr, subject, body)
except SlackApiError as e:
    # 予期されるエラー: フォールバック処理
    logger.error(f"Slack API error: {e.response['error']}")
    post_error_to_slack(client, error_channel, channel, e.response["error"])
except Exception:
    # 予期しないエラー: ログ記録して再スロー
    logger.exception("Unexpected error")
    raise
```

### セキュリティ考慮事項

**禁止事項:**
1. シークレットのログ出力
2. X-Rayトレースへのシークレット含有
3. 環境変数への直接的なシークレット設定

**推奨:**
```python
# Good: Secrets Managerから取得
def get_slack_token() -> str:
    """Get Slack bot token from Secrets Manager.
    
    Note: Not traced with @tracer.capture_method to avoid exposing
    the token in X-Ray traces.
    """
    secret_name = os.environ["SLACK_BOT_TOKEN_SECRET_NAME"]
    response = secrets_client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response["SecretString"])
    return str(secret["SLACK_BOT_TOKEN"])

# Bad: 環境変数から直接取得
token = os.environ["SLACK_BOT_TOKEN"]  # NG
```

## Git規約

### コミットメッセージ

**フォーマット:**
```
<type>: <subject>

<body>
```

**Type:**
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント
- `style`: フォーマット
- `refactor`: リファクタリング
- `test`: テスト追加/修正
- `chore`: ビルド/ツール変更

**例:**
```
feat: Add Sentry error tracking support

- Add SENTRY_DSN configuration parameter
- Initialize Sentry SDK in Lambda handler
- Add unit tests for Sentry initialization
```

### ブランチ戦略

**推奨:** GitHub Flow

- `main`: 本番環境
- `feature/*`: 機能開発
- `fix/*`: バグ修正

### .gitignore

**必須除外:**
- `config.py`: 環境固有設定
- `cdk.context.json`: AWSアカウント情報
- `.venv/`: 仮想環境
- `cdk.out/`: CDK生成物
- `*.pyc`, `__pycache__/`: Pythonキャッシュ

## CI/CD推奨設定

### GitHub Actions例

```yaml
name: Test and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.14'
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: black --check .
      - run: isort --check .
      - run: flake8
      - run: mypy .
      - run: pytest
      - run: cdk synth
```

## VSCode設定

**プロジェクト共通設定 (`.vscode/settings.json`):**
```json
{
  "python.analysis.diagnosticSeverityOverrides": {
    "reportArgumentType": "none"
  }
}
```

**理由:** CDK JSII生成型定義のPylance警告を抑制

## レビュー基準

### プルリクエスト要件

**必須:**
- [ ] すべてのテストが通過
- [ ] カバレッジ80%以上維持
- [ ] リンター/フォーマッターエラーなし
- [ ] CDK Nag警告に対応
- [ ] 適切なコミットメッセージ

**推奨:**
- [ ] 変更内容の説明
- [ ] スクリーンショット (UI変更時)
- [ ] 破壊的変更の明記

### コードレビューポイント

1. **セキュリティ**
   - シークレット漏洩なし
   - 最小権限の原則
   - 入力検証

2. **パフォーマンス**
   - 不要なAPI呼び出しなし
   - 適切なエラーハンドリング
   - リソース制限考慮

3. **保守性**
   - 適切な命名
   - コメント/docstring
   - テストカバレッジ

4. **ベストプラクティス**
   - DRY原則
   - SOLID原則
   - AWS Well-Architected Framework
