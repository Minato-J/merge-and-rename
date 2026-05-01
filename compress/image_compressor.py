"""
图片压缩工具：批量有损压缩
- 支持 JPEG 质量调节、分辨率缩放、WebP 格式转换
- 输出到源文件夹内的 compressed/ 子文件夹，不覆盖原始文件
用法：
    python image_compressor.py                      → 终端交互菜单
    python image_compressor.py <文件夹路径>           → 快速压缩（默认参数）
    python image_compressor.py <文件夹路径> <质量>     → 指定质量（1-100）
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
#  输出格式选项
# ============================================================
OUTPUT_FORMATS = {
    "original": "保持原格式",
    "jpeg": "JPEG (.jpg)",
    "webp": "WebP (.webp)",
}

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
#  获取友好文件大小
# ============================================================
def format_size(size_bytes: int) -> str:
    """将字节数转为可读的大小字符串"""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes} B"


# ============================================================
#  核心压缩逻辑
# ============================================================
def compress_images(
    folder_path: str,
    quality: int = 85,
    scale: int = 100,
    output_format: str = "original",
    output_subdir: str = "compressed",
) -> str:
    """
    批量压缩文件夹内所有图片。

    参数:
        folder_path   : 图片所在文件夹路径
        quality       : JPEG/WebP 压缩质量 (1-100)
        scale         : 缩放百分比 (1-100)，100 表示不缩放
        output_format : "original" / "jpeg" / "webp"
        output_subdir : 输出子文件夹名称

    返回:
        输出文件夹的完整路径

    异常:
        FileNotFoundError : 文件夹不存在
        ValueError        : 文件夹内无支持的图片或参数无效
    """
    folder = Path(folder_path).resolve()

    if not folder.exists():
        raise FileNotFoundError(f"文件夹不存在: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"路径不是文件夹: {folder}")

    # 验证参数
    if not 1 <= quality <= 100:
        raise ValueError(f"质量参数必须在 1-100 之间，当前值: {quality}")
    if not 1 <= scale <= 100:
        raise ValueError(f"缩放比例必须在 1-100 之间，当前值: {scale}")
    if output_format not in OUTPUT_FORMATS:
        raise ValueError(f"不支持的输出格式: {output_format}，可选: {', '.join(OUTPUT_FORMATS.keys())}")

    # 1. 收集所有支持的图片文件，按自然排序
    image_files = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
            image_files.append(f)

    if not image_files:
        raise ValueError(f"文件夹内没有找到支持的图片文件\n支持的格式: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    image_files.sort(key=lambda f: natural_sort_key(f.name))

    # 2. 创建输出子文件夹
    output_folder = folder / output_subdir
    output_folder.mkdir(exist_ok=True)

    # 3. 逐张处理
    total_original_size = 0
    total_compressed_size = 0
    success_count = 0
    skip_count = 0

    print(f"\n找到 {len(image_files)} 张图片，正在压缩...")
    print(f"  输出文件夹: {output_folder}")
    print(f"  压缩质量: {quality}")
    print(f"  缩放比例: {scale}%")
    print(f"  输出格式: {OUTPUT_FORMATS.get(output_format, output_format)}")
    print()

    for i, fp in enumerate(image_files, 1):
        original_size = fp.stat().st_size
        total_original_size += original_size

        try:
            img = Image.open(fp)

            # --- 处理 GIF 等多帧格式：取第一帧 ---
            if getattr(img, "is_animated", False):
                img.seek(0)

            original_mode = img.mode
            original_width, original_height = img.size

            # --- 缩放 ---
            if scale < 100:
                new_width = max(1, int(original_width * scale / 100))
                new_height = max(1, int(original_height * scale / 100))
                # 使用高质量重采样
                img = img.resize((new_width, new_height), Image.LANCZOS)

            # --- 确定输出格式和扩展名 ---
            src_ext = fp.suffix.lower()
            if output_format == "original":
                # 保持原格式：JPEG/WebP 用 quality，PNG/BMP/GIF/TIFF 原样保存
                if src_ext in (".jpg", ".jpeg"):
                    save_format = "JPEG"
                    save_ext = src_ext
                elif src_ext == ".webp":
                    save_format = "WEBP"
                    save_ext = ".webp"
                else:
                    # PNG / BMP / GIF / TIFF：转 JPEG 以应用有损压缩
                    save_format = "JPEG"
                    save_ext = ".jpg"
            elif output_format == "jpeg":
                save_format = "JPEG"
                save_ext = ".jpg"
            elif output_format == "webp":
                save_format = "WEBP"
                save_ext = ".webp"

            # --- 转换色彩模式 ---
            # JPEG 不支持 RGBA/PA/P 等模式，需转为 RGB
            # WebP 支持 RGBA，但有损模式下建议 RGB
            if save_format in ("JPEG", "WEBP"):
                if img.mode in ("RGBA", "LA", "PA", "P"):
                    # 有透明通道 → 填充白色背景
                    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode == "P":
                            img = img.convert("RGBA")
                        background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                        img = background
                    else:
                        img = img.convert("RGB")
                elif img.mode != "RGB":
                    img = img.convert("RGB")

            # --- 确定输出文件名 ---
            stem = fp.stem
            output_name = f"{stem}{save_ext}"
            output_path = output_folder / output_name

            # 防止覆盖：若同名文件已存在，追加序号
            counter = 1
            while output_path.exists():
                output_name = f"{stem}_{counter}{save_ext}"
                output_path = output_folder / output_name
                counter += 1

            # --- 保存 ---
            save_kwargs = {}
            if save_format == "JPEG":
                save_kwargs = {"quality": quality, "optimize": True}
            elif save_format == "WEBP":
                save_kwargs = {"quality": quality}

            img.save(output_path, save_format, **save_kwargs)

            compressed_size = output_path.stat().st_size
            total_compressed_size += compressed_size
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

            # 进度条
            pct = i * 100 // len(image_files)
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)

            size_info = f"{format_size(original_size)} → {format_size(compressed_size)}"
            if ratio > 0:
                size_info += f"  (减小 {ratio:.1f}%)"
            elif ratio < 0:
                size_info += f"  (增大 {abs(ratio):.1f}%)"

            dim_info = f"{original_width}×{original_height}"
            if scale < 100:
                dim_info += f" → {img.width}×{img.height}"

            print(f"  [{bar}] {pct:>3}%  {fp.name}  [{dim_info}]  {size_info}")
            success_count += 1

        except Exception as e:
            print(f"  ❌ 处理失败: {fp.name} — {e}")
            skip_count += 1

    # 4. 汇总
    print()
    print("=" * 60)
    print(f"✅ 压缩完成！")
    print(f"   成功: {success_count} 张  |  跳过: {skip_count} 张")
    print(f"   原始总大小: {format_size(total_original_size)}")
    print(f"   压缩后总大小: {format_size(total_compressed_size)}")
    if total_original_size > 0:
        total_ratio = (1 - total_compressed_size / total_original_size) * 100
        if total_ratio > 0:
            print(f"   总压缩率: {total_ratio:.1f}%  (节省 {format_size(total_original_size - total_compressed_size)})")
        elif total_ratio < 0:
            print(f"   总大小变化: +{abs(total_ratio):.1f}%")
    print(f"   输出文件夹: {output_folder}")
    print("=" * 60)

    return str(output_folder)


# ============================================================
#  预览图片列表
# ============================================================
def preview_images(folder_path: str):
    """列出文件夹内所有支持的图片及其尺寸"""
    folder = Path(folder_path).resolve()
    if not folder.exists() or not folder.is_dir():
        print("❌ 文件夹无效")
        return

    files = sorted(
        [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS],
        key=lambda f: natural_sort_key(f.name),
    )

    if not files:
        print("📭 文件夹内没有支持的图片文件")
        return

    total_size = 0
    print(f"\n共 {len(files)} 张图片:\n")
    for i, f in enumerate(files, 1):
        fsize = f.stat().st_size
        total_size += fsize
        try:
            with Image.open(f) as img:
                info = f"{img.width}×{img.height}  {img.mode}"
        except Exception:
            info = "无法读取"
        print(f"  {i:>3}. {f.name}  ({info})  {format_size(fsize)}")

    print(f"\n  总大小: {format_size(total_size)}")


# ============================================================
#  终端交互菜单
# ============================================================
def interactive_menu():
    """终端交互模式"""
    folder_path = ""
    quality = 85
    scale = 100
    output_format = "original"
    output_subdir = "compressed"

    while True:
        print("\n" + "=" * 50)
        print("         🗜 图片压缩工具箱")
        print("=" * 50)
        print(f"  当前文件夹: {folder_path or '(未选择)'}")
        print(f"  压缩质量: {quality} (1-100)")
        print(f"  缩放比例: {scale}%")
        print(f"  输出格式: {OUTPUT_FORMATS.get(output_format, output_format)}")
        print(f"  输出子文件夹: {output_subdir}")
        print("-" * 50)
        print("  1. 选择文件夹")
        print("  2. 设置压缩质量")
        print("  3. 设置缩放比例")
        print("  4. 设置输出格式")
        print("  5. 设置输出子文件夹名")
        print("  6. 预览图片列表")
        print("  7. 🚀 开始压缩")
        print("  0. 退出")
        print("-" * 50)
        choice = input("请选择操作 [0-7]: ").strip()

        if choice == "0":
            print("👋 再见！")
            break

        elif choice == "1":
            path_input = input("请输入文件夹路径（或拖拽文件夹到此处）: ").strip().strip('"').strip("'")
            p = Path(path_input)
            if p.exists() and p.is_dir():
                folder_path = str(p.resolve())
                print(f"✅ 已选择: {folder_path}")
                # 自动预览
                preview_images(folder_path)
            else:
                print(f"❌ 路径无效或不是文件夹: {path_input}")

        elif choice == "2":
            q_input = input(f"请输入压缩质量 1-100 (当前: {quality}): ").strip()
            try:
                q = int(q_input)
                if 1 <= q <= 100:
                    quality = q
                    print(f"✅ 压缩质量已设为: {quality}")
                else:
                    print("❌ 质量必须在 1-100 之间")
            except ValueError:
                print("❌ 请输入有效数字")

        elif choice == "3":
            s_input = input(f"请输入缩放比例 1-100 (当前: {scale}%): ").strip()
            try:
                s = int(s_input)
                if 1 <= s <= 100:
                    scale = s
                    if scale < 100:
                        print(f"✅ 缩放比例已设为: {scale}% (图片将缩小)")
                    else:
                        print(f"✅ 缩放比例已设为: {scale}% (保持原始尺寸)")
                else:
                    print("❌ 缩放比例必须在 1-100 之间")
            except ValueError:
                print("❌ 请输入有效数字")

        elif choice == "4":
            print("\n可选输出格式:")
            format_keys = list(OUTPUT_FORMATS.keys())
            for idx, key in enumerate(format_keys, 1):
                marker = " ← 当前" if key == output_format else ""
                print(f"  [{idx}] {OUTPUT_FORMATS[key]}{marker}")
            f_input = input("请选择格式编号: ").strip()
            try:
                f_idx = int(f_input)
                if 1 <= f_idx <= len(format_keys):
                    output_format = format_keys[f_idx - 1]
                    print(f"✅ 输出格式已设为: {OUTPUT_FORMATS[output_format]}")
                else:
                    print("❌ 无效的编号")
            except ValueError:
                print("❌ 请输入有效数字")

        elif choice == "5":
            new_subdir = input(f"请输入输出子文件夹名 (当前: {output_subdir}): ").strip()
            if new_subdir:
                # 清理非法字符
                cleaned = re.sub(r'[<>:"/\\|?*]', '_', new_subdir)
                if cleaned != new_subdir:
                    print(f"⚠ 已移除非法字符，使用: {cleaned}")
                output_subdir = cleaned.strip() or "compressed"
                print(f"✅ 输出子文件夹名已设为: {output_subdir}")

        elif choice == "6":
            if not folder_path:
                print("❌ 请先选择文件夹！")
                continue
            preview_images(folder_path)

        elif choice == "7":
            if not folder_path:
                print("❌ 请先选择文件夹！")
                continue
            print(f"\n确认压缩参数:")
            print(f"  文件夹: {folder_path}")
            print(f"  质量: {quality}")
            print(f"  缩放: {scale}%")
            print(f"  输出格式: {OUTPUT_FORMATS.get(output_format, output_format)}")
            print(f"  输出到: {folder_path}\\{output_subdir}\\")
            confirm = input("\n⚠ 开始压缩？(输入 y 确认): ").strip().lower()
            if confirm == 'y':
                try:
                    compress_images(folder_path, quality, scale, output_format, output_subdir)
                except Exception as e:
                    print(f"\n❌ 压缩失败: {e}")
            else:
                print("已取消")

        else:
            print("❌ 无效选项，请重新选择")


# ============================================================
#  入口
# ============================================================
if __name__ == "__main__":
    args = sys.argv[1:]

    if len(args) == 0:
        # 无参数 → 交互菜单
        interactive_menu()

    elif len(args) >= 1:
        # 有参数 → 批量模式
        folder_arg = args[0]
        q = 85  # 默认质量

        if len(args) >= 2:
            try:
                q = int(args[1])
                if not 1 <= q <= 100:
                    print(f"❌ 质量参数必须在 1-100 之间，使用默认值 85")
                    q = 85
            except ValueError:
                print(f"❌ 无效的质量参数 '{args[1]}'，使用默认值 85")

        try:
            compress_images(folder_arg, quality=q)
        except Exception as e:
            print(f"\n❌ 压缩失败: {e}")
            sys.exit(1)
