# N09 — 蒸馏路线被拒：学生拿到了教师的文本，没拿到教师的环境

## 1. 这里发生了什么

用 dots3 的 H_D 轨迹训练 Qwen3-0.6B（20 步 LoRA SFT，3 个去污染视图），
然后在**裸 H_A** 下评估：未训练 0/10 tool calls、0/10 resolve；
SFT 后依然 **0/10 tool calls、0/10 resolve**。
学生模型完全没有学会「调用工具」这个行为——更不用说把 H_D 的收益带走。

## 2. 为什么走到这里

N05/N06 证明 harness 有效。自然的下一步：把 harness 产生的轨迹蒸馏成
一个更小可部署的策略（D04 曾把 Phase 4 定义为 trajectory distillation，
D10 冻结为「current route rejected」后做一次小规模验证——D09）。

## 3. 这里真正的问题

- Q1: 0.6B 学生能从老师的轨迹里学会工具调用吗？
- Q2: 如果学不会，是「容量/步数/格式对齐」哪个环节断了？

## 4. 我原来怎么想

以为轨迹里已经有「正确的行为示范」，SFT 应该至少能让学生模仿出
调用工具的样子。

## 5. 我做了什么

- 3 个 contamination-free SFT view（`training_view.py`）。
- dots3 D_D teacher → Qwen3-0.6B，20 步 LoRA。
- eval 用裸 H_A（不注入提示），避免把 harness 本身也算进效果。
- 对比 untrained vs SFT 的 tool calls / resolve。

## 6. 得到了什么

大白话：**把「好学生写的作业」给一个更小的学生抄，小学生的工具还没学会拿
（0/10 连工具都不会调），谈不抄不抄行为。这一条蒸馏路线不通。**

## 7. 这改变了什么理解

原来：轨迹 = 完整的 capability transfer unit（把文本给够就行）。
现在：**被拒（route-specific）。** 轨迹本身不是传输单元；工具调用的
格式对齐是硬前提，这条路没做。结论被严格限定为
「dots3→0.6B、20 步、无工具格式对齐、H_A eval」这一条路被拒——
**不是「蒸馏不可能」**。

## 8. 证据

- 实验记录：`../../02_experiments/E05_real_swe.md`（蒸馏段）
- commit：`1df2989df`；writeup：`tools/swe_lab/runs/swe_distill_verify.md`
- code：`training_view.py`, `export_pi.py`, `merge_adapter.py`
- 结论行：`../../00_index/hypothesis_ledger.md` H07（route rejected）；
  matrix C10（refuted for this route）

## 9. 专业术语

- distillation：我的理解——用大模型的输出训练小模型；
  本项目含义——dots3→0.6B LoRA，试图转移 harness 行为。
- tool-format alignment：我的理解——让模型先学会输出工具调用语法；
  本项目含义——没做，是路线被拒的可能原因之一。
- trajectory：我的理解——一次 episode 的完整动作记录；
  本项目含义——被证明**不是**完整的 capability transfer unit。

## 10. 可迁移的东西

「教行为先教格式」：如果学生模型连动作语法都没掌握，示范再多也是白给。
任何「模仿学习 + 小模型」都要先确认 action/format 这一层通了
再谈策略迁移。还提醒一条：**负结果要精确限定范围**——一条路被拒 ≠ 问题死亡。

## 11. 还不知道什么

- known：0/10 tool calls（SFT 前后）；0/10 resolve。
- inferred：工具格式对齐可能是断点；但未被隔离验证。
- open：会调用工具的学生（格式已对齐）能否学会 harness 行为？——未测。

## 12. 相关节点

N05 → 蒸馏动机 → N09（被拒）→ N16（三层模型里的边界）；
D10/D04 决策记录。