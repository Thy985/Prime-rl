# N15 — 跨模型 H18：被 provider 阻断，不是被实验否定

## 1. 这里发生了什么

计划中的跨模型复制（banner 研究在 bunny / DeepSeek-v4-flash 上跑）
**从未完成**：bunny provider 先被 `deep-ep==1.2.1` 的 aarch64 元数据问题
卡住（`uv sync` 静默失败，eval 子进程根本没启动——`--no-sync` 修复后
smoke 50.9s 完成、reward=1.0），随后用户决定终止所有 bunny 任务（D18）。
DeepSeek-v4-flash 从未真正运行。Phase 8A 的 run 目录一个都不存在——
只有 3 个 smoke。

## 2. 为什么走到这里

N06 曾在 pilot 上用第二模型复现过方向（bunny +12pt），但 banner 研究的
跨模型版才是「效果是否模型无关」的决定性测试；用户把它排在
Phase 8 的第一步（D15：cross-model first, then n）。

## 3. 这里真正的问题

- Q1: banner 的效果在别的模型上成立吗？
- Q2: provider 失败和模型失败，怎么区分？

## 4. 我原来怎么想

以为换模型只是「再跑一遍」；以为 provider 挂了可以快速绕过。

## 5. 我做了什么

- 诊断 bunny：空流响应 + smoke 挂起 → 根因是 `uv sync` 静默失败于
  aarch64 元数据，不是模型（F10）。`--no-sync` 修复（`6315a6e06`）。
- 并行 subagent：一个修 bunny 兼容，一个跑 8C（D17）——正确的并行决策。
- D18：用户终止所有 bunny 任务；DeepSeek-v4-flash 也没跑。

## 6. 得到了什么

大白话：**我们想验证「换个模型还有没有这个效果」，但两次尝试都被
「模型服务本身不可用」挡住，而不是被「模型没这个效果」否定。
这事至今没有答案——是『未测试』，不是『没有』。**

## 7. 这改变了什么理解

原来：cross-model 是计划中的一步。
现在：H18 **untested (blocked)**——永远记录为未测，不能当 negative。
同时 F10 立下规矩：provider 失败和模型失败在 harness 日志里看起来一样，
诊断顺序必须是：probe endpoint → dependency chain → model。

## 8. 证据

- 实验记录：`../../02_experiments/E08_expanded_n.md`（Phase 8A 段：
  run 目录不存在 = 物理证据）
- commits：`6315a6e06`（--no-sync）、`51f7ae526`（8A configs）
- 失败记录：`../../05_process/failure_ledger.md` F08/F10/F14
- 决策：`../../05_process/decision_log.md` D16/D17/D18
- 结论约束：matrix C18（no evidence）+ “must not claim” 3/6

## 9. 专业术语

- cross-model replication：我的理解——换模型看效果是否一致；
  本项目含义——banner 效果 × bunny/DeepSeek：未完成。
- provider failure：我的理解——模型服务端坏了，不是模型本身不行；
  本项目含义——deep-ep 元数据、空流、挂起 smoke 的根因。
- untested (blocked)：我的理解——因为外部条件没跑成，不是跑输了；
  本项目含义——H18 的正式状态；永远不能写成 negative。

## 10. 可迁移的东西

**「没跑成」和「跑输了」是两种状态，记录上必须分家。**
被外部依赖卡住的研究腿，要么持续投入维持（有真实成本），
要么正式归档为 untested——拖着不发落不归档最坏。
诊断顺序固定为 probe endpoint → dependency → model。

## 11. 还不知道什么

- known：bunny 曾因 deep-ep 元数据挂掉；--no-sync 修复后 smoke 通过；
  8A run 目录不存在；D18 终止。
- inferred：（无——这正是问题：没有任何效果观测。）
- open：banner 效果是否跨模型成立（H18 全开放）。

## 12. 相关节点

N06（pilot 曾跨模型 +12pt）→ N15（banner 跨模未测）
→ N16（边界条件）/ N17（未来工作的第一条）。