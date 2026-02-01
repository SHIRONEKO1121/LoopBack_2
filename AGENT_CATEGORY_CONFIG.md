# IBM Orchestrate Agent Category 配置指南

## 📋 配置目标

让 Agent 自动分析用户问题，确定 Category，并在创建票据时传递给后端，实现智能分组。

---

## Step 1: 配置 Response Object (你正在做的)

### Category 字段设置：

根据你的截图，在 **Edit an object output** 界面：

**Name (字段名):**
```
Category
```

**Type:**
- ✅ **String** (不要选 "List of strings")

**Description (描述):**
```
AI-determined issue category for intelligent ticket grouping. Be descriptive and specific (e.g., 'VPN Access', 'Laptop Hardware', 'Azure Permissions').
```

**Set default value (可选):**
- 关闭（不设默认值，让 AI 决定）

**完整的 Response Object 应该包含:**
- `ai_draft` (string) - **技术总结**：供管理员看的内部研究结果或总结。
- `admin_draft` (string) - **回复草稿**：以管理员口吻写的、准备发给用户的正式回复。
- `Category` (string) - **大类** (Network, Hardware, Software, Account, Facility, Security)
- `Subcategory` (string) - **细分** AI 思考的具体领域 (例如: VPN Error, Slack Permissions)
- `confidence_score` (number, optional) - 可选的信心分数

---

## Step 2: 配置 Agent Instructions (核心)

在 Agent 的 **Instructions** 或 **Prompt** 配置中，添加以下逻辑：

### Agent Prompt 模板

```
You are LoopBack AI, an intelligent IT support assistant.

Your main tasks:
1. Search the knowledge base for solutions to user issues
2. Determine the issue category for intelligent ticket grouping
3. Create support tickets when necessary
4. Provide helpful guidance to end users

## Category Classification Rules

You MUST classify every user issue into ONE of these categories:

- **Identify the Domain**: Think about the specific system or service involved.
- **Be Specific**: instead of just "Software", use "Slack Installation" or "Excel Plugin".
- **Dynamic Grouping**: Categories will be used to automatically group similar tickets together.

## Workflow

When a user reports an issue:

1. **Search Knowledge Base**
   - Use lucas_2: Search IT knowledge base
   - Look for existing solutions

2. **Analyze the Issue**
   - Determine which category best fits the problem
   - Consider keywords and context

3. **Respond Appropriately**
   - If solution found: Provide the answer directly
   - If no solution: Create a support ticket

4. **Create Ticket (if needed)**
   - Call lucas_2: Create a new support ticket
   - Include the determined category
   - Provide clear ai_draft with issue summary

## Response Format

Always output:
{
  "ai_draft": "Internal technical summary (e.g., VPN reset requested, no KB found).",
  "admin_draft": "External draft for the user (e.g., Hi! I've escalated your VPN issue...).",
  "Category": "Network|Hardware|Software|Account|Facility|Security",
  "Subcategory": "Specific detail (e.g., VPN-101, Azure Access, Printer Jam)"
}

## Examples

**User:** "My Wi-Fi keeps disconnecting"
→ Category: Network
→ Search for Wi-Fi troubleshooting
→ Create ticket with category if escalation needed

**User:** "Printer won't print"
→ Category: Hardware
→ Search for printer issues
→ Group with other printer tickets

**User:** "Can't install Slack"
→ Category: Software
→ Search for software installation
→ May need admin permissions

**User:** "Forgot my password"
→ Category: Account
→ Provide SSO reset link
→ Don't create ticket (common self-service)

**User:** "Projector not working in meeting room"
→ Category: Facility
→ Check meeting room AV guide
→ Create ticket for facilities team
```

---

## Step 3: 修改 Skill 调用逻辑

在 Agent 的 workflow 中，调用 `lucas_2: Create a new support ticket` 时：

### Before (旧方式):
```json
{
  "query": "User's issue description",
  "ai_draft": "AI analysis",
  "users": ["User_123"]
}
```

