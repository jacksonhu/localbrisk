# ==========================================
# Agent 核心规范 (BMAD Standard Spec)
# 用于多 Agent 协作架构下的角色定义与动态调度
# ==========================================

# 1. 身份与元数据 (Identity)
# 注意：不需要 ID 字段，Agent 的唯一性由 Catalog 下的目录路径决定
baseinfo:
  name: my_agent
  display_name: My Agent
  description: An AI agent
  tags: []
  owner: admin
  created_at: 2026-01-31T10:00:00
  updated_at: 2026-01-31T10:00:00

# 2. LLM 运行配置 (LLM Config)
llm_config:
  # LLM 模型引用 - 对应你的 Schema 或模型网关中定义的名称
  llm_model: "gpt-4-turbo"
  # 采样参数
  temperature: 0.2
  max_tokens: 2000
  # 响应格式约束
  response_format: "text" # 选项: json_object, text

# 3. 提示词矩阵 (Prompt Matrix)
instruction:
  system_prompt: |
    你是一个精通 Python 和 Plotly 的可视化专家。
    你的职责是接收数据字典并生成符合 PySide6 QWebEngineView 显示要求的 HTML 代码。
  
  user_prompt_template: |
    ### 任务指令
    请针对以下数据进行处理：{input_data}
    视觉约束：{ui_theme_context}

# 4. 动态调度标签 (Routing & Trigger)
routing:
  trigger_keywords: ["绘图", "可视化", "图表"]
  required_context_keys: ["input_data"]
  next_possible_agents: ["supervisor", "human_reviewer"]

# 5. 技能与资源 (Capabilities)
capabilities:
  native_skills:
    - name: "data_cleaner"
  mcp_tools:
    - server_id: "local-file-system"
      tools: ["write_file"]

# 6. 治理与终止 (Governance & Lifecycle)
governance:
  human_in_the_loop:
    trigger: "on_error"
  termination_criteria: |
    1. 输出了标准 HTML 字符串且包含 Plotly 核心逻辑。