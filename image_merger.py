"""
图片工具箱：竖向拼接 + 智能重命名
- 拼接：按文件名自然排序，将文件夹下所有图片居中竖向拼接为一张 PNG。
- 重命名：智能清理文件名，格式化数字后缀为两位数。
用法：
    python image_merger.py                  → 终端交互菜单
    python image_merger.py <文件夹路径>      → 直接拼接（默认文件名）
    python image_merger.py <文件夹路径> <输出文件名> → 直接拼接（指定文件名）
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from PIL import Image

# ============================================================
#  支持的图片格式
# ============================================================
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff", ".tif"}


# ============================================================
#  自然排序工具
# ============================================================
def natural_sort_key(name: str) -> list:
    """
    将文件名拆分为文本段和数字段，实现自然排序。
    例如: ['img', 2, '.png'] < ['img', 10, '.png']
    """
    parts = re.split(r"(\d+)", name)
    result = []
    for part in parts:
        if part.isdigit():
            result.append(int(part))
        else:
            result.append(part.lower())
    return result


# ============================================================
#  核心拼接逻辑
# ============================================================
def merge_images(folder_path: str, output_name: str = "merged_output.png") -> str:
    """
    将文件夹内所有图片按文件名自然排序后，居中竖向拼接。

    参数:
        folder_path : 图片所在文件夹路径
        output_name : 输出文件名（仅文件名，不含路径）

    返回:
        输出文件的完整路径

    异常:
        FileNotFoundError : 文件夹不存在
        ValueError        : 文件夹内无支持的图片
    """
    folder = Path(folder_path).resolve()

    if not folder.exists():
        raise FileNotFoundError(f"文件夹不存在: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"路径不是文件夹: {folder}")

    # 1. 收集所有支持的图片文件，按自然排序
    image_files = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
            image_files.append(f)

    if not image_files:
        raise ValueError(f"文件夹内没有找到支持的图片文件\n支持的格式: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    image_files.sort(key=lambda f: natural_sort_key(f.name))

    # 2. 加载所有图片
    images: list[Image.Image] = []
    print(f"\n找到 {len(image_files)} 张图片，正在加载...")
    for i, fp in enumerate(image_files, 1):
        img = Image.open(fp)
        # 统一转换为 RGBA 以支持透明通道
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        images.append(img)
        print(f"  [{i}/{len(image_files)}] {fp.name}  ({img.width}×{img.height})")

    # 3. 计算最大宽度
    max_width = max(img.width for img in images)

    # 4. 将每张图片居中放置到 max_width 宽的透明画布上
    padded_images: list[Image.Image] = []
    print(f"\n最大宽度: {max_width}px，正在居中处理...")
    for i, img in enumerate(images, 1):
        if img.width == max_width:
            padded_images.append(img)
            print(f"  [{i}/{len(images)}] {image_files[i-1].name}  — 已是最大宽度，无需调整")
        else:
            canvas = Image.new("RGBA", (max_width, img.height), (0, 0, 0, 0))
            offset_x = (max_width - img.width) // 2
            canvas.paste(img, (offset_x, 0), img)  # 使用 img 自身作为 mask 保留透明
            padded_images.append(canvas)
            print(f"  [{i}/{len(images)}] {image_files[i-1].name}  — 居中偏移 {offset_x}px")

    # 5. 计算总高度并拼接
    total_height = sum(img.height for img in padded_images)
    merged = Image.new("RGBA", (max_width, total_height), (0, 0, 0, 0))

    y_offset = 0
    print(f"\n总高度: {total_height}px，正在拼接...")
    for i, img in enumerate(padded_images, 1):
        merged.paste(img, (0, y_offset), img)
        y_offset += img.height
        # 进度百分比
        pct = i * 100 // len(padded_images)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"  [{bar}] {pct}%", end="\r")
    print()  # 换行

    # 6. 保存
    output_path = folder / output_name
    merged.save(output_path, "PNG")
    print(f"\n✅ 拼接完成！")
    print(f"   输出文件: {output_path}")
    print(f"   图片尺寸: {max_width} × {total_height}")
    print(f"   文件大小: {output_path.stat().st_size / 1024:.1f} KB")

    return str(output_path)


# ============================================================
#  智能重命名逻辑
# ============================================================
def rename_images(folder_path: str, preview: bool = True) -> tuple:
    """
    智能重命名文件夹内的图片文件。
    - 清理文件名首尾空格
    - 去除前缀末尾的空格、下划线、横杠
    - 将数字后缀格式化为两位数 (如 img 5 -> img05)
    - 无数字后缀时追加 01

    参数:
        folder_path : 文件夹路径
        preview     : True=仅预览, False=正式重命名

    返回:
        (成功数, 跳过数)
    """
    folder = Path(folder_path).resolve()
    if not folder.exists():
        raise FileNotFoundError(f"文件夹不存在: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"路径不是文件夹: {folder}")

    exts = {'.jpg', '.png', '.jpeg', '.gif', '.bmp', '.webp'}
    files = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in exts]

    if not files:
        print("📭 未发现支持的图片文件。")
        return 0, 0

    error_log = folder / "error.txt"
    success_count = 0
    skip_count = 0

    print(f"\n共找到 {len(files)} 张图片，正在分析...\n")

    for file in files:
        name = file.stem.strip()
        ext = file.suffix

        try:
            # 正则匹配：前缀 + 尾部数字
            m = re.match(r'^(.*?)(\d+)$', name)
            if m:
                prefix = m.group(1).rstrip(' _-')
                num = int(m.group(2))
                new_name = f"{prefix}{num:02d}{ext}"
            else:
                clean_name = name.rstrip(' _-')
                new_name = f"{clean_name}01{ext}"

            new_path = folder / new_name

            if file.resolve() != new_path.resolve():
                if preview:
                    print(f"  拟重命名: {file.name}  ->  {new_name}")
                    success_count += 1
                else:
                    if not new_path.exists():
                        file.rename(new_path)
                        print(f"  ✅ 成功: {file.name}  ->  {new_name}")
                        success_count += 1
                    else:
                        print(f"  ⏭ 跳过: {new_name} (目标已存在)")
                        skip_count += 1
        except Exception as e:
            error_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 错误: 无法修改文件 {file.name} - {e}"
            print(f"  ❌ {error_msg}")
            try:
                with open(error_log, 'a', encoding='utf-8') as f:
                    f.write(error_msg + '\n')
            except Exception:
                pass

    return success_count, skip_count


# ============================================================
#  终端交互菜单
# ============================================================
def interactive_menu():
    """终端交互模式"""
    folder_path = ""
    output_name = "merged_output.png"

    while True:
        print("\n" + "=" * 50)
        print("         📷 图片工具箱")
        print("=" * 50)
        print(f"  当前文件夹: {folder_path or '(未选择)'}")
        print(f"  输出文件名: {output_name}")
        print("-" * 50)
        print("  1. 选择文件夹")
        print("  2. 预览图片列表")
        print("  3. 设置输出文件名")
        print("  4. 🚀 开始拼接")
        print("  5. 🔧 智能重命名")
        print("  0. 退出")
        print("-" * 50)
        choice = input("请选择操作 [0-5]: ").strip()

        if choice == "0":
            print("👋 再见！")
            break
        elif choice == "1":
            path_input = input("请输入文件夹路径（或拖拽文件夹到此处）: ").strip().strip('"').strip("'")
            p = Path(path_input)
            if p.exists() and p.is_dir():
                folder_path = str(p.resolve())
                print(f"✅ 已选择: {folder_path}")
            else:
                print(f"❌ 路径无效或不是文件夹: {path_input}")
        elif choice == "2":
            if not folder_path:
                print("❌ 请先选择文件夹！")
                continue
            folder = Path(folder_path)
            files = sorted(
                [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS],
                key=lambda f: natural_sort_key(f.name),
            )
            if not files:
                print("📭 文件夹内没有支持的图片文件")
            else:
                print(f"\n共 {len(files)} 张图片:\n")
                for i, f in enumerate(files, 1):
                    try:
                        with Image.open(f) as img:
                            info = f"{img.width}×{img.height}"
                    except Exception:
                        info = "无法读取"
                    print(f"  {i:>3}. {f.name}  ({info})")
        elif choice == "3":
            new_name = input(f"请输入输出文件名 (当前: {output_name}): ").strip()
            if new_name:
                if not new_name.lower().endswith(".png"):
                    new_name += ".png"
                output_name = new_name
                print(f"✅ 输出文件名已设为: {output_name}")
        elif choice == "4":
            if not folder_path:
                print("❌ 请先选择文件夹！")
                continue
            try:
                merge_images(folder_path, output_name)
            except Exception as e:
                print(f"\n❌ 拼接失败: {e}")
        elif choice == "5":
            if not folder_path:
                print("❌ 请先选择文件夹！")
                continue
            print("\n--- 智能重命名 ---")
            print("  [1] 预览模式 (仅查看结果，不修改文件)")
            print("  [2] 正式重命名 (直接修改文件)")
            print("  [0] 返回")
            sub = input("请选择 [0-2]: ").strip()
            if sub == "0":
                continue
            elif sub == "1":
                print("\n--- 预览模式 ---")
                try:
                    rename_images(folder_path, preview=True)
                except Exception as e:
                    print(f"\n❌ 预览失败: {e}")
            elif sub == "2":
                confirm = input("\n⚠ 确认要正式重命名所有文件吗？(输入 y 确认): ").strip().lower()
                if confirm == 'y':
                    print("\n--- 正式重命名 ---")
                    try:
                        success, skip = rename_images(folder_path, preview=False)
                        print(f"\n✅ 重命名完成！成功: {success}, 跳过: {skip}")
                    except Exception as e:
                        print(f"\n❌ 重命名失败: {e}")
                else:
                    print("已取消。")
            else:
                print("❌ 无效选项")
        else:
            print("❌ 无效选项，请输入 0-5")


# ============================================================
#  入口
# ============================================================
if __name__ == "__main__":
    args = sys.argv[1:]

    if len(args) >= 1:
        # 命令行模式
        folder = args[0]
        out = args[1] if len(args) >= 2 else "merged_output.png"
        if not out.lower().endswith(".png"):
            out += ".png"
        try:
            merge_images(folder, out)
        except Exception as e:
            print(f"❌ 错误: {e}")
            sys.exit(1)
    else:
        # 交互菜单模式
        interactive_menu()
