# N10 — gating 被否：banner 才是机制

## 1. 这里发生了什么

一个 2×2 因子设计把 H_D 的两半拆开：banner（每回合注入阶段提示）和
gate（侦察阶段藏起 edit 工具）。结果决定性地偏向 banner：

| | gate OFF | gate ON |
|---|---|---|
| banner ON | H_P 25% (=H_D) | H_D 25% |
| banner OFF | H_A（地板） | H_G 1/20（地板） |

加上 pilot 确认：**H_P 精确复现 H_D（7/16 = 44%，同一批实例）**。
也就是说：把门控全部拿掉、只留每回合的提示文字，效果一模一样；
反过来只留门控、没有提示，掉回地板。**affordance scheduling 被否决。**

## 2. 为什么走到这里

N06–N09 排除了静态散文、蒸馏、把量级和预算搞清楚之后，
剩一个最顽固的候选机制：也许不是「文字」，而是「阶段里没有 edit 工具」
这个结构性约束在起作用（gate）。

## 3. 这里真正的问题

- Q1: H_D 的效果，是「提示」还是「门控」给的？
- Q2: 一个更聪明的自适应调度器（H_ADAPT）能不能超过固定分段？

## 4. 我原来怎么想

以为 gating 是主力：edit 工具不在侦察阶段，agent 被迫先看再改。

## 5. 我做了什么

- 2×2 factorial：H_A/H_P/H_G/H_D（`SWE_LAB_PROMPTS` × `SWE_LAB_GATE`）。
- H_ADAPT：确定性的 recon→execute→verify 状态机（按观察到的调用驱动）。
- T=6（有信号的预算）做 6C 分解；pilot（5 实例）做精确复现。
- 修掉行为分类器 bug（`4b6854707`：`2>/dev/null` 不再算 tree write）。

## 6. 得到了什么

大白话：**「先看再改」的效果不是靠「把改的按钮藏起来」实现的，
而是靠每回合提醒「现在是侦察阶段」实现的。藏按钮（gating）没用，
提醒（banner）全权负责。自适应调度器也赢不了固定分段。**

## 7. 这改变了什么理解

原来：H04 残留的「工具集是杠杆」读法 + gate 假设。
现在：**gate falsified。** 机制改名：per-turn control-plane signaling。
「banner（每回合的相位提示）就是机制」成为后续所有工作的支点。
顺带：H_ADAPT（v1 三条规则）从未胜过固定分段，还有 recon-2 税。

## 8. 证据

- 实验记录：`../../02_experiments/E06_mechanism.md`
- commits：`2bae38d38`（6A/6B 开关）、`6aea58419`（6C T=6：
  H_P 5/20 = H_D、H_G 1/20）、`ce618eed3`（pilot H_P=H_D 7/16）、
  `4b6854707`（分类器修正）
- code：`swe_lab_planner_program.py`、`swe_lab_adaptive.py`
- 结论行：`../../00_index/hypothesis_ledger.md` H11（rejected）
- 决策：`../../05_process/decision_log.md` D13（停止研究 affordance scheduling）

## 9. 专业术语

- affordance gating：我的理解——按阶段隐藏可用工具；
  本项目含义——H_G/H_D 的 recon 阶段无 edit；被否。
- 2×2 factorial：我的理解——两个开关的组合实验；
  本项目含义——banner × gate 四格，一次回答两个问题。
- control-plane signaling：我的理解——对决策过程的旁路提示；
  本项目含义——H_D/H_P 每回合的 phase banner；D13 定名。

## 10. 可迁移的东西

**先验证「最可信的机制故事」，再优化它**——而且要用能同时区分
「两个候选」的设计（2×2），而不是逐个测。机制命名错误会污染一整段研究，
尽早用最小分解实验钉住它。

## 11. 还不知道什么

- known：H_P=H_D、H_G 地板；pilot 上精确复现；H_ADAPT 不敌固定分段。
- inferred：banner 是机制；门控贡献 ≈ 0。
- open：banner 的**哪个性质**承载效果（重复/内容/角色）→ N11。

## 12. 相关节点

N05（H_F 归因预告）→ N10（钉死 banner）→ N11（拆 banner 的性质）
→ N12（角色收窄）。