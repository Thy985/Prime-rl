# N14 — action allocation：同数量的动作，换了分配

## 1. 这里发生了什么

n=60 的轨迹 mediation 链，把「banner 生效」的机制从行为上钉住：
- **state-changing action 比例**：0.04 → 0.07（全体）；0.17 → 0.30（仅 solved）。
- **总工具调用数（n_calls）**：不变。
- **第一次 edit 的时间**：不提前。
- **最长的 inspect run**：变短。

也就是说：agent **没有更努力、没有更早动手、没有多干活**——它把同样数量
的动作从「重复侦察」再分配给了「会改变状态的调用」。这就是 action allocation。

## 2. 为什么走到这里

N13 确认两个对比存活（banner vs none；multiple vs single）。剩下最后一块拼图：
**通过什么机制存活？** 需要区分「更努力」「更早动手」「更聪明」几种候选。

## 3. 这里真正的问题

- Q1: banner 是让模型更努力（更多调用）吗？
- Q2: 是让模型更早动手（first_edit 提前）吗？
- Q3: 还是只是改变了「做什么」的分配？

## 4. 我原来怎么想

有可能的几种解释都摆在桌上：effort↑（多干活）、earlier action
（早动手）、reasoning↑（想得更深）、allocation（同样动作换分配）。

## 5. 我做了什么

- 用 `analyze_banner.py` 的轨迹指标：state-chg ratio、inspect-run length、
  inspect-to-edit lag、edit-after-failed-test。
- 在 n=60 的配对结构上测 mediation 链（观测性链条，非正式因果估计）。
- solved-only 子集重复看 state_chg（0.17→0.30），排除「整体比例被
  失败 episode 拉低」的假象。

## 6. 得到了什么

大白话：**给模型每回合提一句「现在是哪个阶段」，它并不会变得更勤快、
更早动手或更聪明——它只是把同样的力气，从「反复看」挪到了「动手改」。
结果就是同样 6 个回合，改得更多、冗余侦察更少。**

## 7. 这改变了什么理解

原来：机制可能是多干活 / 早动手 / 想得更深。
现在：**全部排除。** n_calls 平（不是 effort）、first_edit 不提前
（不是 earlier）、没有任何 reasoning 测量（C04 明确 no evidence）。
唯一变化的维度是 action allocation。这也是最终 headline 的机制核心。

## 8. 证据

- 实验记录：`../../02_experiments/E08_expanded_n.md`（mediation 段）
- commits：`0807caa0c`（paired + mediation）、`a5975ac74`（freeze）
- code：`tools/swe_lab/analyze_banner.py`
- 结论行：`../../00_index/claim_evidence_matrix.md` C16（moderate，
  观测性链条）；final_report 4.6 节

## 9. 专业术语

- action allocation：我的理解——把有限的决策机会分配到哪些动作上；
  本项目含义——state_chg 升、n_calls 平：分配变了，总量没变。
- mediation chain：我的理解——解释「输入→输出」中间过程的观测链条；
  本项目含义——trajectory 上测出来的行为差异，非正式因果估计。
- state-changing call：我的理解——会改变世界状态的动作（如 edit）；
  本项目含义——与只读 inspect 相对；banner 让它变多。

## 10. 可迁移的东西

「干预变了分配的哪个维度」这类 question 模板：先量总量（n_calls）、
再量时间（first_edit）、再量构成（state_chg）——三者一起看才能区分
努力/时机/分配。任何「引导」类干预都该报告这三件事。

## 11. 还不知道什么

- known：state_chg 0.04→0.07（0.17→0.30 solved-only）；n_calls 平；
  first_edit 不提前；inspect_run_max 缩短。
- inferred：分配变化是机制，且是观测性证据。
- open：为什么分配会变（注意力？上下文相关性？）；正式因果估计
  （bootstrap/SEM）未做 → N17。

## 12. 相关节点

N13（存活对比）→ N14（机制）→ N16（最终理解）/ N17（正式 mediation 未做）。