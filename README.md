# Human_Relations_CRM
人物管理システム。ゆくゆくは性格診断、人相診断、適性診断と組み合わせてmanagementの最適化を図る。

# 🏗️ Setup Guide (環境構築手順)

このアプリを新しいPCや環境で動かすための手順書です。

## 1. Pythonのインストール
PythonがPCに入っていない場合は、公式サイトからインストールしてください。
- 推奨バージョン: Python 3.10 以上
- 注意点: インストール時に **"Add Python to PATH"** にチェックを入れること。

## 2. プロジェクトの準備
コマンドプロンプト（またはターミナル）を開き、以下の手順を実行します。

### ① 仮想環境の作成（推奨）
プロジェクトフォルダ内で、専用の部屋（仮想環境）を作ります。
```bash
# Windowsの場合
python -m venv .venv

# 仮想環境を有効化（左端に (.venv) と出れば成功）
.venv\Scripts\activate
```

### ② ライブラリのインストール
必要なツール（ライブラリ）を一括でインストールします。
```bash
pip install -r requirements.txt
```

## 3. アプリの起動
以下のコマンドでアプリを立ち上げます。
```bash
streamlit run app.py
```
