"""推荐解释生成器

将候选组合压缩为提示词，调用模型生成可读推荐理由
"""

import json
import os
from typing import Dict, Mapping, Sequence
from .service.utils import OUTPUT_CANDIDATES

MODEL = "deepseek-v4-flash"
BASE_URL = "https://api.deepseek.com"
TEMPERATURE = 0.8
THINKING_TYPE = "disabled"
API_KEY_ENV_VAR = "DEEPSEEK_API_KEY"
CLIENT = None
AGENT_TIMEOUT_SECONDS = 15.0


def safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def combo_to_text(index: int, item: Mapping[str, object]) -> str:
    """将候选组合转为紧凑文本，供提示词拼接。"""
    parts = item.get("parts", {})
    scores = item.get("scores", {})
    return (
        f"{index}. "
        f"总价={safe_float(item.get('total_price')):.2f}元, "
        f"总分={safe_float(scores.get('total_score_100')):.1f}/100, "
        f"性价比={safe_float(item.get('combo_value_100')):.1f}/100, "
        f"CPU={getattr(parts.get('cpu'), 'name', '')}, "
        f"GPU={getattr(parts.get('gpu'), 'name', '')}, "
        f"内存={getattr(parts.get('ram'), 'name', '')}, "
        f"存储={getattr(parts.get('storage'), 'name', '')}"
    )


def build_agent_prompt(
    form_data: Mapping[str, object],
    recommendations: Sequence[Mapping[str, object]],
) -> str:
    """构建 JSON 输出的提示词模板。"""
    user_text = form_data["free_text"]
    prefs = {
        "user_text": user_text or "",
        "budget_min": form_data.get("budget_min", ""),
        "budget_max": form_data.get("budget_max", ""),
        "workload": form_data.get("workload", ""),
        "cpu_brand": form_data.get("cpu_brand", ""),
        "gpu_chip_brand": form_data.get("gpu_chip_brand", ""),
        "top_k": form_data.get("top_k", 3),
    }
    combos = [
        combo_to_text(i + 1, item) for i, item in enumerate(recommendations)
    ]

    prompt_template = (
        "你是专业 DIY 装机推荐助手，请根据用户需求和候选配置进行分析与推荐。\n\n"
        "任务要求：\n"
        "1. 必须从候选组合中选择恰好 {top_k} 套推荐方案。\n"
        "2. choices 数组长度必须等于 {top_k}。\n"
        "3. rank 从 1 开始连续编号，数字越小表示越推荐。\n"
        "4. combo_index 必须来自候选组合编号。\n"
        "5. 每个 choice 都必须包含非空 reason，不允许遗漏。\n"
        "6. 推荐时优先考虑用户需求、预算匹配度、整机均衡性和配件搭配合理性。\n"
        "7. 尽量选择具有差异化特点的方案，不要推荐几乎相同的组合。\n"
        "8. 不要编造候选组合中不存在的配件、参数或价格信息。\n"
        "9. 不要提及性能分数、性价比分数、排名计算过程等系统内部信息。\n"
        "10. 仅输出 JSON，不要输出 Markdown、解释文字或额外内容。\n\n"
        "reason 编写要求：\n"
        "- 每条控制在 1~2 句话。\n"
        "- 结合用户需求说明为什么推荐该方案。\n"
        "- 突出 CPU、GPU、内存、存储等关键配件的搭配特点。\n"
        "- 不要写空泛评价，例如“性能不错”“值得购买”。\n"
        "- 不要重复 summary 内容。\n\n"
        "summary 编写要求：\n"
        "- 控制在 3 句话左右。\n"
        "- 先分析用户真实需求和预算范围。\n"
        "- 再分析排名第 1 的推荐方案为何最匹配。\n"
        "- 最后给出明确购买建议。\n"
        "- 如果用户提到了具体游戏、软件、AI训练、渲染、建模、直播、分辨率、剪辑等场景，必须明确回应这些需求。\n"
        "- 不要讨论未入选方案。\n\n"
        "输出前检查：\n"
        "- choices 数量是否等于 {top_k}\n"
        "- 每个 choice 是否都包含 rank、combo_index、reason\n"
        "- reason 是否为空\n"
        "- rank 是否从 1 连续递增\n"
        "- combo_index 是否来自候选列表\n"
        "- JSON 是否合法\n\n"
        "JSON 格式：\n"
        "{{\n"
        '  "choices": [\n'
        '    {{"rank": 1, "combo_index": 2, "reason": "推荐理由"}},\n'
        '    {{"rank": 2, "combo_index": 5, "reason": "推荐理由"}}\n'
        "  ],\n"
        '  "summary": "总体分析与购买建议"\n'
        "}}\n\n"
        "用户偏好：\n"
        "{prefs_json}\n\n"
        "候选组合（共 {max_combos} 条）：\n"
        "{combos_text}"
    )

    return prompt_template.format(
        top_k=prefs["top_k"],
        prefs_json=json.dumps(prefs, ensure_ascii=False),
        combos_text="\n".join(combos),
        max_combos=OUTPUT_CANDIDATES,
    )


