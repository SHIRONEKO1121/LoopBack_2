# LoopBack AI IT Hub - 功能激活与测试指南

这份指南将引导你完成新功能的最后配置环节，并教你如何进行完整的端到端测试。

---

## 🛠️ 第一步：激活 Watsonx AI Agent (配置脑部)

为了让系统能够识别分类并生成“回复”格式，你需要更新 Agent 的配置。

1.  **更新系统提示词 (Instructions)**：
    *   参考项目根目录下的 [AGENT_CATEGORY_CONFIG.md](file:///Users/shironeko/.gemini/antigravity/scratch/ibm-hackathon-2026/AGENT_CATEGORY_CONFIG.md)。
    *   将该文件中的 `## Agent Prompt 模板` 逻辑复制并粘贴到你的 Watsonx Agent 指令界面中。
2.  **配置输出对象 (Response Object)**：
    *   确保 Agent 的 JSON 输出包含以下字段：
        *   `ai_draft`: AI 生成的、语气礼貌的**用户回复**。
        *   `Category`: 具体的分类名称（例如：Network, Hardware, Software, Account, Facility）。

---

## 🧪 第二步：功能测试流程

按照以下步骤验证系统功能是否运行流畅：

### 1. 测试“询问用户” (Clarifying Question) 流程
验证管理员与用户之间的初步对话逻辑。

*   **管理员操作**：在任何票据卡片上，点击蓝色的 **"Ask User"** 按钮（问号图标）。
*   **输入问题**：在弹出的模态框中输入一个问题，点击 **"Send Question"**。
*   **检查结果**：
    *   票据卡片应立即显示橙色的 **"Awaiting Info"** 状态标签。
    *   卡片底部应出现 **"Conversation History"** 区域，并显示你刚刚发送的问题。

### 2. 测试“用户回复”后的自动状态转换
验证当用户提供新信息时，系统是否能自动感知并处理。

*   **模拟测试**：通过 Agent 界面再次发送相同的用户问题（模拟用户补充细节）。
*   **检查结果**：
    *   之前标记为 "Awaiting Info" 的票据应自动变回 **"Pending"** 状态。
    *   卡片的对话历史记录中应增加一条新的 **User** 消息。
    *   后端日志应显示：`DEBUG: 🔄 Pushing Group TKT-XXXX back to Pending (User replied)`。

### 3. 测试“批量回复”与动态计数
验证卡片选择逻辑与广播功能的联动。

*   **仪表盘操作**：手动点击多个票据卡片进行选中。
*   **观察计数**：顶部的绿色按钮应动态更新为 **"Broadcast Selected (X)"**，其中 X 是你选中的数量。
*   **模态框验证**：点击该按钮，确保弹出的窗口中仅列出了你选中的那几个票据。
*   **发送回复**：输入解决方案并发送，验证是否有自定义的成功通知弹出。

---

## 🔍 第三步：后端日志检查 (调试)

如果你发现分类或分组没有生效，请查看运行 `server.py` 的终端，重点关注以下调试信息：

*   `DEBUG: 📂 Ticket has category: Network` (分类识别)
*   `DEBUG: 🔗 Category match! Grouped with TKT-XXXX` (智能分组)
*   `DEBUG: ✅ Question sent for TKT-XXXX` (询问逻辑)

---

💡 **提示**：完整的视觉效果演示可以参考 [walkthrough.md](file:///Users/shironeko/.gemini/antigravity/brain/b7d8bb33-b5e1-4b32-9293-79a0125244e0/walkthrough.md)。
