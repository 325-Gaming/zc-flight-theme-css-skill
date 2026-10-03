# 数据录入客户端 WebView 变量

客户端基础样式负责窗口、控件的尺寸和布局。主题只在原有 `body[data-page-style="<name>"]` 规则中填写以下不透明 `#RRGGBB` 色值；顺序以当前 `classic.css` 为准。每款主题都应与直播页配色相称，且完整提供这些变量。

| 变量 | 用途 |
| --- | --- |
| `--client-window-background` | 窗口背景 |
| `--client-panel-background` | 面板、菜单和弹窗背景 |
| `--client-text`、`--client-muted-text` | 正文和次要文字 |
| `--client-border` | 控件、面板和表格边框 |
| `--client-control-background`、`--client-control-hover-background`、`--client-control-pressed-background`、`--client-control-text` | 普通按钮与菜单项的正常、悬停和按下状态 |
| `--client-control-disabled-background`、`--client-control-disabled-text` | 禁用状态 |
| `--client-input-background`、`--client-input-text`、`--client-placeholder-text` | 输入框、选择框和只读框 |
| `--client-focus` | 键盘焦点外框 |
| `--client-selection-background`、`--client-selection-text` | 乘客和记录选中状态 |
| `--client-accent-background`、`--client-accent-hover-background`、`--client-accent-pressed-background`、`--client-accent-text` | 主要操作按钮各状态 |
| `--client-table-heading-background`、`--client-table-heading-text`、`--client-table-row-hover-background` | 表头与记录悬停 |
| `--client-danger-background`、`--client-danger-hover-background`、`--client-danger-pressed-background`、`--client-danger-text` | 错误和危险操作各状态 |
| `--client-success-text`、`--client-warning-text` | 成功和提醒状态文字 |
| `--client-scrollbar-track`、`--client-scrollbar-thumb` | 滚动条 |

客户端基础样式将这些变量映射到所有 WebView 内控件；系统标题栏和系统文件选择器由操作系统绘制。主题中的客户端变量不能包含透明色、渐变、图片或 `var()`，以便静态校验最不利状态的对比度。普通及次要文字、按钮各种状态、输入内容与占位文字、选中项、主要操作、表头和错误提示的成对颜色至少达到 4.5:1。成功与提醒文字以面板背景检查。焦点颜色还须在相邻面板和输入框背景上明显可辨。

修改已存在的主题时，根据当前任务的 Git 范围处理文件；未跟踪主题不因存在于目录中就自动纳入批量迁移。验证时先运行主题校验器，再在客户端检查长乘客名、所有控件状态、字体缺失及缩放，不能把静态校验当作渲染验证。
