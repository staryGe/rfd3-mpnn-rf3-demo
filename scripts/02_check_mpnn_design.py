# check_step2_mpnn.py

from lightning.fabric import seed_everything
from rfd3.engine import RFD3InferenceConfig, RFD3InferenceEngine
from mpnn.inference_engines.mpnn import MPNNInferenceEngine
from biotite.sequence import ProteinSequence
from biotite.structure import get_residue_starts

# ---- Step 1: 复现刚才验证过的 backbone 生成 ----
seed_everything(0)

config = RFD3InferenceConfig(
    specification={'length': 80, 'extra': {}},
    diffusion_batch_size=2,
)
model = RFD3InferenceEngine(**config)
outputs = model.run(inputs=None, out_dir=None, n_batches=1)

first_key = next(iter(outputs.keys()))
atom_array = outputs[first_key][0].atom_array

print(f"Backbone confirmed: {len(set(atom_array.chain_id))} chain(s), "
      f"{len(atom_array)} atoms")

# ---- Step 2: MPNN 序列设计（原始官方demo参数，无binder条件）----
engine_config = {
    "model_type": "ligand_mpnn",
    "is_legacy_weights": True,
    "out_directory": None,
    "write_structures": False,
    "write_fasta": False,
}

input_configs = [
    {
        "batch_size": 3,
        "remove_waters": True,
    }
]

mpnn_model = MPNNInferenceEngine(**engine_config)
mpnn_outputs = mpnn_model.run(input_dicts=input_configs, atom_arrays=[atom_array])

print(f"\nGenerated {len(mpnn_outputs)} designed sequences:\n")
for i, item in enumerate(mpnn_outputs):
    res_starts = get_residue_starts(item.atom_array)
    seq_1letter = ''.join(
        ProteinSequence.convert_letter_3to1(res_name)
        for res_name in item.atom_array.res_name[res_starts]
    )
    print(f"Sequence {i+1} (len={len(seq_1letter)}): {seq_1letter}")
