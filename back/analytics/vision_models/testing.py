#pip uninstall torch torchvision torchaudio
#pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
import torch
print(torch.__version__)
print(torch.cuda.is_available())
print(torch.version.cuda)