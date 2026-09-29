# 扩展主题规则

仅在需要新增其他字体或现有主题变量无法表达目标视觉效果时读取本文件。默认黑体、宋体、楷体和项目通用 Fusion Pixel 不需要加载这些细节。

## 独立确认边界

### 修改共享基础样式

修改 `zc-flight-live.css`、新增共享选择器、伪元素、关键帧、媒体查询或效果变量之前，先向用户说明：

- 准备修改的文件和共享能力；
- 新增的选择器、变量、动画和媒体查询；
- 对 classic 与其他主题的潜在影响；
- 如何保证默认关闭、布局不变和交互不受影响；
- 兼容性、可访问性、性能和回归检查计划。

收到用户明确确认后才能修改。确认仅覆盖已经说明的内容；扩大范围时再次确认。仅配置基础样式中已经存在的效果槽不需要重复确认。

### 项目通用 Fusion Pixel

Fusion Pixel 12px 比例版是已经批准的项目通用字体。基础样式统一注册以下本地资源，并提供简体中文与日文两套完整字体栈：

- `assets/fonts/fusion-pixel-font/fusion-pixel-12px-proportional-zh_hans.otf.woff2`
- `assets/fonts/fusion-pixel-font/fusion-pixel-12px-proportional-ja.otf.woff2`
- `assets/fonts/fusion-pixel-font/fusion-pixel-12px-proportional-latin.otf.woff2`
- `assets/licenses/fusion-pixel-font/OFL.txt` 及同目录中的上游许可证

简体中文或通用主题设置 `--page-font-family: var(--fusion-pixel-font-family)`；日文内容或需要日文字形风格的主题设置 `--page-font-family: var(--fusion-pixel-ja-font-family)`。两者均无需再次确认。不得在主题文件中重复添加 Fusion Pixel 的 `@font-face`，也不得改为远程地址。创建或更新使用它们的主题时，检查上述资源、共享注册、完整 classic fallback、加载失败回退和文字溢出，并使用 `--base` 执行校验。

### 新增其他字体

在主题中首次引入默认黑体、宋体、楷体和项目通用 Fusion Pixel 以外的字体前，无论使用本地资源还是远程资源，都要先向用户说明字体名称、来源、许可、fallback、可能的布局变化和检查计划，并取得明确确认。

本地字体优先使用 `woff2`，放入项目既有字体资源目录并随适用的版权和许可证文件一起交付。不得因为文件已经存在于项目中就自动把它加入允许清单。

### 远程字体

写入任何新的远程字体 URL 前，除上述新增字体确认信息外，还要单独说明字体地址、格式、网络和 CORS 风险，并取得用户明确确认。对共享视觉扩展的确认不包含新增字体确认，反之亦然。

优先使用项目内已有或用户提供的本地 `woff2`。远程资源只允许直接 HTTPS 字体文件，不使用远程 `@import`。`@font-face` 必须设置 `font-display: swap`，主题字体栈必须完整保留 classic 默认字体栈。

## 通用视觉效果槽

新增能力应作为通用、默认关闭的基础组件，而不是把某个主题的颜色写死在共享样式中。静态纹理优先使用 `body[data-page-style]::before`，移动扫光优先使用 `body[data-page-style]::after`；复用已有槽位，不随意增加更多全屏伪元素。

效果槽必须满足：

- 使用 `content: var(--name, none)` 或等效关闭 fallback；
- 脱离文档流，不占据或推动原组件空间；
- 设置 `pointer-events: none`；
- 默认背景和动画均为 `none`；
- 层级受控，不遮挡必须保持清晰的内容；
- 动画名称具有明确作用域，不复用无关关键帧；
- 动画提供 `prefers-reduced-motion: reduce` 降级；
- 不修改现有组件的尺寸、位置、滚动、点击或内容结构。

当前允许的可选扩展变量为：

- `--scanline-overlay-content`
- `--scanline-overlay-background`
- `--scanline-overlay-z-index`
- `--scan-sweep-content`
- `--scan-sweep-height`
- `--scan-sweep-z-index`
- `--scan-sweep-background`
- `--scan-sweep-animation`

增加新的可选扩展变量时，同时更新本清单和校验器；不要加入 `classic.css` 的核心必填变量，除非它确实应由每个主题明确配置。

## 检查清单

- classic 和未启用效果的主题保持原样。
- 装饰层不会接收点击，也不会产生滚动条。
- 动画关闭和减少动态效果模式均正常。
- 扫描线、噪点或扫光经过文字时仍然可读。
- 目标 OBS/浏览器支持使用的颜色语法、字体格式和自定义属性。
- 检查动画的持续性能，不使用高频闪烁。
- 自定义字体分别测试加载前、加载后、加载失败、长中文、拉丁字符、数字和标点。
