"""测试动态导入"""
import sys
from pathlib import Path
import importlib.util

# 修复 Windows 终端编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

print("[测试] 开始动态导入...", flush=True)
sys.stdout.flush()

try:
    spec = importlib.util.spec_from_file_location(
        "generate_platinum_centroids",
        Path("tools/generate_platinum_centroids.py")
    )
    print("[测试] spec 创建成功", flush=True)
    sys.stdout.flush()
    
    module = importlib.util.module_from_spec(spec)
    print("[测试] module 创建成功", flush=True)
    sys.stdout.flush()
    
    spec.loader.exec_module(module)
    print("[测试] 模块执行完成", flush=True)
    sys.stdout.flush()
    
    generate_platinum_centroids = module.generate_platinum_centroids
    print("[测试] ✅ 函数获取成功", flush=True)
    sys.stdout.flush()
    print(f"[测试] 函数类型: {type(generate_platinum_centroids)}", flush=True)
    sys.stdout.flush()
except Exception as e:
    print(f"[ERROR] 导入失败: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.stdout.flush()

