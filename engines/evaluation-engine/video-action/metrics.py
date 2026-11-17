from ivw.common import number


def validate(item):
    number(item.get("start"), "start", 0)
    number(item.get("end"), "end", 0)
    if item["end"] <= item["start"]:
        raise ValueError("事件结束必须晚于开始")


def iou(a, b):
    overlap = max(0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
    return overlap / (max(a["end"], b["end"]) - min(a["start"], b["start"]))


def cost(prediction, truth, threshold):
    overlap = iou(prediction, truth)
    return 1 - overlap if prediction["label"] == truth["label"] and overlap >= threshold else None


def bound(prediction, sample_id):
    evidence = prediction.get("evidence", {})
    if not isinstance(evidence, dict):
        return False
    value = evidence.get("time")
    try:
        number(value, "evidence.time", 0)
    except ValueError:
        return False
    return (evidence.get("sample_id") == sample_id and isinstance(evidence.get("object_id"), str)
            and bool(evidence["object_id"].strip()) and prediction["start"] <= value <= prediction["end"])
