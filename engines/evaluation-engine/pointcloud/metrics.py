import math
from ivw.common import number


def validate(item):
    center = item.get("center")
    if not isinstance(center, list) or len(center) != 3:
        raise ValueError("center 必须是三维米制坐标")
    for value in center:
        number(value, "center")


def distance(a, b):
    return math.dist(a["center"], b["center"])


def cost(prediction, truth, threshold):
    error = distance(prediction, truth)
    return error / threshold if prediction["label"] == truth["label"] and error <= threshold else None
