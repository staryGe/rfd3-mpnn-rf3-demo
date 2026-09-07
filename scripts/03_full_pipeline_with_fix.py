# check_step3_rf3_full.py

import numpy as np
from lightning.fabric import seed_everything
from rfd3.engine import RFD3InferenceConfig, RFD3InferenceEngine
from mpnn.inference_engines.mpnn import MPNNInferenceEngine
from rf3.inference_engines.rf3 import RF3InferenceEngine
from rf3.utils.inference import InferenceInput
from biotite.structure import superimpose, rmsd
from biotite.sequence import ProteinSequence
from biotite.structure import get_residue_starts

# ---- Step 1: Backbone生成（复现基准）----
seed_everything(0)
config = RFD3InferenceConfig(specification={'length': 80, 'extra': {}}, diffusion_batch_size=2)
model = RFD3InferenceEngine(**config)
outputs = model.run(inputs=None, out_dir=None, n_batches=1)
first_key = next(iter(outputs.keys()))
backbone_atom_array = outputs[first_key][0].atom_array
print(f"[1] Backbone: {len(set(backbone_atom_array.chain_id))} chain(s), {len(backbone_atom_array)} atoms")

# ---- Step 2: MPNN序列设计 ----
engine_config = {
    "model_type": "ligand_mpnn",
    "is_legacy_weights": True,
    "out_directory": None,
    "write_structures": False,
    "write_fasta": False,
}
input_configs = [{"batch_size": 3, "remove_waters": True}]
mpnn_model = MPNNInferenceEngine(**engine_config)
mpnn_outputs = mpnn_model.run(input_dicts=input_configs, atom_arrays=[backbone_atom_array])
print(f"[2] MPNN generated {len(mpnn_outputs)} sequences")

# ---- Step 3: RF3验证 —— 注意用 mpnn_outputs 的结果，不是原始 backbone ----
inference_engine = RF3InferenceEngine(ckpt_path='rf3', verbose=False)

for i, mpnn_item in enumerate(mpnn_outputs):
    designed_structure = mpnn_item.atom_array   # ← 关键：用MPNN的输出

    input_structure = InferenceInput.from_atom_array(
        designed_structure, example_id=f"design_{i}"
    )
    rf3_outputs = inference_engine.run(inputs=input_structure)
    rf3_output = rf3_outputs[f"design_{i}"][0]

    summary = rf3_output.summary_confidences
    predicted_structure = rf3_output.atom_array

    # ---- 计算RMSD：只用CA原子做superposition ----
    backbone_ca = backbone_atom_array[backbone_atom_array.atom_name == "CA"]
    predicted_ca = predicted_structure[predicted_structure.atom_name == "CA"]

    if len(backbone_ca) != len(predicted_ca):
        print(f"  [WARNING] CA count mismatch: backbone={len(backbone_ca)}, predicted={len(predicted_ca)}")
        continue

    fitted, transform = superimpose(backbone_ca, predicted_ca)
    ca_rmsd = rmsd(backbone_ca, fitted)

    print(f"\n=== Design {i} ===")
    print(f"  pLDDT:  {summary['overall_plddt']:.3f}")
    print(f"  PAE:    {summary['overall_pae']:.2f} A")
    print(f"  pTM:    {summary['ptm']:.3f}")
    print(f"  Ranking score: {summary['ranking_score']:.3f}")
    print(f"  Has clash: {summary['has_clash']}")
    print(f"  CA-RMSD to original backbone: {ca_rmsd:.3f} A   ← 关键指标")
