#!/usr/bin/env python3
"""根据 classic 核心变量和受控扩展约定校验 ZC 航班直播主题。"""

from __future__ import annotations

import argparse
import re
import sys

from pathlib import Path
from urllib.parse import urlparse


COMMENT_PATTERN = re.compile(r"/\*.*?\*/", re.DOTALL)
THEME_RULE_PATTERN = re.compile(
    r'body\[data-page-style="(?P<style>[a-z0-9][a-z0-9-]*)"\]\s*'
    r"\{(?P<body>[^{}]*)\}\s*",
    re.DOTALL,
)
FONT_FACE_PATTERN = re.compile(
    r"@font-face\s*\{(?P<body>[^{}]*)\}\s*",
    re.DOTALL | re.IGNORECASE,
)
CUSTOM_DECLARATION_PATTERN = re.compile(
    r"(?P<name>--[a-z0-9-]+)\s*:\s*(?P<value>[^;{}]+?)\s*;",
    re.DOTALL,
)
FONT_DECLARATION_PATTERN = re.compile(
    r"(?P<name>[a-z-]+)\s*:\s*(?P<value>[^;{}]+?)\s*;",
    re.DOTALL | re.IGNORECASE,
)
URL_PATTERN = re.compile(
    r"url\(\s*(?:\"(?P<double>[^\"]+)\"|'(?P<single>[^']+)'|"
    r"(?P<bare>[^)\s]+))\s*\)",
    re.IGNORECASE,
)
FONT_PREFIXES = (
    '"SimSun", "Songti SC", "STSong"',
    '"KaiTi", "Kaiti SC", "STKaiti"',
)
FUSION_PIXEL_FONT_FILES = {
    "fusion-pixel-12px-proportional-zh_hans": (
        "../../assets/fonts/fusion-pixel-font/"
        "fusion-pixel-12px-proportional-zh_hans.otf.woff2"
    ),
    "fusion-pixel-12px-proportional-ja": (
        "../../assets/fonts/fusion-pixel-font/"
        "fusion-pixel-12px-proportional-ja.otf.woff2"
    ),
    "fusion-pixel-12px-proportional-latin": (
        "../../assets/fonts/fusion-pixel-font/"
        "fusion-pixel-12px-proportional-latin.otf.woff2"
    ),
}
FUSION_PIXEL_FONT_STACKS = {
    "--fusion-pixel-font-family": (
        "fusion-pixel-12px-proportional-zh_hans",
        "fusion-pixel-12px-proportional-latin",
    ),
    "--fusion-pixel-ja-font-family": (
        "fusion-pixel-12px-proportional-ja",
        "fusion-pixel-12px-proportional-latin",
    ),
}
FUSION_PIXEL_FONT_VALUES = {
    f"var({property_name})" for property_name in FUSION_PIXEL_FONT_STACKS
}
FUSION_PIXEL_LICENSE_FILES = (
    "../../assets/licenses/fusion-pixel-font/OFL.txt",
    "../../assets/licenses/fusion-pixel-font/LICENSES/ark-pixel/OFL.txt",
    "../../assets/licenses/fusion-pixel-font/LICENSES/cubic-11/OFL.txt",
    "../../assets/licenses/fusion-pixel-font/LICENSES/galmuri/LICENSE.txt",
)
FONT_FACE_ALLOWED_PROPERTIES = {
    "font-display",
    "font-family",
    "font-style",
    "font-weight",
    "src",
    "unicode-range",
}
OPTIONAL_EXTENSION_PROPERTIES = {
    "--scanline-overlay-background",
    "--scanline-overlay-content",
    "--scanline-overlay-z-index",
    "--scan-sweep-animation",
    "--scan-sweep-background",
    "--scan-sweep-content",
    "--scan-sweep-height",
    "--scan-sweep-z-index",
}
CONTENT_PROPERTIES = {
    "--scanline-overlay-content",
    "--scan-sweep-content",
}
BACKGROUND_PROPERTIES = {
    "--scanline-overlay-background",
    "--scan-sweep-background",
}
Z_INDEX_PROPERTIES = {
    "--scanline-overlay-z-index",
    "--scan-sweep-z-index",
}


def normalize_value(value: str) -> str:
    return " ".join(value.split())


