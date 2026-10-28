# GPU Power Sweep

**NVIDIA GPUs ONLY. LINUX ONLY.**

**WARNING: USE AT YOUR OWN RISK.** This tool temporarily changes NVIDIA GPU power limits using `sudo nvidia-smi`. The author accepts no responsibility for hardware damage, instability, data loss, or other consequences of using or modifying these scripts. Verify what you run on your own system. Provided **AS IS**, without warranty. See `LICENSE`.

A deliberately small, hackable collection of Bash scripts for comparing ComfyUI image-generation times at different GPU power limits. No installer, no configuration framework, no multi-GPU support.

Tested on a **single NVIDIA RTX 3080** under Linux. Other NVIDIA cards may work, but have not been validated here. **GPU 0** is used by default; ensure ComfyUI uses the same GPU if you have several.

## Requirements

- A working NVIDIA driver and `nvidia-smi` with permission to change power limits via `sudo`
- Bash, `awk`, `jq`, `curl`, `zip`, `sudo`, and `mktemp`
- **ComfyUI already running** with its API at `http://127.0.0.1:8188`
- A compatible **API-format** ComfyUI workflow saved as `teapot_api.json`

This project does not install or configure ComfyUI. The included workflow is a Qwen Image 2.1 example and needs the matching models and custom nodes; replace it with your own API-exported workflow if necessary. `teapot.sh` currently changes the seed of all `KSampler` nodes and expects a generated image in ComfyUI's history output.

## Run

```bash
chmod +x *.sh
./batch-run.sh
```

`batch-run.sh` queries GPU 0 for its supported power range, starts at approximately **60% of the maximum** (rounded up to a 10 W step and clamped to hardware minimum), and tests in **10 W steps** through the hardware maximum. It includes the exact maximum as a final point if needed. No GPU-model tables or manually entered maximum wattage.

**WARNING: Each run deletes and recreates `./output/`.** Copy anything you wish to keep first. Earlier `results-*.zip` archives are not deleted.

The run writes `output/results.csv` and images to `output/`, then creates a timestamped `results-*.zip` in this folder. Temporary workflow files are also created and removed here. ComfyUI itself may still save images and internal data in its own configured directories.

## Change settings

Edit the scripts directly:

| File | Setting | Default |
| --- | --- | --- |
| `batch-run.sh` | `START_PERCENT` | `60` |
| `batch-run.sh` | `STEP` | `10` watts |
| `batch-run.sh` and `gpu-load-lock.sh` | `GPU` | `0` |
| `teapot.sh` | `API` | `http://127.0.0.1:8188` |
| `teapot.sh` | `WORKFLOW` | `teapot_api.json` |

The scripts intentionally do not auto-configure multiple GPUs. To modify them for such a setup, know which GPU your ComfyUI server actually uses.

## How it works

- `gpu-load-lock.sh`: set a temporary power limit, run any command, restore the old limit on exit.
- `teapot.sh`: submit an API workflow to ComfyUI, wait for completion, save the image and elapsed wall-clock time.
- `batch-run.sh`: choose a sweep range, call the other scripts, and archive the results.

The reported wattage is a **power limit, not measured consumption**. The CSV measures end-to-end elapsed time for one image per power limit; it does **not** measure joules, electricity cost, or statistically validated performance. Results can be affected by warm-up, background processes, temperatures, and the workflow itself.

## License

MIT. See `LICENSE`.
