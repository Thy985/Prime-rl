# Concepts — 概念地图（谁通向谁）

这张图回答：「这个术语和那个术语是什么关系」。
规则：关系必须来自流程中的真实问题，不能是字典关系。

```
verifier ──审计出──> tests green ≠ 修复有效（N02）
harness ──包含──> action affordance（工具开关）＋ banner（提示注入）
interaction budget ──决定──> headroom（N03）/ 效果形状（N08）
staged runtime ──由──> banner（提示）＋ gating（工具隐藏）组成（N10）
gating ──被否──> 不是机制（N10）
banner ──由──> repetition × content × role 三个维度（N11）
runtime intervention ──是──> banner 的正式说法（N12）
action allocation ──被证实──> banner 的机制（N14）
single-seed artifact ──被修正──> paired McNemar 存活（N13）
distilled trajectory ──被拒──> 一条路线，不是一类路线（N09）
```

## 按角色分组

| 角色 | 概念 | 反例/边界 |
| --- | --- | --- |
| 测量基础 | verifier, protocol invariance, paired McNemar | 测试绿 ≠ 修好；聚合率对比会死 |
| 干预对象 | harness, interaction budget, action affordance | 预算不是噪音；工具开关≠机制 |
| 干预本身 | staged runtime, banner, runtime intervention | banner 是组合，不是一句话 |
| 机制解释 | action allocation, mediation chain | 是观测性链条，不是因果估计 |
| 失败模式 | single-seed artifact, provider failure | 单 seed 是假设；provider 失败≠模型失败 |
| 路线状态 | distilled trajectory (rejected), cross-model (untested) | 路线被拒≠不可能；未测≠阴性 |

## 忘记术语时怎么找回

1. 想「我观察到了什么」→ 查概念总表的「我的观察」列。
2. 想「哪个实验」→ 看「关键节点」，跳到 nodes/Nxx。
3. 想「能不能说」→ 看 `../../00_index/claim_evidence_matrix.md` 的
   「What we must not claim」。