def parse_declarations(
    body: str,
    pattern: re.Pattern[str],
) -> list[tuple[str, str]]:
    declarations = [
        (match.group("name").lower(), normalize_value(match.group("value")))
        for match in pattern.finditer(body)
    ]
    residue = pattern.sub("", body).strip()
    if residue:
        raise ValueError(f"存在无效声明：{residue!r}")

    names = [name for name, _ in declarations]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"存在重复声明：{', '.join(duplicates)}")
    return declarations


def parse_theme(
    path: Path,
) -> tuple[str, list[tuple[str, str]], list[dict[str, str]]]:
    css = COMMENT_PATTERN.sub("", path.read_text(encoding="utf-8")).strip()
    font_faces: list[dict[str, str]] = []
    cursor = 0

    while match := FONT_FACE_PATTERN.match(css, cursor):
        declarations = parse_declarations(
            match.group("body"),
            FONT_DECLARATION_PATTERN,
        )
        font_faces.append(dict(declarations))
        cursor = match.end()

    rule = THEME_RULE_PATTERN.fullmatch(css[cursor:].strip())
    if rule is None:
        raise ValueError(
            "文件必须由可选的 @font-face 和一条 "
            'body[data-page-style="<name>"] 规则组成'
        )

    declarations = parse_declarations(
        rule.group("body"),
        CUSTOM_DECLARATION_PATTERN,
    )
    if not declarations:
        raise ValueError("主题规则中没有自定义属性")

    return rule.group("style"), declarations, font_faces


def border_geometry(value: str) -> tuple[str, str]:
    parts = value.split(maxsplit=2)
    if len(parts) < 2:
        raise ValueError(f"无法从 {value!r} 中读取边框宽度和线型")
    return parts[0], parts[1]


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def font_stack_items(value: str) -> list[str]:
    return [unquote(item) for item in value.split(",") if item.strip()]


def extract_urls(value: str) -> list[str]:
    urls: list[str] = []
    for match in URL_PATTERN.finditer(value):
        urls.append(
            match.group("double")
            or match.group("single")
            or match.group("bare")
        )
    return urls


def validate_font_faces(
    font_faces: list[dict[str, str]],
    allow_custom_fonts: bool,
    allow_remote_fonts: bool,
) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    declared_families: set[str] = set()

    if font_faces and not allow_custom_fonts:
        errors.append("包含 @font-face 时必须显式启用自定义字体校验")

    for index, face in enumerate(font_faces, start=1):
        label = f"第 {index} 个 @font-face"
        extra = sorted(set(face) - FONT_FACE_ALLOWED_PROPERTIES)
        if extra:
            errors.append(f"{label} 包含不允许的描述符：{', '.join(extra)}")

        family = face.get("font-family")
        source = face.get("src")
        if family is None:
            errors.append(f"{label} 缺少 font-family")
        else:
            declared_families.add(unquote(family))
        if source is None:
            errors.append(f"{label} 缺少 src")
            continue
        if face.get("font-display", "").lower() != "swap":
            errors.append(f"{label} 必须设置 font-display: swap")
        if not re.search(r"format\(\s*['\"]woff2['\"]\s*\)", source, re.I):
            errors.append(f"{label} 必须明确声明 woff2 格式")

        urls = extract_urls(source)
        if not urls:
            errors.append(f"{label} 的 src 中没有可识别的 url()")
        for font_url in urls:
            parsed = urlparse(font_url)
            if parsed.scheme == "https":
                if not allow_remote_fonts:
                    errors.append(
                        f"{label} 使用远程字体，必须在用户单独确认后启用"
                        "远程字体校验"
                    )
            elif parsed.scheme:
                errors.append(f"{label} 只允许相对路径或 HTTPS 字体 URL")
            if not parsed.path.lower().endswith(".woff2"):
                errors.append(f"{label} 只允许直接引用 .woff2 字体文件")

        if any("!important" in value for value in face.values()):
            errors.append(f"{label} 不允许使用 !important")

    if allow_remote_fonts and not allow_custom_fonts:
        errors.append("--allow-remote-fonts 必须与 --allow-custom-fonts 同时使用")
    return errors, declared_families


