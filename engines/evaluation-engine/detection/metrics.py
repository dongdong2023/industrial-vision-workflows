from ivw.common import number


def validate(item):
    box = item.get("box")
    if not isinstance(box, list) or len(box) != 4:
        raise ValueError("检测框必须是四元素 xyxy")
    for value in box:
        number(value, "box", 0, 1)
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("检测框必须有正面积")


def iou(a, b):
    a, b = a["box"], b["box"]
    overlap = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return overlap / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - overlap)


def cost(prediction, truth, threshold):
    overlap = iou(prediction, truth)
    return 1 - overlap if prediction["label"] == truth["label"] and overlap >= threshold else None
