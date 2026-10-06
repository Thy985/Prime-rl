# 研究流程图 (Research Map)

一次研究是一张有向图。横向看是阶段，纵向看是「为什么走到下一步」。
被推翻的路和缩水的结论都留在图上——它们是这张图里最有价值的部分。

## 一行结论（本图最终汇合点）

> 给固定模型/固定预算/固定工具集的 agent，在**每个决策回合重复注入**
> 当前阶段上下文（user 角色），会**重新分配它固定数量的动作**，从而在
> 小预算下提高成功率。不是推理变强、不是更努力、不是更早动手、不是工具开关。

---

## 流程图

```
N01 起点：奖励能塑造可迁移能力吗？
  │    E01 reverse-text：两个结论都被撤回
  │    （protocol bug / optimiser artifact）
  ▼    教训 → 先验证验证器，protocol 必须单一来源
N02 验证器审计：tests green 不是 verifier
  │    E02：tampering 1.000 > 真实修复 0.571 → 结构化 verdict
  ▼    验证器可信，才敢建难度阶梯
N03 难度阶梯 + 预算前沿
  │    E03：headroom 不是难度给的，是绑定预算给的（bug 曾掩盖它）
  ▼    有了 headroom，harness 比较才有意义
N04 工具即杠杆？ Harness A/B/C
  │    E04：移除 edit 工具 −44pt（n=1）→ n=32 时 Harness C 反转撤回
  │    └─ 教训：**每个机制先复制，再命名**
  ▼    工具影响是真的，但怎么用工具时间表影响更大
N05 分阶段运行时 H_D
  │    lab 效果显著 → 但 planner turns 写真实计划的 0/120
  │    └─ 撤回 "planner" 框架 → 改名 staged action allocation
  ▼    去真实 SWE 验证
N06 真实 SWE 校准
  │    E05：pilot +32pt → wide 20 集 +10pt（4× 缩水）
  ├─ 否│ N07 静态散文假设  H_A-prime 1/16 → 文字不是控制信号
  ├─ 否│ N08 预算无关假设  T=4 峰 T=8 消失 → 效果是预算形状的
  ├─ 否│ N09 蒸馏路线      student 0/10 tool calls → 路线被拒
  └─ 疑│ N10 gating 是机制？
        │    E06 2×2：H_P(banner) = H_D 25%；H_G(gate) = 1/20
        │    → **gating 被否，banner 就是机制**（pilot 上 H_P=H_D=7/16 精确复现）
        ▼
        N11 banner 分解
        │    E07：H_A 0% / H_ONCE 5% / H_NEUTRAL 5% / H_ACTION 15% / H_P 25% / H_SYS 15%
        │    三个杠杆：重复（必要）、内容（次要）、角色（有影响）
        ├─ 界│ N12 角色对比收窄：system ≠ user，**不是**「中断因果」（D15）
        └─ 疑│ 单 seed 能信吗？
              ▼
              N13 复制修正  n=60
              │    E08：H_P 的 25% → 13%（seed-1 rerun 0/20 → 单 seed 噪声）
              │    timing 维度死亡：H_REPLAY 17% > H_P 13%, p=0.77
              │    两个配对主张存活：banner vs no-banner p=0.031；
              │    multiple vs single p=0.008
              ▼
              N14 机制定型：action allocation
              │    E08 mediation：state_chg ↑、n_calls 平、first_edit 不提前
              ▼
              N16 当前最终理解（三层模型）
              │    harness 改变行为 → 不是 gate → 是注入的性质
              ▼
              N17 开放问题（跨模型、更多 seed、正式 mediation…）

另路（未汇合，保持开放）：
  N06 → N15 跨模型 H18：bunny/DeepSeek 两条腿都被 provider 阻断（F08/D18）
       → 状态：untested（不是 negative）→ 汇入 N16/N17
```

---

## 节点一览

| ID | 节点 | 类型 | 一句话 |
| --- | --- | --- | --- |
| N01 | 起点：奖励能塑造可迁移能力吗？ | design | E01 反转文本；两个结论撤回 → 测量纪律 |
| N02 | 验证器审计 | mechanism | tests green ≠ verifier；tampering 反而得高分 |
| N03 | 难度阶梯 + 预算前沿 | design | headroom 来自绑定预算，不是难度 |
| N04 | 工具即杠杆？ | experiment | 移除 edit −44pt；n=32 反转撤回 |
| N05 | 分阶段运行时 H_D | concept | 效果显著；planner 框架撤回 |
| N06 | 真实 SWE 校准 | experiment | +32pt → +10pt（4× 缩水） |
| N07 | 静态散文假设 | hypothesis | H_A-prime 被否：文字不是控制信号 |
| N08 | 预算形状效应 | hypothesis | T=4 峰 T=8 消失：效果是预算形状的 |
| N09 | 蒸馏路线 | failure | student 0/10 → 路线被拒 |
| N10 | gating 被否 | experiment | H_P=H_D；H_G 地板；banner 是机制 |
| N11 | banner 分解 | experiment | 重复必要、内容次要、角色有影响 |
| N12 | 角色对比收窄 | design | system ≠ user，不是「中断因果」 |
| N13 | 复制修正 n=60 | experiment | 25%→13%；timing 维度死亡；两个配对主张存活 |
| N14 | action allocation | mechanism | n_calls 平、state_chg 升：动作被重新分配 |
| N15 | 跨模型 H18 | open question | 被 provider 阻断；untested |
| N16 | 当前最终理解 | concept | 三层模型收拢 |
| N17 | 开放问题 | open question | 未做的事，不是失败 |

