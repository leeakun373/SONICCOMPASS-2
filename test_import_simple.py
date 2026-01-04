"""简单测试导入"""
import sys
from pathlib import Path

# 修复 Windows 终端编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

print("[1] 开始测试...", flush=True)
sys.stdout.flush()

sys.path.insert(0, str(Path(__file__).parent))
print("[2] sys.path 已设置", flush=True)
sys.stdout.flush()

print("[3] 准备导入 generate_platinum_centroids...", flush=True)
sys.stdout.flush()

try:
    from tools.generate_platinum_centroids import generate_platinum_centroids
    print("[4] ✅ 导入成功！", flush=True)
    sys.stdout.flush()
    print(f"[5] 函数类型: {type(generate_platinum_centroids)}", flush=True)
    sys.stdout.flush()
except Exception as e:
    print(f"[ERROR] 导入失败: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.stdout.flush()

