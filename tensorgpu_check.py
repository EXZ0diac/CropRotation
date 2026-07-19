import tensorflow as tf
import subprocess
import sys

print('Python executable:', sys.executable)
print('tf.__version__:', tf.__version__)
print('tf.test.is_built_with_cuda():', tf.test.is_built_with_cuda())
print('Physical devices (all):', tf.config.list_physical_devices())
print('Physical GPUs:', tf.config.list_physical_devices('GPU'))
print('\nTrying nvidia-smi...')
try:
    out = subprocess.check_output(['nvidia-smi'], stderr=subprocess.STDOUT, timeout=5)
    print(out.decode())
except Exception as e:
    print('nvidia-smi failed:', e)
