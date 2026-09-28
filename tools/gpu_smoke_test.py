"""prime-rl GPU runtime smoke test: torch + CUDA + RTX 4060 + tensor math."""
import torch

print(f"torch version:          {torch.__version__}")
print(f"cuda build version:     {torch.version.cuda}")
print(f"cuda available:         {torch.cuda.is_available()}")
assert torch.cuda.is_available(), "CUDA not available!"

props = torch.cuda.get_device_properties(0)
print(f"gpu name:               {props.name}")
print(f"gpu arch (compute):     {props.major}.{props.minor}")
print(f"memory total:           {props.total_memory / (1024 ** 3):.1f} GiB")
assert "4060" in props.name, f"Expected RTX 4060, got {props.name}"

x = torch.randn(4096, 4096, device="cuda")
y = torch.randn(4096, 4096, device="cuda")
z = x @ y
torch.cuda.synchronize()
print(f"matrix 4096x4096:       shape={tuple(z.shape)} dtype={z.dtype} mean={z.mean().item():.4f}")

out = torch.relu(x + y).sum()
torch.cuda.synchronize()
print(f"elementwise op:         sum={out.item():.4f} device={out.device}")

torch.cuda.empty_cache()
print(f"device count:           {torch.cuda.device_count()}")
print("SMOKE TEST OK")