def validate_font_stack(
    theme_font: str | None,
    reference_font: str | None,
    declared_families: set[str],
    allow_custom_fonts: bool,
) -> list[str]:
    errors: list[str] = []
    if reference_font is None or theme_font is None:
        return errors

    allowed_fonts = {reference_font}
    allowed_fonts.update(
        f"{prefix}, {reference_font}" for prefix in FONT_PREFIXES
    )
    allowed_fonts.update(FUSION_PIXEL_FONT_VALUES)
    if theme_font in allowed_fonts:
        if declared_families:
            errors.append("存在未被 --page-font-family 使用的 @font-face")
        return errors

    if not allow_custom_fonts:
        errors.append(
            "--page-font-family 只能使用 classic 默认字体栈，或在其前面添加"
            "规定的宋体、楷体字体栈"
        )
        return errors
    if not declared_families:
        errors.append("自定义字体栈必须由同文件中的 @font-face 注册")
        return errors

    suffix = f", {reference_font}"
    if not theme_font.endswith(suffix):
        errors.append("自定义字体栈末尾必须完整保留 classic 默认字体栈")
        return errors

    custom_prefix = theme_font[: -len(suffix)]
    used_custom_families = set(font_stack_items(custom_prefix))
    undeclared = sorted(used_custom_families - declared_families)
    unused = sorted(declared_families - used_custom_families)
    if undeclared:
        errors.append(f"字体栈包含未注册的自定义字体：{', '.join(undeclared)}")
    if unused:
        errors.append(f"存在未被字体栈使用的 @font-face：{', '.join(unused)}")
    return errors


def validate_extension_values(theme: dict[str, str]) -> list[str]:
    errors: list[str] = []

    for name in CONTENT_PROPERTIES:
        if name in theme and theme[name] not in {"none", '""', "''"}:
            errors.append(f"{name} 只能是 none 或空字符串")

    for name in BACKGROUND_PROPERTIES:
        if name in theme and "url(" in theme[name].lower():
            errors.append(f"{name} 不允许加载外部图片")

    height = theme.get("--scan-sweep-height")
    if height is not None:
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)(px|vh)", height)
        if match is None:
            errors.append("--scan-sweep-height 只能使用正数 px 或 vh")
        else:
            amount = float(match.group(1))
            limit = 1000 if match.group(2) == "px" else 100
            if amount <= 0 or amount > limit:
                errors.append("--scan-sweep-height 超出安全范围")

    for name in Z_INDEX_PROPERTIES:
        if name not in theme:
            continue
        try:
            z_index = int(theme[name])
        except ValueError:
            errors.append(f"{name} 必须是整数")
            continue
        if not 0 <= z_index <= 2000:
            errors.append(f"{name} 必须位于 0 到 2000 之间")

    animation = theme.get("--scan-sweep-animation")
    if animation is not None and animation != "none":
        match = re.fullmatch(
            r"scan-sweep-down\s+([0-9]+(?:\.[0-9]+)?)s\s+"
            r"(?:linear|ease|ease-in-out)\s+infinite",
            animation,
        )
        if match is None:
            errors.append(
                "--scan-sweep-animation 只能使用受控的 scan-sweep-down 循环动画"
            )
        elif float(match.group(1)) < 1:
            errors.append("--scan-sweep-animation 周期不得短于 1 秒")

    if theme.get("--scanline-overlay-content") in {'""', "''"}:
        if "--scanline-overlay-background" not in theme:
            errors.append("启用固定扫描线时必须声明其背景")
    if theme.get("--scan-sweep-content") in {'""', "''"}:
        for required in (
            "--scan-sweep-background",
            "--scan-sweep-animation",
            "--scan-sweep-height",
        ):
            if required not in theme:
                errors.append(f"启用移动扫描线时必须声明 {required}")

    return errors


def selector_block(css: str, selector: str) -> str | None:
    pattern = re.compile(
        rf"{re.escape(selector)}\s*\{{(?P<body>[^{{}}]*)\}}",
        re.DOTALL,
    )
    match = pattern.search(css)
    return None if match is None else match.group("body")


