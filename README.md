## CogniAudit

非侵入式人机对话认知漂移监测 Demo：**语义嵌入 + River ADWIN + 轻量微审计**，Streamlit 前端，Gemini API（见 `核心.md` 规约）。

### 运行

1. 复制 `.env.example` 为 `.env`，填入 `GEMINI_API_KEY`（勿提交 `.env`）。

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

可选：无 Key 时用 Fake 嵌入/回复做本地冒烟：`COGNIAUDIT_USE_FAKE=1 streamlit run app.py`。

### 技术栈

Python 3.10+、`google-generativeai`、`river`、`streamlit`、`pydantic`、`numpy` 等（见 `requirements.txt`）。
