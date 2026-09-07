# RFdiffusion3 + ProteinMPNN + RF3：官方Pipeline的demo复现与Bug修复



## 项目简介

本项目复现了 [RosettaCommons/foundry](https://github.com/RosettaCommons/foundry)中 RFdiffusion3 (RFD3) → ProteinMPNN → RoseTTAFold3 (RF3) 的官方end-to-end蛋白质设计示例流程，并在复现过程中**定位并修复了官方notebook中的一处关键逻辑错误**——该错误导致设计验证环节完全失真（RMSD偏差高达30倍以上），修复后指标恢复至正常优秀水平。

本项目当前处于 **Phase 1（无条件生成场景的流程复现与验证）**，Phase 2（针对真实蛋白靶点的条件生成 / binder design）正在进行中，详见文末「后续计划」。



## 背景：这套Pipeline是做什么的

| 步骤        | 模型        | 作用                                                         |
| ----------- | ----------- | ------------------------------------------------------------ |
| 1. 骨架生成 | RFD3        | 基于扩散模型，从头生成蛋白质主链结构（只有N/CA/C/O原子坐标，无氨基酸序列） |
| 2. 序列设计 | ProteinMPNN | 给定固定骨架，反向设计出能折叠成该结构的具体氨基酸序列       |
| 3. 结构验证 | RF3         | 将设计出的序列重新折叠预测结构，与原始骨架比对，验证"可设计性"(designability) |

核心验证逻辑：如果MPNN设计的序列被RF3重新折叠后，能高度还原RFD3最初生成的骨架形状（低RMSD、高pLDDT/pTM），则说明这是一个"可设计"（designable）的结构，具备被真实合成表达的潜力。该问题的定位并非通过阅读文档发现（相关文档尚未完善），而是通过**将pipeline拆解为三个独立可验证的阶段，逐段打印中间产物（链数、残基数、序列内容）进行排查后定位**。



## 官方Notebook中的Bug

在复现官方 end-to-end notebook 时，发现其 RF3 验证环节实际使用的是 **RFD3生成的原始骨架**（序列为占位符），而非 **MPNN真正设计出的序列结构**，导致整个验证流程未能真正闭环。

```python
# 官方notebook原始代码（有问题）
aa_generated = atom_array              # 来自Section 1，序列未设计
aa_refolded = rf3_output.atom_array    # RF3基于"未设计序列"预测的结构

# 修正后
designed_structure = mpnn_outputs[i].atom_array   # 真正的MPNN设计结果
input_structure = InferenceInput.from_atom_array(
    designed_structure, example_id=f"design_{i}"
```



**修复前后对比**：

| 指标    | 修复前          | 修复后（Design 0/1/2，见 results/design_summary.md） |
| ------- | --------------- | ---------------------------------------------------- |
| CA-RMSD | 10.56 ~ 38.19 Å | 0.80 ~ 0.91 Å                                        |
| pLDDT   | ~0.73           | ~0.83                                                |
| PAE     | ~13-16 Å        | ~2.0-2.5 Å                                           |
| pTM     | ~0.55-0.64      | ~0.89-0.90                                           |

> 注：由于MPNN序列采样具有随机性（未固定该阶段的随机种子），不同批次运行的具体数值会有小幅波动，但均稳定落在 RMSD < 1.0 Å 
> 的"Excellent designability"区间内，说明该backbone的设计成功率稳定可靠，而非偶然的单次结果。

完整排查过程详见 [PITFALLS.md](./PITFALLS.md)，完整数据见 [results/design_summary.md](./results/design_summary.md)。



## 仓库结构

```
├── scripts/
│   ├── 01_check_rfd3_backbone.py       # 验证RFD3骨架生成
│   ├── 02_check_mpnn_design.py         # 验证MPNN序列设计
│   └── 03_full_pipeline_with_fix.py    # 完整闭环流程（含bug修复）
├── results/
│   ├── design_summary.csv              # 各design的量化指标汇总
│   └── structures/                     # 关键结构文件(.cif)
├── PITFALLS.md                         # 完整踩坑记录
└── README.md
```



## 环境要求

- Python 3.12
- [RosettaCommons/foundry](https://github.com/RosettaCommons/foundry)
  （按官方README安装 `rfd3`、`mpnn`、`rf3` 三个模块及对应权重）
- GPU（本项目在 NVIDIA RTX 5060 Ti 上验证，使用 bfloat16 AMP）



## 复现步骤

```
python scripts/01_check_rfd3_backbone.py   # 生成80残基无条件骨架
python scripts/02_check_mpnn_design.py     # 设计对应氨基酸序列
python scripts/03_full_pipeline_with_fix.py # 完整验证+RMSD计算
```



## 结果

三组独立MPNN设计序列，经RF3重新折叠验证后，CA-RMSD均低于0.91Å，pTM均超过0.88，按官方notebook自定义标准（<1.0Å为"Excellent"）
均达到最高designability等级。由于MPNN序列采样具有随机性（该阶段未固定随机种子），不同批次运行的具体数值存在小幅波动，但均稳定落在Excellent区间内，说明该backbone的设计成功率稳定可靠。详细数据见 [results/design_summary.md](./results/design_summary.md)。



## 后续计划（Phase 2，进行中）

针对真实蛋白靶点（泛素 Ubiquitin, PDB: 1UBQ）的 Ile44 疏水膜片（由 Leu8 / Ile44 / His68 / Val70 构成，是天然泛素结合结构域UBD
识别泛素的核心界面），设计能特异性结合该区域的迷你binder蛋白，并通过完整pipeline验证其可设计性与结合特异性。



## 致谢

基于 [RosettaCommons/foundry](https://github.com/RosettaCommons/foundry)
开源项目，模型来自华盛顿大学 Institute for Protein Design。



