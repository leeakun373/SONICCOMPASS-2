"""快速测试导入是否正常"""
import sys
from pathlib import Path

# 修复 Windows 终端编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

print("测试导入...", flush=True)
sys.stdout.flush()

try:
    from tools.generate_platinum_centroids import generate_platinum_centroids
    print("✅ 成功导入 generate_platinum_centroids", flush=True)
except Exception as e:
    print(f"❌ 导入失败: {e}", flush=True)
    import traceback
    traceback.print_exc()

try:
    import umap
    print("✅ 成功导入 umap", flush=True)
except Exception as e:
    print(f"❌ 导入 umap 失败: {e}", flush=True)

try:
    from sklearn.preprocessing import LabelEncoder
    print("✅ 成功导入 LabelEncoder", flush=True)
except Exception as e:
    print(f"❌ 导入 LabelEncoder 失败: {e}", flush=True)

try:
    from data import SoundminerImporter
    print("✅ 成功导入 SoundminerImporter", flush=True)
except Exception as e:
    print(f"❌ 导入 SoundminerImporter 失败: {e}", flush=True)

try:
    from core import DataProcessor, VectorEngine
    print("✅ 成功导入 DataProcessor 和 VectorEngine", flush=True)
except Exception as e:
    print(f"❌ 导入失败: {e}", flush=True)
    import traceback
    traceback.print_exc()

print("测试完成", flush=True)
sys.stdout.flush()