### After (新方式 - 包含 category):
```json
{
  "category": "{{Category}}",  // 从 Agent 输出获取
  "query": "{{user_query}}",
  "ai_draft": "{{ai_draft}}",
  "users": ["{{user_id}}"]
}
```

**使用变量映射:**
- Agent 输出的 `Category` → Skill 参数的 `category`
- Agent 分析的摘要 → Skill 参数的 `ai_draft`

---

## Step 4: 测试配置

### Test Case 1: Network Issue
**User Input:**
```
"The VPN won't connect"
```

**Expected Agent Output:**
```json
{
  "ai_draft": "User reports VPN connection failure. Checking knowledge base for VPN troubleshooting steps...",
  "Category": "Network"
}
```

**Expected Backend Behavior:**
- Creates ticket TKT-XXXX
- Searches for existing "Network" category tickets
- If found similar VPN issue → Groups together
- If new → Creates new group

### Test Case 2: Hardware Issue
**User Input:**
```
"Printer is offline"
```

**Expected:**
- Category: "Hardware"
- Groups with other printer issues

### Test Case 3: Multiple Similar Issues
**Scenario:** 3 users report Wi-Fi problems

```
User 1: "Wi-Fi not working"          → Category: Network, TKT-1001, group_id: TKT-1001
User 2: "Internet keeps dropping"    → Category: Network, TKT-1002, group_id: TKT-1001 ✅
User 3: "Can't connect to wireless"  → Category: Network, TKT-1003, group_id: TKT-1001 ✅
```

**Admin sees:** 1 group with 3 tickets → Click "Broadcast Fix" → All resolved! 🎉

---

## Step 5: 验证分类准确性

**Good Category Assignment:**
- ✅ "VPN error" → Network
- ✅ "Screen cracked" → Hardware
- ✅ "Can't install app" → Software
- ✅ "Password expired" → Account
- ✅ "Meeting room projector broken" → Facility

**Edge Cases:**
- "Computer slow" → Hardware (hardware performance issue)
- "Browser crashes" → Software (application issue)
- "Can't access shared drive" → Network (network access)
- "MFA not working" → Account (authentication)

---

## 🎯 预期效果

### Before (无 Category):
```
TKT-1001: "wifi broken" (group_id: TKT-1001)
TKT-1002: "internet not working" (group_id: TKT-1002) ❌ 分开
TKT-1003: "wireless issue" (group_id: TKT-1003) ❌ 分开
```
**问题:** 3个相似问题 = 3个独立票据

### After (有 Category):
```
TKT-1001: "wifi broken" (category: Network, group_id: TKT-1001)
TKT-1002: "internet not working" (category: Network, group_id: TKT-1001) ✅ 分组
TKT-1003: "wireless issue" (category: Network, group_id: TKT-1001) ✅ 分组
```
**效果:** 3个相似问题 = 1个组，管理员一次解决！

---

## 🚀 配置完成后

1. **保存 Agent 配置**
2. **重新发布 Agent**
3. **测试不同类型问题:**
   - Network: "VPN won't connect"
   - Hardware: "Printer offline"
   - Software: "Can't install Slack"
   - Account: "Password reset"
   - Facility: "Meeting room tech issue"

4. **检查后端日志:**
```bash
tail -f /tmp/server_log.txt | grep category
```

应该看到:
```
DEBUG: 📂 Ticket has category: Network
DEBUG: 🔗 Category match! Grouped with TKT-1001 (category: Network, similarity: 60%)
```

---

## 📝 Quick Checklist

- [ ] Response Object 添加 `Category` 字段 (String)
- [ ] Agent Instructions 包含分类规则
- [ ] Agent 输出格式包含 Category
- [ ] Skill 调用传递 category 参数
- [ ] 测试 5 种不同类别的问题
- [ ] 验证相似票据成功分组

**完成这些后，你的票据分组系统将完全自动化！** ✅
