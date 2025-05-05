# Agno Streamlit 聊天应用

这是一个使用 Streamlit 构建的前端应用程序，用于与 `agno` AI 代理进行交互。它提供了一个用户友好的界面，允许用户配置不同的 LLM（大型语言模型）提供商、选择模型、管理会话和用户特定的记忆，并利用 `agno` 框架的各种功能。

## ✨ 主要功能

*   **多提供商支持**: 支持 OpenAI (GPT), Google (Gemini), Anthropic (Claude) 模型。
*   **模型选择**: 在侧边栏动态选择可用的模型 ID。
*   **API 密钥管理**: 通过侧边栏输入 API 密钥，或自动从 `.env` 文件加载。
*   **用户和会话管理**: 输入用户 ID 和会话 ID 来区分不同的用户和对话。
*   **灵活的记忆功能**:
    *   **用户记忆**: 允许代理学习和回忆有关特定用户的事实。
    *   **会话历史**: 加载和保存特定会话的聊天记录。
    *   **会话摘要**: 生成和查看当前会话的摘要。
*   **工具使用**: 集成了 DuckDuckGo 搜索工具，允许代理进行网络搜索。
*   **代理定制**: 可以通过 "Prompts" 选项卡设置代理的描述和指令。
*   **调试和查看**: "Memories" 选项卡提供了查看用户记忆、会话存储（历史记录）和会话摘要的界面。

## 🚀 安装指南

1.  **克隆仓库**:
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  **创建并激活虚拟环境** (推荐):
    ```bash
    # Linux/macOS
    python3 -m venv .venv
    source .venv/bin/activate

    # Windows
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

3.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **(可选) 配置 API 密钥**:
    *   创建一个名为 `.env` 的文件在项目根目录下。
    *   根据需要添加以下格式的 API 密钥：
        ```dotenv
        OPENAI_API_KEY=sk-...
        GOOGLE_API_KEY=AIza...
        ANTHROPIC_API_KEY=sk-ant-...
        ```
    *   应用启动时会尝试从 `.env` 文件加载对应提供商的密钥。如果在侧边栏输入了密钥，则会覆盖 `.env` 中的值。

## 🎮 使用方法

1.  **启动应用**:
    ```bash
    streamlit run app/main.py
    ```

2.  **打开浏览器**: 访问终端中显示的本地 URL (通常是 `http://localhost:8501`)。

3.  **配置设置**:
    *   在左侧边栏中，选择 **提供商** (Provider) 和 **模型 ID** (Model ID)。
    *   输入所选提供商的 **API 密钥** (API Key)，除非它已从 `.env` 自动填充。
    *   输入 **用户 ID** (User ID) 以启用用户记忆功能。
    *   输入或接受自动生成的 **会话 ID** (Session ID) 以启用聊天历史和会话摘要。
    *   根据需要切换 **加载历史** (Load History)、**用户记忆** (User Memory) 和 **会话摘要** (Session Summary) 的开关。

4.  **开始聊天**: 在主界面的 **"Chat UI"** 选项卡中，输入消息并与代理互动。

5.  **探索其他选项卡**:
    *   **"Prompts"**: 尝试预设的顺序提示或自定义代理的描述和指令。
    *   **"Memories"**: 查看当前用户 ID 的记忆、当前会话 ID 的历史记录和摘要。

## 📁 项目结构

```
.
├── app/                  # 主要应用代码
│   ├── __init__.py       # 使 app 成为 Python 包
│   ├── main.py           # Streamlit 应用入口、侧边栏、主选项卡逻辑
│   ├── ui.py             # UI 组件函数 (聊天显示、记忆查看等)
│   ├── models.py         # Agent 初始化、模型/记忆/存储设置
│   ├── prompts.py        # 预设提示和代理配置模板
│   └── config.py         # 配置相关 (如从 .env 加载密钥)
├── tmp/                  # 临时文件目录 (包含 SQLite 数据库)
│   └── agent_memory.db   # SQLite 数据库文件 (用于记忆和存储)
├── .venv/                # Python 虚拟环境 (被 .gitignore 忽略)
├── .gitignore            # Git 忽略文件列表
├── requirements.txt      # Python 依赖包列表
├── README.md             # 项目文档 (本文档)
└── TODO.md               # 待办事项和已知问题列表
```

## ⚙️ 配置

*   **应用配置**: 主要通过 Streamlit 应用界面的侧边栏进行：
    *   LLM 提供商和模型
    *   API 密钥
    *   用户 ID 和 会话 ID
    *   记忆功能开关
*   **代理行为**: 通过 "Prompts" 选项卡中的 "Agent Settings" 子选项卡配置：
    *   代理描述 (Description)
    *   代理指令 (Instructions)
*   **环境变量**: API 密钥可以通过项目根目录下的 `.env` 文件预先配置。`app/config.py` 文件中的 `get_optional_key_from_env` 函数负责加载这些变量。支持的环境变量名包括 `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`。

## 🔗 依赖项

*   **Python**: (请根据您的 `requirements.txt` 或环境指定版本，例如 Python 3.9+)
*   **主要库**:
    *   `streamlit`: 用于构建 Web UI。
    *   `agno`: 核心 AI 代理框架。
*   详细列表请参见 `requirements.txt` 文件。

## 🤝 贡献

欢迎提出问题、报告 Bug 或建议新功能！您可以通过项目的 Issue 跟踪系统进行。 (如果项目托管在 GitHub 等平台)

## 📝 注意事项

*   API 密钥存储在 Streamlit 会话状态中，请注意在共享或部署应用时的安全风险。
*   `tmp/` 目录包含数据库文件，确保它有写入权限。
*   某些功能（如用户记忆、历史记录、摘要）需要正确设置用户 ID 和/或会话 ID 才能启用。
