"""Maximum-cardinality, minimum-cost bipartite matching via rectangular Hungarian assignment."""


def match(predictions, truths, cost):
    if not predictions or not truths:
        return []
    n, t = len(predictions), len(truths)
    penalty = (n + t + 1) * 100.0
    edges = [[cost(prediction, truth) for truth in truths] for prediction in predictions]
    matrix = [[penalty * 2 if value is None else value for value in row] + [penalty] * n for row in edges]
    m = t + n
    u, v, p, way = [0.0] * (n + 1), [0.0] * (m + 1), [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minimum, used = [float("inf")] * (m + 1), [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], float("inf"), 0
            for j in range(1, m + 1):
                if not used[j]:
                    current = matrix[i0 - 1][j - 1] - u[i0] - v[j]
                    if current < minimum[j]:
                        minimum[j], way[j] = current, j0
                    if minimum[j] < delta:
                        delta, j1 = minimum[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0], j0 = p[j1], j1
            if j0 == 0:
                break
    return [(p[j] - 1, j - 1) for j in range(1, t + 1) if p[j] and edges[p[j] - 1][j - 1] is not None]
