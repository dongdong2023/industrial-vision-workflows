import math
from ivw.common import number


def compute(data, sample_ids):
    if not isinstance(data, dict) or "traces" in data and not isinstance(data["traces"], list):
        raise ValueError("性能数据必须为对象，traces 必须为列表")
    traces = data.get("traces")
    if not isinstance(traces, list) or not traces:
        return {"p95_latency_ms": None, "failure_rate": None}
    seen, values, failures = set(), [], 0
    for trace in traces:
        if not isinstance(trace, dict):
            raise ValueError("性能 trace 必须为对象")
        sid = trace.get("sample_id")
        if sid not in sample_ids or sid in seen or type(trace.get("ok")) is not bool:
            raise ValueError("性能 trace ID 重复、未知或缺少 ok")
        seen.add(sid)
        values.append(number(trace.get("latency_ms"), "latency_ms", 0))
        failures += not trace["ok"]
    if seen != set(sample_ids):
        raise ValueError("性能 trace 未覆盖声明的数据集")
    values.sort()
    return {"p95_latency_ms": values[math.ceil(0.95 * len(values)) - 1], "failure_rate": failures / len(values)}
