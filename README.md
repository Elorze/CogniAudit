## CogniAudit Demo

本目录是 `CogniAudit` 的最小可运行 Demo（Streamlit + Gemini + ADWIN）。

### 运行

1. 准备环境变量

- 在本目录下放置 `.env`：
  - `GEMINI_API_KEY=...`
- 你也可以参考 `.env.example`（不要把真实 Key 写进仓库/聊天里）。

2. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. 启动

```bash
streamlit run app.py
```

### 测试

```bash
pytest -q
COGNIAUDIT_USE_FAKE=1 PYTHONPATH=src python scripts/selfcheck.py
```

说明：

- `pytest` 与 `selfcheck` 默认走 **Fake 模式**（不消耗 API 额度）。
- 若你在某些受限沙盒环境里运行 Python，可能会遇到 `numpy` 导入异常；在本机终端正常运行一般没问题。

