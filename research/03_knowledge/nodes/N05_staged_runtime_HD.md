# N05 — 分阶段运行时 H_D：效果显著，但「planner」框架撤回

## 1. 这里发生了什么

在 lab（工具集 + 预算都定了）上做了一个分阶段运行时 harness：把一次
修复任务拆成侦察（recon）→ 执行（execute）→ 反馈（feedback）三段，
每段注入阶段提示。效果显著（tier3 上 H_D 明显高于 H_A）。但随后挖了
120 个 episode 的 trace，发现：**planner 回合里真正写下计划的是 0/120。**
「这是一个 plan/execute 架构」的说法被自己的 trace 数据推翻，
改名成：staged action allocation（有阶段的动作分配）。然后 H_F attribution
控制显示：增益主要来自阶段提示本身，gate（门控）只帮了 tier4。

## 2. 为什么走到这里

N04 证明工具存在与否影响结果，但留下一个矛盾：工具都在，为什么
H_A 还是乱用？怀疑**动作的时间表**才是杠杆——同样是能 edit，
什么时候(拿到 edit 的机会)不一样。

## 3. 这里真正的问题

- Q1: 分阶段运行时（同一模型、同一工具、同一预算）会不会改变结果？
- Q2: 如果会，是因为它更接近「planner/executor 架构」吗？
- Q3: 是阶段提示（text）在起作用，还是工具门控（gate）在起作用？

## 4. 我原来怎么想

以为 H_D 的成功可以理解为「一个更好的计划-执行架构」：
先规划、再执行、再检查，是经典 agent 设计。

## 5. 我做了什么

- 实现 H_D（SWE_LAB_PHASES="1,2,"—— reconnaissance 阶段禁用 edit）。
- 在 tier3 上对比 H_A/H_D/H_E（H_E 是 H_D 的消融）。
- **120 episodes trace 审计：planner 回合 write 计划 = 0/120。**
- H_F 归因控制：只留阶段提示（去掉 gate），或只留 gate（去掉提示）。
- 命名修正：`7cdbc5980` retire 'planner' framing。

## 6. 得到了什么

大白话：**让模型「先侦察、再动手、再检查」，成功率确实涨了——但别把它
说成「模型更会规划了」，因为它压根没写过计划。真正的机制是：
在那几个回合里，模型被结构性地引导去『先看再改』，而不是一上来乱敲。**

## 7. 这改变了什么理解

原来：H_D 的 gain = planner/executor 架构有效。
现在：gain = **staged action allocation**——对固定 turn 预算做结构化分配。
进一步（H_F）：增益大头来自**阶段提示文本**，工具门控只对 tier4 有帮助。
这个改名是档案里的里程碑修正，防止了「planner 架构有效」的误归因。

## 8. 证据

- 实验记录：`../../02_experiments/E05_real_swe.md`（design 部分）+
  `../../02_experiments/E06_mechanism.md`（H_F）
- commits：`08e6b1a1d`（H_D）、`76d91806e`（H_E 消融）、
  `7cdbc5980`（**改名**）、`1416ba43f`（H_F 归因）
- code：`tools/swe_lab_env/swe_lab_planner_program.py`
- 决策记录：`../../05_process/decision_log.md` D03

## 9. 专业术语

- staged runtime：我的理解——运行时把任务拆成有顺序的阶段；
  本项目含义——recon → execute → feedback，每段有提示。
- planner/executor 架构：我的理解——一个模型先写计划再执行；
  本项目含义——H_D 曾误用它命名；0/120 证明模型从不真写计划。
- attribution control：我的理解——只动一个因素，看它占多少效果；
  本项目含义——H_F：阶段提示 vs 工具门控，谁扛大头。

## 10. 可迁移的东西

「效果是真的」不等于「你给效果起的名字是对的」。
任何机制命名都要过一遍自己的 trace——如果模型根本没做你说它在做的事，
名字就该改。这对 agent 系统设计、产品功能命名都适用。

## 11. 还不知道什么

- known：H_D 提升 tier3；planner 回合 0/120 写计划；H_F 显示提示是大头。
- inferred：结构化的「先看再改」是有效成分。
- open：阶段提示的**哪一部分**有效（重复？内容？角色？）→ N11。

## 12. 相关节点

N04 → N05（从工具到时间表）→ N06（去真实 SWE 验证）
→ N10（gate vs banner 归因收尾）。