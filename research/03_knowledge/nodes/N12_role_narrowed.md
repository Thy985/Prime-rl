# N12 — 角色对比收窄：system ≠ user，但不是「中断因果」

## 1. 这里发生了什么

H_SYS（同 H_P 文字，但用 system 角色发）拿到 15%，H_P（user 角色）
25%——角色是有影响的。但在收敛结论时明确设了边界：
**H_SYS 只能证明「system-role ≠ user-role」，不能证明「中断是因果」。
**术语从「harness 必须中断模型」收窄为「user-turn runtime intervention /
per-decision control-plane injection」。这是档案里一次重要的主张收窄
（D15），防止把 E07 读成它支撑不了的东西。

## 2. 为什么走到这里

N11 发现角色是三个杠杆之一。需要判读它到底证明了什么——
是「角色重要」，还是「注入本身必须打断模型」？

## 3. 这里真正的问题

- Q1: 角色的影响，能不能推广成「中断是因果」？
- Q2: 系统角色 vs 用户角色，在什么意义上不同？

## 4. 我原来怎么想

容易滑向的直觉：H_SYS 更低 → 说明「强行打断模型有效」；
「harness 必须 interrupt the model」。

## 5. 我做了什么

- 读 H_SYS 结果：15% vs 25%。
- 对照三层模型（N16 会展开）：Phase5 harness 改变行为；Phase6 不是 gate；
  Phase7 是注入的性质（role/cadence/content）。
- D15 显式收窄主张：「不要直接写成 harness 必须中断模型」。
- 统一术语：user-turn runtime intervention。

## 6. 得到了什么

大白话：**同一个消息，用「系统」身份发和用「用户」身份发，效果不一样——
但这只是说明「身份有影响」，不等于「必须打断模型才行」。
后者是一个更强的主张，我们没有证据。**

## 7. 这改变了什么理解

原来：角色杠杆 → 中断因果（可能）。
现在：**窄了。** role 对比是 injection position 的对比，不是中断测试。
「interruption is causal」被列进 ‘what we must not claim’（matrix 第 4 条）。
这个收窄让「user-turn runtime intervention」成为档案的标准说法。

## 8. 证据

- 实验记录：`../../02_experiments/E07_banner.md`（H_SYS 段）
- commits：`610450d35`（H_SYS 15%）、`d0985e941`（boundary/术语）
- 决策：`../../05_process/decision_log.md` D15
- 结论约束：`../../00_index/claim_evidence_matrix.md` C17 + “must not claim” 4
- 会话证据：`../../05_process/hypothesis_origin.md`（seq=8292 用户直接收窄）

## 9. 专业术语

- message role：我的理解——消息以谁的名义发出；本项目含义——user vs
  system，H_SYS vs H_P。
- user-turn runtime intervention：我的理解——在运行中，以用户回合的形式
  注入上下文；本项目含义——D15 定下的标准说法。
- control-plane injection：我的理解——对决策过程的旁路提示；
  本项目含义——per-decision 注入的正式名。

## 10. 可迁移的东西

**分清「对比的结果」和「对比的推广」。** 一个 A≠B 的对比只能说明二者
不等价，不能自动升级成「A 的某种更强性质」。写结论前先问：
这个主张需要哪种证据？我有没有？

## 11. 还不知道什么

- known：H_SYS 15% < H_P 25%（单 seed）；system ≠ user。
- inferred：角色是注入的独立性质。
- open：为什么这个模型对 role 敏感——机制未探明；跨模型是否一致？未测。

## 12. 相关节点

N11（角色是杠杆之一）→ N12（收窄）→ N16（三层模型收拢）
→ N17（开放：机制未明、跨模未测）。