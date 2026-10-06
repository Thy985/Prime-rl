# N06 — 真实 SWE 校准：+32pt 缩水到 +10pt

## 1. 这里发生了什么

把 H_D vs H_A 搬到真实 SWE-bench Verified 上（没有 Docker，自建
containerless verifier：prepare.py 在 base commit clone，verify.py 对
host 侧副本打 oracle 测试补丁，跑 F2P/P2P）。5 个 django 实例的小 pilot
上 H_D 拿到 44%（7/16），H_A 12%（2/16）——+32pt，非常亮眼。
但扩到 20 实例两仓库后，差距缩到 +10pt——**pilot 高估了约 4 倍**。

## 2. 为什么走到这里

N05 的 lab 效果需要回答：离开自建 lab，在真实 issue 修复上还成立吗？
lab 的 tier 是「作者声称的难度」，真实 SWE 是外部现实的难度。

## 3. 这里真正的问题

- Q1: 没有容器运行时，怎么在真实 SWE-bench 上验证修复？（自建 verifier。）
- Q2: H_D 的效果在真实 SWE 上多大？（pilot +32pt，wide +10pt。）
- Q3: 这个效果在更宽的预算/任务集上还成立吗？（→ N08 budget sweep。）

## 4. 我原来怎么想

以为 pilot 的 +32pt 是 H_D 效果的「真实大小」，会随样本变大保持。

## 5. 我做了什么

- 自建 containerless verifier 管线（5-check gate；resolve=1.0 iff 全部
  F2P+P2P 过且无 tampering；f2p_fraction 0 权重；setup 剥离 gold-fix 痕迹）。
- pilot：5 gated django（11239、12155 因无信号被 gate 掉）。
- topup 到 5 eps/harness：11066、11206 补满 → 7/16 vs 2/16。
- wide 20 实例（+sympy）重新校准。
- 第二模型（space-bunny 7B）同 grid 复测方向。

## 6. 得到了什么

大白话：**在真实修 bug 的场景里，分阶段引导仍然有用，但没有 pilot 显示
的那么大——5 个题上 +32 分，20 个题上 +10 分。小样本会放大好消息。**

## 7. 这改变了什么理解

原来：pilot 的 +32pt 是效果的规模。
现在：诚实的规模是 wide 集的 +10pt；pilot 是 5-instance / 4-turn 的数字。
同时方向在第二模型上复现（bunny +12pt），说明这不是单模型巧合，
但量级是任务集相关的。

## 8. 证据

- 实验记录：`../../02_experiments/E05_real_swe.md`
- commits：`14c2b34e6`（pilot）、`22f40cd41`（topup 7/16 vs 2/16）、
  `6bc971c6b`（**wide 校准：4× 缩水**）、`e559251f3`（bunny）
- code：`tools/swe_lab_env/swe_bench/{prepare,verify,taskset}.py`
- 复现细节：E05 的 budget-sweep 表格逐格可复现（base 10 + topup 6 = 16 eps）

## 9. 专业术语

- containerless verifier：我的理解——不开容器也能验证修复；
  本项目含义——host 侧 clone + 打测试补丁 + 解释器跑 F2P/P2P。
- pilot：我的理解——小样本先看方向；
  本项目含义——5 实例 django，曾给出 +32pt 的过乐观读数。
- calibration：我的理解——用更大的样本来修正早期数字；
  本项目含义——wide 20 集把 +32pt 修正为 +10pt。

## 10. 可迁移的东西

任何研究都会遇到「小样本效果好」：**先别庆祝，先扩大样本看量级。**
方向可以从小样本读，量级必须从更大样本读。这适用于产品 A/B、
模型评测、任何效果衡量。

## 11. 还不知道什么

- known：+32pt（pilot）→ +10pt（wide）；bunny 方向复现（+12pt）。
- inferred：效果真实但量级与任务集强相关。
- open：任务族分层（更多 repo）会怎样；不同预算下的量级 → N08。

## 12. 相关节点

N05 → N06（去哪验证）→ N07（静态散文被否）/ N08（预算形状）/ N09（蒸馏）。