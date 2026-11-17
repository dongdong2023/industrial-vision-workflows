# 双引擎接口与基础评测契约

## 数据与证据

`experiment dataset --file <manifest.json> --store <目录>` 校验并按内容 SHA-256 登记数据集。协议为 `schema_version: 1`，任务为 `detection`、`video-action` 或 `pointcloud`，`evidence_level` 必须为 `synthetic`、`offline`、`field` 之一；不同证据等级不混为现场结论。

每个样本含唯一 `id`、采集 `group`、`split`（train/validation/test）、`observations` 列表与独立 `ground_truth` 列表，可含 `slice`、原始采集 `content_sha256`。同组或已声明的重复内容不能跨 split。`annotation_status` 缺省表示该 manifest 提供已确认标签；显式值只能为 `verified`。未知工艺完成状态不得填成空真值。标签准确性、来源授权、未声明重复和现场代表性仍需人工核查。

检测对象用归一化 `[x1,y1,x2,y2]` 的 `box`，点云对象用米制 `[x,y,z]` 的 `center`（数据集必须 `coordinate_unit: m`），事件用非负秒制 `start/end`。每个对象必须有非空 `label`。合成示例见 `examples/datasets/`；客户原始采集和权重只保留本地引用。

## Experiment Engine

入口：`python ivw.py experiment <dataset|register-runner|run|compare|failure> --help`。

`run --config <json> --store <目录>` 要求固定 `name`、`dataset`、`runner`、`model.id/version`、`code_version`、整数 `seed`、`parameters` 和可选 `timeout_seconds`。数据集和 `model.weights` 相对配置文件解析。内置 runner 仅用于合成演示；自定义 runner 用唯一名称和本地 `.py` 文件登记，SHA-256 变化后必须重新登记新名称。

runner 命令为 `python <runner.py> --input <input.json> --config <runner-config.json> --output <run目录>`。工作目录是唯一 run 目录；`input.json` 直接提供训练 split 标签，validation/test 标签不进入此输入。程序受信任且能访问本机，标签裁剪和目录隔离不是安全隔离。外部 Python 依赖及硬件环境由调用者固定，本工具不自动构建隔离环境。

`config.json` 保留原始配置以计算 `config_hash`；`runner-config.json` 将模型权重引用解析为绝对路径。可用的本地原始数据引用放在 `observations` 内，由 runner 按项目适配。运行前后检查 runner、权重、固定输入和配置是否改变。

输出 `predictions.json`：

```json
{"dataset_id":"数据集内容摘要","samples":[{"id":"sample-1","predictions":[]}]}
```

每个已处理样本都要输出记录，包括无目标样本的空列表。`performance.json` 可含 `traces`，每项为 `sample_id`、非负 `latency_ms`、布尔 `ok`，非空 trace 必须覆盖数据集且不得重复。缺失 trace 的性能指标为 null，不记成零耗时或零失败。

训练程序可输出 `models.json`：`{"models":[{"id":"model-name","version":"1","path":"model.json"}]}`。产物必须位于 run 目录，登记模型摘要及数据/配置/run 关联。进程失败、超时、非法输出都留存 `stdout.log`、`stderr.log` 与失败记录。记录包含实际命令、Python 版本、runner/模型/配置摘要和产物摘要，只以新 run ID 追加。

## Evaluation Engine

`evaluate --run <run.json> --dataset <原始manifest> --protocol <json> --store <目录>` 只接受完成且摘要一致的实验。独立读取指定真值，校验 dataset_id，再与固定预测计算指标；忽略 runner 的 metrics/score 文件。

一对一匹配优先最大匹配数量，再最小化代价。检测按类别和 IoU，事件按类别和时间 IoU，点云按类别和米制中心距离。报告 TP/FP/FN、precision/recall、类别与切片指标、空场误报率、事件证据绑定、匹配中心误差和 trace P95/失败率。未匹配几何目标同时产生 FP/FN，不会只靠少数匹配目标的小误差通过。

事件绑定检查 `evidence.sample_id` 等于当前样本、非空字符串 `object_id`、`time` 在事件区间内；不证明物理动作完成或对象身份真实。点云不覆盖配组拓扑/尺寸；检测不是 mAP。性能是经摘要固定的 runner trace，不是独立硬件采样或长稳验收。

协议见 `examples/evaluation-protocol.json`：固定 `split`、匹配阈值、按任务 `required_metrics` 和非空 `thresholds`（`<metric>_min/max`）。必须约束 precision 与 recall。`minimum_samples` 和 `minimum_negative_samples` 为正整数，缺省各为 1；示例样本下限仅用于合成演示。缺失预测强制 FAIL，即使遗漏的是空场。样本不足、无负例或必需指标为 null 都不能通过。

结果为不可覆写的 `evaluations/eval-*/report.json` 与 Markdown，含验收逐项结果、覆盖、未评估项、失败样本、证据等级和命令/模型/代码来源。`evaluate --baseline <report> --candidate <report>` 仅允许同数据、任务、split、协议比较；返回指标差值，不自动选择或批准模型。

闭环是“固定数据 → 运行基线/候选 → 独立评测 → 比较 → failure 留档 → 下次新版本实验”。Smoke 的合成标定展示训练改进，SOP 展示证据绑定回归被拒绝。报告永远保留 `production_authorized: false`、`loading_authorized: false`。失败案例可用 `experiment failure --file <json> --store <目录>` 追加，至少包含 sample_id、stage、expected、observed、hypothesis、evidence_level。
