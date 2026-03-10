# df: 该类配件数据
# budget: 预算
def select_best(df, budget):

    df = df[df["price"] <= budget]

    # 计算性价比
    df = df.copy()  # 避免修改原数据
    df["value"] = df["score"] / df["price"]

    df = df.sort_values("value", ascending=False)

    return df.iloc[0]
