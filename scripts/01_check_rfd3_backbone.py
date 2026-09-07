# check_step1_rfd3.py

from lightning.fabric import seed_everything
from rfd3.engine import RFD3InferenceConfig, RFD3InferenceEngine
from biotite.structure.io.pdbx import CIFFile, set_structure

# 固定随机种子，保证可复现
seed_everything(0)

# 配置：完全无条件生成，80残基
config = RFD3InferenceConfig(
    specification={
        'length': 80,
        'extra': {},
    },
    diffusion_batch_size=2,
)

# 初始化并运行
model = RFD3InferenceEngine(**config)
outputs = model.run(
    inputs=None,
    out_dir=None,
    n_batches=1,
)

print("=== Output keys ===")
print(list(outputs.keys()))

for idx, data in outputs.items():
    print(f"\nBatch {idx}: {len(data)} structure(s)")
    atom_array = data[0].atom_array

    # ---- 关键诊断信息 ----
    chains = set(atom_array.chain_id)
    n_atoms = len(atom_array)
    import numpy as np
    res_ids = np.unique(atom_array.res_id[atom_array.chain_id == list(chains)[0]])

    print(f"  Chains present: {chains}")
    print(f"  Total atoms: {n_atoms}")
    print(f"  Residue count (first chain): {len(res_ids)}")

    # ---- 保存到硬盘，方便用PyMOL肉眼检查 ----
    out_path = f"check_backbone_batch{idx}_struct0.cif"
    cif_file = CIFFile()
    set_structure(cif_file, atom_array)
    cif_file.write(out_path)
    print(f"  Saved to: {out_path}")

print("\n=== Done. Please inspect the .cif file(s) in PyMOL. ===")