---

## 关系表

> 读法：第三列是**节点 id** 的行与 `knowledge_graph.json` 的边一一对应；
> 第三列是纯括号（如「(timing 维度)」）的行，指被支撑/否定的**假设本身**
> 而非节点——假设不是节点，不进 JSON 边表，它落到对应节点的状态上。

| 从 | 关系到 | 到 | 为什么 |
| --- | --- | --- | --- |
| N01 | leads_to | N02 | 撤回的结论逼出「先验证验证器」 |
| N02 | leads_to | N03 | 验证器可信，难度阶梯才有意义 |
| N03 | leads_to | N04 | headroom 确定，harness 比较才不饱和 |
| N04 | leads_to | N05 | 工具存在但时间表不同 → 分阶段运行时 |
| N05 | replaces | N04 | 移除工具 → staged action allocation：旧的机制命名被替代 |
| N05 | leads_to | N06 | 实验室效果 → 真实 SWE |
| N06 | rejects | N07 | H_A-prime 1/16：静态散文不携带效果 |
| N06 | rejects | N08 | T=8 反超：效果依赖预算 |
| N06 | rejects | N09 | 蒸馏 0/10：这条路线不通 |
| N06 | tests | N10 | 下一步怀疑 gate 是机制 |
| N06 | connects_to | N15 | 跨模型腿被 provider 阻断（H18 untested） |
| N10 | refines | N04 | 2×2 缩窄「工具即杠杆」：机制不是工具开关 |
| N10 | rejects | N05 | 2×2：banner 不带 gate 也等于 H_D，gating 假设死 |
| N10 | supports | (banner 机制) | H_P = H_D 精确复现 → 机制改名为 banner |
| N10 | leads_to | N11 | banner 是机制 → 拆它的性质 |
| N11 | refines | (banner 机制) | 重复/内容/角色三个杠杆，不可互相替代 |
| N11 | connects_to | N12 | 角色对比 → 收窄主张边界 |
| N11 | leads_to | N13 | 单 seed 证据 → 复制 |
| N13 | corrects | N11 | H_P 25% 是 seed 噪声，实际 13% |
| N13 | rejects | (timing 维度) | H_REPLAY p=0.77：位置不重要 |
| N13 | supports | N11 | multiple vs single p=0.008；banner vs none p=0.031 |
| N13 | leads_to | N14 | 存活主张 → 测量其机制 |
| N14 | supports | (action allocation 机制) | mediation 链：同数量动作，不同分配 |
| N14 | supports | N16 | 机制定型进入最终理解 |
| N14 | leads_to | N16 | 机制定型 → 三层模型收拢 |
| N15 | connects_to | N16 | 跨模型始终未测 → 边界条件保留 |
| N16 | leads_to | N17 | 理解停在哪 → 接下来做什么 |

---

## 三条被否/缩水的路（别删，这是主体）

1. **奖励塑造能力（N01）** — 「reward rises and transfers」与
   「every reward destroys the capability」双双撤回：前者 protocol bug，
   后者 optimiser artifact。产出两个铁律：验证验证器、protocol 单一来源。
2. **工具即杠杆（N04→N10）** — 先是「edit 工具移除导致 −44pt」，
   后来 2×2 证明在分阶段 harness 里 **gate 毫无贡献**，
   banner（纯文字注入）才是机制。中间还撤回过一次 Harness C。
3. **单 seed 结论（N11→N13）** — E07 的 25% 被 n=60 修正为 13%；
   timing 维度（H_REPLAY）直接死亡。过程教训：
   **配对比较（同 20 实例）存活，聚合率比较死亡。**

## 怎么读这张图

- 先沿 `N01 → N02 → … → N16` 主链走一遍（约 5 分钟）。
- 再回到三个「被否」分支，看它们**为什么**被否（N07/N08/N09/N10/N13）。
- 最后读 `N15` 和 `N17`：这两处是「研究故意没做的事」，不是失败。
- 节点详情：`nodes/N01_*.md` … `nodes/N17_*.md`（统一 12 节结构）。