def validate_base(base_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        css = COMMENT_PATTERN.sub("", base_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        return [f"{base_path}：无法读取基础样式：{error}"]

    for name in sorted(OPTIONAL_EXTENSION_PROPERTIES):
        if re.search(rf"var\(\s*{re.escape(name)}\s*,", css) is None:
            errors.append(f"基础样式未以关闭 fallback 使用扩展变量 {name}")

    for selector in (
        "body[data-page-style]::before",
        "body[data-page-style]::after",
    ):
        block = selector_block(css, selector)
        if block is None:
            errors.append(f"基础样式缺少受控效果槽 {selector}")
            continue
        if re.search(r"pointer-events\s*:\s*none\s*;", block) is None:
            errors.append(f"{selector} 必须设置 pointer-events: none")
        if re.search(r"position\s*:\s*fixed\s*;", block) is None:
            errors.append(f"{selector} 必须使用 fixed 脱离文档流")

    if re.search(r"@keyframes\s+scan-sweep-down\b", css) is None:
        errors.append("基础样式缺少 scan-sweep-down 关键帧")
    reduced_motion = re.search(
        r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{.*?"
        r"body\[data-page-style\]::after\s*\{.*?content\s*:\s*none\s*;",
        css,
        re.DOTALL,
    )
    if reduced_motion is None:
        errors.append("基础样式必须在减少动态效果模式下关闭移动扫描层")

    return errors


def validate_fusion_pixel_base(
    base_path: Path,
    reference_font: str | None,
) -> list[str]:
    errors: list[str] = []
    try:
        css = COMMENT_PATTERN.sub("", base_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        return [f"{base_path}：无法读取基础样式：{error}"]

    for property_name, families in FUSION_PIXEL_FONT_STACKS.items():
        stack_matches = re.findall(
            rf"{re.escape(property_name)}\s*:\s*"
            r"(?P<value>[^;{}]+?)\s*;",
            css,
            re.DOTALL,
        )
        if len(stack_matches) != 1:
            errors.append(f"基础样式必须且只能声明一次 {property_name}")
        elif reference_font is not None:
            family_prefix = ", ".join(
                f'"{family}"' for family in families
            )
            expected_stack = f"{family_prefix}, {reference_font}"
            if normalize_value(stack_matches[0]) != expected_stack:
                errors.append(
                    f"{property_name} 必须按规定字体顺序完整保留 "
                    "classic 默认字体栈"
                )

    registered_faces: dict[str, dict[str, str]] = {}
    for match in FONT_FACE_PATTERN.finditer(css):
        try:
            face = dict(
                parse_declarations(
                    match.group("body"),
                    FONT_DECLARATION_PATTERN,
                )
            )
        except ValueError as error:
            errors.append(f"基础样式中的 @font-face 无效：{error}")
            continue
        family = face.get("font-family")
        if family is not None:
            registered_faces[unquote(family)] = face

    for family, expected_url in FUSION_PIXEL_FONT_FILES.items():
        face = registered_faces.get(family)
        if face is None:
            errors.append(f"基础样式缺少通用字体注册：{family}")
            continue
        if face.get("font-display", "").lower() != "swap":
            errors.append(f"通用字体 {family} 必须设置 font-display: swap")
        source = face.get("src", "")
        urls = extract_urls(source)
        if urls != [expected_url]:
            errors.append(
                f"通用字体 {family} 必须引用规定的本地 WOFF2 文件"
            )
            continue
        font_path = (base_path.parent / expected_url).resolve()
        if not font_path.is_file():
            errors.append(f"通用字体文件不存在：{font_path}")

    for license_url in FUSION_PIXEL_LICENSE_FILES:
        license_path = (base_path.parent / license_url).resolve()
        if not license_path.is_file():
            errors.append(f"Fusion Pixel 许可证文件不存在：{license_path}")

    return errors


def validate(
    theme_path: Path,
    reference_path: Path,
    *,
    base_path: Path | None = None,
    allow_custom_fonts: bool = False,
    allow_remote_fonts: bool = False,
    allow_extensions: bool = False,
) -> list[str]:
    errors: list[str] = []
    try:
        style_name, declarations, font_faces = parse_theme(theme_path)
    except (OSError, UnicodeError, ValueError) as error:
        return [f"{theme_path}: {error}"]

    try:
        reference_style, reference_declarations, reference_fonts = parse_theme(
            reference_path
        )
    except (OSError, UnicodeError, ValueError) as error:
        return [f"{reference_path}：基准文件无效：{error}"]

    if reference_style != "classic":
        errors.append(f'{reference_path}：基准选择器的样式名必须为 "classic"')
    if reference_fonts:
        errors.append(f"{reference_path}：classic 基准不应包含 @font-face")
    if theme_path.stem != style_name:
        errors.append(f'{theme_path}：文件名必须为 "{style_name}.css"，与选择器一致')

    theme = dict(declarations)
    reference = dict(reference_declarations)
    missing = [name for name in reference if name not in theme]
    extra = [name for name in theme if name not in reference]
    invalid_extra = [
        name
        for name in extra
        if not allow_extensions or name not in OPTIONAL_EXTENSION_PROPERTIES
    ]
    if missing:
        errors.append(f"缺少 classic 核心变量：{', '.join(missing)}")
    if invalid_extra:
        errors.append(f"包含未经允许的扩展变量：{', '.join(invalid_extra)}")

    actual_core_order = [name for name, _ in declarations if name in reference]
    expected_core_order = [name for name, _ in reference_declarations]
    if not missing and actual_core_order != expected_core_order:
        errors.append("核心变量必须按照 classic.css 中的顺序排列")

    font_errors, declared_families = validate_font_faces(
        font_faces,
        allow_custom_fonts,
        allow_remote_fonts,
    )
    errors.extend(font_errors)
    errors.extend(
        validate_font_stack(
            theme.get("--page-font-family"),
            reference.get("--page-font-family"),
            declared_families,
            allow_custom_fonts,
        )
    )

    if theme.get("--page-font-family") in FUSION_PIXEL_FONT_VALUES:
        if base_path is None:
            errors.append(
                "使用通用 Fusion Pixel 字体栈时必须通过 --base 提供基础样式表"
            )
        else:
            errors.extend(
                validate_fusion_pixel_base(
                    base_path,
                    reference.get("--page-font-family"),
                )
            )

    if "--scoreboard-border" in theme and "--scoreboard-border" in reference:
        try:
            theme_border = border_geometry(theme["--scoreboard-border"])
            reference_border = border_geometry(reference["--scoreboard-border"])
            if theme_border != reference_border:
                errors.append(
                    "--scoreboard-border 的宽度和线型必须与 classic 完全一致"
                )
        except ValueError as error:
            errors.append(str(error))

    animation = theme.get("--identity-animation")
    reference_animation = reference.get("--identity-animation")
    if animation not in {reference_animation, "none"}:
        errors.append("--identity-animation 必须使用 classic 的原值或 none")

    if any("!important" in value for value in theme.values()):
        errors.append("主题值中不允许使用 !important")

    extension_names = set(extra) & OPTIONAL_EXTENSION_PROPERTIES
    if extension_names:
        errors.extend(validate_extension_values(theme))
        if base_path is None:
            errors.append("使用扩展变量时必须通过 --base 提供基础样式表")
        else:
            errors.extend(validate_base(base_path))

    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="校验 ZC 航班直播主题的核心变量和受控扩展。"
    )
    parser.add_argument("theme", type=Path, help="新的主题 CSS 文件")
    parser.add_argument(
        "--reference",
        required=True,
        type=Path,
        help="作为核心变量和布局基准的 classic.css",
    )
    parser.add_argument(
        "--base",
        type=Path,
        help="使用通用 Fusion Pixel 或扩展效果时对应的 zc-flight-live.css",
    )
    parser.add_argument(
        "--allow-custom-fonts",
        action="store_true",
        help="允许经过检查的 @font-face 和自定义字体栈",
    )
    parser.add_argument(
        "--allow-remote-fonts",
        action="store_true",
        help="允许已取得用户单独确认的 HTTPS 远程字体",
    )
    parser.add_argument(
        "--allow-extensions",
        action="store_true",
        help="允许受控的可选视觉扩展变量",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    errors = validate(
        args.theme.resolve(),
        args.reference.resolve(),
        base_path=None if args.base is None else args.base.resolve(),
        allow_custom_fonts=args.allow_custom_fonts,
        allow_remote_fonts=args.allow_remote_fonts,
        allow_extensions=args.allow_extensions,
    )
    if errors:
        for error in errors:
            print(f"错误：{error}", file=sys.stderr)
        return 1

    print(f"通过：{args.theme} 符合 classic 核心变量及所选扩展约定")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
