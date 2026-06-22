# C语言每日一题

> 本插件由 E33EPUS 使用 Claude Code 辅助开发

MaiBot 插件 — C语言程序阅读题，AI出题 + 题库兜底，不限制做题次数。

## 指令

| 指令 | 说明 |
|------|------|
| `/每日一题` | 获取一道C语言阅读题 |
| `/再来一题` | 换一道新题 |
| `/答 <答案>` | 提交你的答案 |
| `/答案` | 查看正确答案和解析 |
| `/题解` | 查看详细题解 |

## 特性

- **LLM生成题目**：优先用 AI 生成新题，参考 LeetCode/牛客网/PTA 风格
- **题库兜底**：LLM 不可用时自动切换到内置题库（43+ 题）
- **知识点覆盖**：运算符优先级、指针、位运算、static、宏、sizeof、类型转换、内存管理、递归、结构体对齐、未定义行为等
- **群组隔离**：每个群的题目独立，互不干扰

## 配置

在 MaiBot WebUI → 插件管理 → C语言每日一题 中调整：

- `llm_first`：是否优先用 LLM 生成（默认开）
- `reveal_on_wrong`：答错后是否立即揭示答案（默认关）

## 安装

MaiBot 插件市场搜索 `c-daily-problem` 一键安装。

或手动安装：

```bash
git clone https://github.com/E33EPUS/c-daily-problem.git plugins/c-daily-problem
```

## 依赖

- MaiBot >= 1.0.0
- MaiBot SDK >= 2.0.0

## 许可

GPL-3.0-or-later
