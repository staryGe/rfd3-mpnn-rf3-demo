# 设计结果汇总 (Design Summary)

流程：RFD3生成80残基unconditional backbone → MPNN设计3组候选序列 → RF3重新折叠验证 → 与原始backbone计算CA-RMSD

评判标准（沿用notebook定义）：RMSD < 1.0Å = Excellent，< 2.0Å = Good

| Design | pLDDT | PAE (Å) | pTM   | Ranking Score | Has Clash | CA-RMSD (Å) | 评级      |
| ------ | ----- | ------- | ----- | ------------- | --------- | ----------- | --------- |
| 0      | 0.834 | 2.31    | 0.899 | 0.180         | False     | 0.802       | Excellent |
| 1      | 0.825 | 2.11    | 0.903 | 0.181         | False     | 0.878       | Excellent |
| 2      | 0.837 | 2.49    | 0.885 | 0.177         | False     | 0.912       | Excellent |

**结论**：三组独立采样的设计序列，经RF3重新折叠后均与原始RFD3生成的 backbone高度吻合（RMSD均<1.0Å，pTM均>0.88），证明该80残基backbone
具有良好的designability，MPNN设计出的序列能够可靠地折叠回预期结构。

对应结构文件见 `structures/` 目录。



