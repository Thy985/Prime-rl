# N11 — banner 分解：重复、内容、角色三个杠杆

## 1. 这里发生了什么

固定 dots3 + wide 20 集 + T=6 + edit 永远可用，只改每回合 banner 的
五种变体（单发/中性/动作/全相位/系统角色），加 H_A 作基线：

| arm | banner | solve |
|---|---|---|
| H_A | 无 | 0% |
| H_ONCE | 相位上下文只发一次（turn 1） | 5% |
| H_NEUTRAL | 中性文字，每回合 | 5% |
| H_ACTION | 动作导向文字 | 15% |
| H_P | 完整相位上下文，每回合 | 25% |
| H_SYS | 同 H_P 文字但 <system> 角色 | 15% |

三个独立杠杆现形：**重复**（once 5% → every-turn 15–25%）、
**内容**（neutral 5% → action 15%）、**角色**（user 25% → system 15%）。
中性状态文字是惰性的；三个杠杆**不可互相替代**。

## 2. 为什么走到这里

N10 钉死了 banner 是机制。接下来是最自然的下一步：
**既然每回合注入有用，是注入里的哪个属性在起作用？**

## 3. 这里真正的问题

- Q1: 每条回合都发（repetition）是必要的吗？
- Q2: 发什么内容（content）重要吗？
- Q3: 用哪个角色发（role）重要吗？

## 4. 我原来怎么想

以为最可能只靠「内容」：把话说对，效果就有。

## 5. 我做了什么

- 5 臂 + 基线：H_A / H_ONCE / H_NEUTRAL / H_ACTION / H_P（后来加 H_SYS），
  n=20 per arm。
- 修正注入计数：`7ca05d71d`（H_ACTION/H_PHASE 是 every-turn，
  不是 phase-boundary）。
- 对照轨迹指标：state-chg ratio、inspect-run length、inspect→edit lag。

## 6. 得到了什么

大白话：**光在开头叮嘱一次没用（5%）。每回合重复才有用（15–25%）。
重复的时候，发「中性废话」没用（5%），发「该干什么」有用（15%）。
同文字换 system 角色发，效果打折（25%→15%）。这三件事是独立的，
谁也不能替谁。**

## 7. 这改变了什么理解

原来：banner = 一条提示；改改措辞就行。
现在：banner 是一个**三维变量**（repetition × content × role），
三个杠杆各自贡献、不可替代。三条互相独立的「必要时」链结成：
repetition 是必要项；content/cadence 各值一半、不能互相替代
（→ H14）；role 是独立一维（→ H13，N12 收窄其主张）。

## 8. 证据

- 实验记录：`../../02_experiments/E07_banner.md`
- commits：`3b4f0286e`（5 臂分解）、`7ca05d71d`（注入计数修正）、
  `610450d35`（H_SYS 15%）、`d0985e941`（boundary of claim）
- code：`SWE_LAB_BANNER` 模式、`analyze_banner.py`
- 结论行：`../../00_index/hypothesis_ledger.md` H12/H13/H14（supported）
- ⚠️ 单 seed：整组数字来自 n=20 单 seed → 被 N13 修正一半

## 9. 专业术语

- cadence：我的理解——注入的节奏/次数模式；本项目含义——once vs
  every-turn（recency 必要性）。
- content：我的理解——注入的语义内容；本项目含义——neutral vs action。
- role：我的理解——消息以谁的身份出现；本项目含义——user vs system。

## 10. 可迁移的东西

对任何「提醒类」干预：区分 **频次、内容、身份** 三个旋钮，分别调。
很多系统只调内容就以为调完了——频次（recency）和身份往往才是大头。
适合：agent 提示工程、教学提醒、产品 onboarding 消息。

## 11. 还不知道什么

- known：repetition 必要（5%→15–25%）；neutral 惰性；content 次要；
  role 有影响；三者独立不可替代。
- inferred：三个杠杆都存在且独立——但全部来自单 seed。
- open：n=60 后哪些数字活下来 → N13（答案是只有「对比方向」活下来，
  绝对值全缩水）。

## 12. 相关节点

N10 → N11（拆 banner）→ N12（角色主张收窄）/ N13（单 seed 复制修正）。