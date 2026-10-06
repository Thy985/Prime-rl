# N02 — 验证器审计：tests green 不是 verifier

## 1. 这里发生了什么

在建立任何能力结论之前，先审计「谁在给奖励」。发现：只看退出码或
原始通过率的验证器，会给**作弊式的修复**打 1.000 分，而给真正的部分修复
只打 0.571 分。于是把验证器改成结构化 verdict（per_test / fixed_targets /
regressions / tampered / timed_out），并建立了 Golden Episode +
replay acceptance 两道闸。

## 2. 为什么走到这里

N01 的撤回留下了两条铁律：验证验证器、protocol 单一来源。
E02 就是第一条铁律的落地：**在奖励被当真之前，先审计奖励**。

## 3. 这里真正的问题

- Q1: 测试全绿，等于修好了吗？（答：不等于。作弊也能全绿。）
- Q2: 我怎么证明验证器没在看错的东西？——Golden Episode + replay。
- Q3: 每个难度的任务，验证器真的有区分度吗？——per-tier audit。

## 4. 我原来怎么想

以为「测试套件绿了 = 修复有效」是当然的。

## 5. 我做了什么

- 环境契约 + Golden Episode（一条手检过的 episode，记录 trace、树哈希、
  verdict、reward），在第一次真实 run 之前关闭。
- Replay acceptance：用存档 trace 重算 reward，必须复现 live 值（通过）。
- 难度阶梯每级审计（P2）：验证每个 tier 的 reward 到底区不区分好坏修复。
- 审计发现反例并修正：naive scalar 奖励的致命问题。

## 6. 得到了什么

现实中一句大白话：**「测试过了」和「修好了」之间隔着一个验证器设计。
如果验证器只看绿不绿，那不让测试跑（或绕过测试）就能骗过分。**

## 7. 这改变了什么理解

原来：奖励 = 测试通过率，越高越好。
现在：奖励必须能识别「真修复 / 耍诈 / 部分修复」——结构化 verdict 存在
正是因为 scaalar 不够用。后面档案里所有指标纷争（`4b6854707` 的
`2>/dev/null` 计数、WRITE_RE 修正）都是这次审计的子孙。

## 8. 证据

- 实验记录：`../../02_experiments/E02_verifier_audit.md`
- commits：`498fca529`（契约+Golden Episode）、`b2698922c`（real verifiers
  Episode）、`56a6c91d1`（replay 通过，Phase 1B acceptance）
- code：`tools/swe_lab/{contract.py,golden.py,replay_executing.py,terrain.py}`
- spec：`tools/swe_lab/PLAN.md` 2.1 节（三档事实 + Episode 优先规则）

## 9. 专业术语

- verifier：我的理解——判断「答案对不对」的程序；本项目含义——SWE
  repair 的裁判，含 tampered/per_test/fixed_targets 等字段。
- Golden Episode：我的理解——一条人工确认过的完整样例，作为验收基准；
  本项目含义——第一次真实 run 之前必须存在且被记录。
- replay acceptance：我的理解——拿旧 trace 重算，数值必须一致；
  本项目含义——验证「计算奖励的代码没在被测对象之外漂移」。

## 10. 可迁移的东西

任何「打分器」都要先证明它打的是你想打的分数。特别是对抗性场景：
如果被你计分的那一方可以操纵计分输入（这里是让测试不跑），先堵这个洞。
适用：RL reward design、代码审查自动化、评测集正确性。

## 11. 还不知道什么

- known：naive scalar 被 tampering 骗过（1.000 vs 0.571）；结构化 verdict 修复了它。
- inferred：结构化工件足以当该 tier 的裁判；replay 证明计算路径稳定。
- open：验证器在没见过分布的修复（OOD repair）上是否仍然正确——未审计。

## 12. 相关节点

N01（撤回 → 逼出本次审计）→ N03（可信验证器才敢建难度阶梯）。