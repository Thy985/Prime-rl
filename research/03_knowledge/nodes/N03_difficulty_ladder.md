# N03 — 难度阶梯 + 预算前沿：headroom 从哪来

## 1. 这里发生了什么

造了一个 5 级的难度阶梯（tier1 单文件 → tier5 多约束），每级都做了
per-tier audit，并测了「预算前沿」：不同 max_turns 下各 tier 能解多少。
结论是**出乎意料的负向发现**——难度本身并没有制造区分度；
真正制造 headroom（可测量的提升空间）的是**绑定 turn 预算**。
期间还修了两个测量 bug：tier3 的悬崖部分是 endpoint 错误率假象，
以及一个把「有预算效果」藏起来的 bug。

## 2. 为什么走到这里

N02 后验证器可信了，N01 的教训说要先有好的测量。那测量什么？
需要一个能区分 agent 强弱的地形——于是先造地形。

## 3. 这里真正的问题

- Q1: 把任务改难，agent 的表现会平滑下降吗？（答：不会，会出悬崖。）
- Q2: 这个悬崖是真的难度差异，还是测量假象？（答：部分是 endpoint 错误率。）
- Q3: 什么条件能让「不同 harness 的可比性」成立？（答：绑定预算。）

## 4. 我原来怎么想

以为难度是天然可用的区分度：tier 越高，headroom 越大。
也以为跑几遍就可以把结果并起来看。

## 5. 我做了什么

- 建 5 级阶梯 + 每 tier audit；每 tier 8 attempts。
- 发现 tier3 悬崖后先查失败率：`5ef3bf8ee` 修了 endpoint 错误率，
  把 errored episodes 从 solve 曲线排除。
- 重复 run 暴露 endpoint contention：`b43c3f1d4`——**重复便宜，结论贵**。
- tier4 是 hidden configuration layer：audit 比 solve rate 更能说明问题。
- tier5 没有让 H_A 脱敏（a56e6ae13）——难度轴上的负结果。
- `6004a7559`：绑定 turn budget 创造出 H_A 之前没有的 headroom
  （而且有个 bug 曾把它藏起来）。

## 6. 得到了什么

大白话：**「题目难」不等于「能看出好坏」。要让 agent 之间的差别显现，
你得让它们都在一个紧的回合预算下干活——钱少了，才会看出谁更会花。**

## 7. 这改变了什么理解

原来：难度 × budget 都是顺手设的；pool 几遍就能下结论。
现在：operating point（任务集 + 预算组合）是**先于 harness 比较就要选好**
的；饱和基线（tier1/2、无预算的 tier5）不是实验设置，是地板。
E04 的整体可比较性由此而来。

## 8. 证据

- 实验记录：`../../02_experiments/E03_swe_micro.md`
- commits：`57e81c8af`, `5ef3bf8ee`, `2755ba56f`, `a56e6ae13`, `6004a7559`
- artifacts：`tools/swe_lab/runs/frontier_budget.json`,
  `tools/swe_lab/tiers/ladder_audit.json`
- code：`ladder.py`, `frontier.py`
- runs：`outputs/swe-lab-harnessA` 等

## 9. 专业术语

- difficulty ladder：我的理解——一组刻意排序的任务集；
  本项目含义——tier1–5，每级有 audit。
- budget frontier：我的理解——成功率随预算（回合数）变化的曲线；
  本项目含义——`max_turns` 扫出来，决定哪个预算有信号。
- headroom：我的理解——可被 harness 拉开差距的空间；
  本项目含义——无预算时 H_A 饱和，绑定预算后才有可比较的差异。

## 10. 可迁移的东西

「先找到有信号的 operating point，再开始比较」——选错操作点（饱和或地板）
会让整个实验白做（P6 的 2×2 就栽在这里，见 N10）。这是设计层教训：
budget、任务集、模型是实验的一部分，不是环境噪音。

## 11. 还不知道什么

- known：tier5 无预算时 H_A 不脱敏（难度轴负结果）。
- inferred：绑定预算创造 headroom；tier4 是 hidden-config 层。
- open：更多 tier、更多任务族时这个 ladder 是否稳定；audit 的覆盖上限。

## 12. 相关节点

N02 → N03（可信地形）→ N04（第一次 harness 比较用上它）。