def parse_agent_json(text: str) -> Dict[str, object]:
    """尽量稳健地从模型输出中解析 JSON。"""
    text = (text or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
        return {}


def load_openai_class():
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return OpenAI


def get_agent_client():
    """
    获取模块级复用 client。
    首次调用时懒加载，后续请求复用，减少重复初始化开销。
    """
    global CLIENT
    if CLIENT is not None:
        return CLIENT

    api_key = os.getenv(API_KEY_ENV_VAR, "").strip()
    if not api_key:
        return None

    openai_cls = load_openai_class()
    if openai_cls is None:
        return None

    CLIENT = openai_cls(
        api_key=api_key,
        base_url=BASE_URL,
        timeout=AGENT_TIMEOUT_SECONDS,
    )
    return CLIENT


def warmup_agent_client() -> bool:
    """
    预热智能体 client：在页面进入阶段提前完成初始化。
    """
    try:
        return get_agent_client() is not None
    except Exception:
        return False


def run_agent_recommendation(
    form_data: Mapping[str, object],
    recommendations: Sequence[Mapping[str, object]],
) -> Dict[str, object]:
    api_key = os.getenv(API_KEY_ENV_VAR, "").strip()

    # 检查 API Key
    if not api_key:
        return {
            "enabled": False,
            "reason": f"未配置 {API_KEY_ENV_VAR}，已使用规则推荐。",
        }

    # 检查是否有候选组合
    if not recommendations:
        return {
            "enabled": False,
            "reason": "暂无候选组合，无法进行智能体分析。",
        }

    # 调用智能体
    client = get_agent_client()
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "你将作为装机推荐顾问，为用户输出安全、准确、结构化的建议。",
                },
                {
                    "role": "user",
                    # 拼接用户需求和候选组合，构建提示词
                    "content": build_agent_prompt(
                        form_data,
                        recommendations,
                    ),
                },
            ],
            temperature=TEMPERATURE,
            extra_body={"thinking": {"type": THINKING_TYPE}},
            timeout=AGENT_TIMEOUT_SECONDS,
        )

        output_text = completion.choices[0].message.content or ""

    except Exception as exc:
        return {
            "enabled": False,
            "reason": f"智能体调用失败：{exc}",
        }

    # 解析智能体输出
    parsed = parse_agent_json(output_text)
    if not parsed:
        return {
            "enabled": False,
            "reason": "智能体返回无法解析。",
        }

    top_k = min(
        int(form_data.get("top_k", 3)),
        len(recommendations),
    )
    choices = sorted(
        parsed.get("choices", []),
        key=lambda x: x["rank"],
    )[:top_k]

    return {
        "enabled": True,
        "summary": str(parsed.get("summary", "")).strip(),
        "choices": choices,
        "model": MODEL,
    }
