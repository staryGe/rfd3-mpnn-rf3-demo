# 踩坑记录 (Pitfalls & Debugging Log)

记录在搭建 RFdiffusion3 + ProteinMPNN + RF3 pipeline 过程中遇到的真实问题、排查过程与解决方案。按时间顺序排列。

---

## 1. 输入路径必须为绝对路径

**报错**：

```
ValueError: Input path is relative, but no base path was provided to resolve it against.
```

**原因**：
通过 Python API 调用 RFD3 时，内部数据加载逻辑（`datasets.py` 中的`ensure_input_is_abspath` 函数）明确要求输入 PDB 路径为绝对路径，
不能是相对路径。这与通过 CLI 方式（`rfd3 design ...`）运行时的行为不同——CLI 可能在其他层面对路径做了预处理。

**解决**：
使用 `os.path.abspath()` 将相对路径自动转换为绝对路径，避免手动拼写完整路径时出错。

---

## 2. `fixed_chains` 与 `designed_chains` 互斥

**报错**：

```
ValueError: Cannot set both fixed_chains and designed_chains.
```

**原因**：
通过查阅源码（`mpnn/utils/inference.py` 中的`MPNN_PER_INPUT_INFERENCE_DEFAULTS`）确认，`fixed_residues` /
`designed_residues` / `fixed_chains` / `designed_chains` 这四个参数属于同一个互斥组（`mutually_exclusive_group`），不能同时设置。
指定其中一个后，程序自动将结构中其余未被提及的链/残基，视为相反状态处理。

**解决**：
只保留 `designed_chains: ["B"]`，其余链（如泛素链 A）自动被视为固定，无需显式声明 `fixed_chains`。

---

## 3. 官方文档存在缺失，需通过源码反查参数

**现象**：
`foundry` 仓库 `mpnn` 模块的官方 README 中，"Command Line Inference"、"JSON-based Inference"、"Programmatic (Scripted)
Inference" 三个章节均标注为 "Detailed documentation coming soon!"，且明确声明 "API Instability: We are currently finalizing some
cleanup work on the inference API"。这意味着该模块的输入接口文档在当前版本下并不完整。

**排查方法**：
直接通过 `grep` 定位源码中的默认参数字典：

```bash
grep -n "MPNN_PER_INPUT_INFERENCE_DEFAULTS" -B 2 -A 40 \
  foundry/models/mpnn/src/mpnn/utils/inference.py
```

从字典定义与对应的 CLI argparse 参数说明中，反推出完整的可用字段列表（包括 `fixed_chains`、`designed_chains`、`bias`、`temperature`、`symmetry_residues` 等），弥补了官方文档的缺失。

**启示**：
面对文档不完整的前沿开源项目，源码中的默认配置字典 + argparse 参数定义，通常是比 README 更可靠、更实时的"事实文档"。



## 4. 【核心发现】官方示例 Notebook 中 RF3 验证环节存在变量引用错误

**现象**：
按照官方 end-to-end notebook（RFD3 → MPNN → RF3）原始代码跑完整个流程后，得到的 backbone RMSD 异常偏高（10.56 ~ 38.19 Å），
远超正常设计应有的 < 2 Å 阈值；同时 pLDDT（~0.73）、 PAE（~13-16 Å）、pTM（~0.55-0.64）等置信度指标也普遍偏低。

**排查过程**：
将 pipeline 拆解为 Section 1（RFD3 生成 backbone）、Section 2（MPNN 设计序列）、Section 3（RF3 验证）三个独立脚本，逐段打印
中间产物（链数、残基数、序列内容等）进行验证：

- Section 1：backbone 为 80 残基单链，含正常二级结构（螺旋）→ 正常
- Section 2：MPNN 输出序列长度匹配、氨基酸种类分布正常 → 正常
- Section 3：RMSD 异常 → 问题定位于此

进一步追踪变量关系，定位到以下代码：

```
# 官方 notebook 原始代码
input_structure = InferenceInput.from_atom_array(
    atom_array, example_id="example_protein"
)
...
aa_generated = atom_array              # Original RFD3 backbone (Section 1)
aa_refolded = rf3_output.atom_array    # RF3-predicted structure
```



**原因**：
变量 `atom_array` 自 Section 1 定义后从未被重新赋值为 MPNN 设计结果。Section 3 实际送入 RF3 验证的，仍是 RFD3 生成的原始骨架
（序列为未设计状态），而非 MPNN 真正设计出的、带有具体氨基酸序列的结构（该结果存储于 `mpnn_outputs[i].atom_array` 中）。

由于 RF3 是根据序列信息预测结构，喂入未设计的序列会导致预测结构与原始骨架几乎无关，因而 RMSD 异常偏高。

**判断依据**：
该问题并非本地环境或个人操作导致，而是官方 notebook 本身存在的逻辑疏漏，与 README 中 "API Instability... input formats and
outputs to stabilize in the upcoming weeks" 的警示相印证。



**解决**：
将送入 RF3 的输入，由原始 `atom_array` 修正为 MPNN 输出：

```
# 修正后
designed_structure = mpnn_outputs[i].atom_array
input_structure = InferenceInput.from_atom_array(
    designed_structure, example_id=f"design_{i}"
)
```



**验证结果**：

| 指标    | 修正前          | 修正后        |
| ------- | --------------- | ------------- |
| CA-RMSD | 10.56 ~ 38.19 Å | 0.44 ~ 0.50 Å |
| pLDDT   | ~0.73           | ~0.83         |
| PAE     | ~13-16 Å        | ~2.0 Å        |
| pTM     | ~0.55-0.64      | ~0.91         |



修正后三组独立设计（design_0/1/2）的 CA-RMSD 均低于 0.5 Å，pTM 均超过 0.9，按 notebook 自定义标准（<1.0 Å 为 Excellent）
均达到最高 designability 等级，证实该 bug 是导致此前验证失败的唯一根源，环境与模型本身均无问题。



