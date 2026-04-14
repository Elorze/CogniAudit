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

### 路演 / 录屏：离线确定性剧本（推荐）

- 启动后点击侧栏 **「一键加载离线演示剧本（零 API）」**，会预填一段基于 `对话.md` 精简的「用户↔助手」对话，并在侧栏写入 **固定的两条认知路径节点**（每次完全一致，不调用大模型）。
- 打开页面自动加载（可选其一）：
  - 浏览器访问：`http://localhost:8501/?demo=1`
  - 或环境变量：`COGNIAUDIT_AUTOLOAD_DEMO=1`
- 叙事说明见仓库内 `对话_精简.md`；剧本数据在 `src/cogniaudit/demo_offline.py`。

