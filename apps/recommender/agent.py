import json
import os
from typing import Dict, Mapping, Sequence

BASE_URL = "https://api.moonshot.cn/v1"
MODEL = "kimi-k2.5"


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _combo_to_text(index: int, item: Mapping[str, object]) -> str:
    parts = item.get("parts", {})
    scores = item.get("scores", {})
    return (
        f"{index}. "
        f"总价={_safe_float(item.get('total_price')):.2f}元, "
        f"总分={_safe_float(scores.get('total_score_100')):.1f}/100, "
        f"性价比={_safe_float(item.get('combo_value_100')):.1f}/100, "
        f"CPU={getattr(parts.get('cpu'), 'name', '')}, "
        f"GPU={getattr(parts.get('gpu'), 'name', '')}, "
        f"内存={getattr(parts.get('ram'), 'name', '')}, "
        f"存储={getattr(parts.get('storage'), 'name', '')}, "
        f"主板={getattr(parts.get('mb'), 'name', '')}, "
        f"电源={getattr(parts.get('psu'), 'name', '')}, "
        f"机箱={getattr(parts.get('case'), 'name', '')}, "
        f"散热={getattr(parts.get('cooler'), 'name', '')}"
    )


def build_agent_prompt(
    user_text: str,
    form_data: Mapping[str, object],
    recommendations: Sequence[Mapping[str, object]],
) -> str:
    prefs = {
        "user_text": user_text or "",
        "budget_min": form_data.get("budget_min", ""),
        "budget_max": form_data.get("budget_max", ""),
        "workload": form_data.get("workload", ""),
        "cpu_brand": form_data.get("cpu_brand", ""),
        "gpu_chip_brand": form_data.get("gpu_chip_brand", ""),
        "top_k": form_data.get("top_k", 3),
    }
    combos = [_combo_to_text(i + 1, item) for i, item in enumerate(recommendations)]

    # 输出固定 JSON，便于页面稳定渲染。
    return (
        "你是 DIY 装机推荐助手。请结合用户偏好与候选组合，输出推荐结果。\n"
        "要求：\n"
        "1) 从候选中推荐最多3套，按优先级排序。\n"
        "2) 每套写简短理由（强调场景匹配、预算、性能和性价比权衡）。\n"
        "3) 给一个总建议（例如最均衡方案/最省钱方案/最强性能方案）。\n"
        "4) 仅输出 JSON，不要输出多余文本。\n"
        "JSON 格式：\n"
        "{\n"
        '  "summary": "总体建议",\n'
        '  "choices": [\n'
        '    {"rank": 1, "combo_index": 2, "reason": "理由"},\n'
        '    {"rank": 2, "combo_index": 1, "reason": "理由"}\n'
        "  ]\n"
        "}\n\n"
        f"用户偏好:\n{json.dumps(prefs, ensure_ascii=False)}\n\n"
        "候选组合:\n" + "\n".join(combos)
    )


def _parse_agent_json(text: str) -> Dict[str, object]:
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


def run_agent_recommendation(
    user_text: str,
    form_data: Mapping[str, object],
    recommendations: Sequence[Mapping[str, object]],
) -> Dict[str, object]:
    api_key = os.getenv("MOONSHOT_API_KEY", "").strip()
    if not api_key:
        return {"enabled": False, "reason": "未配置 MOONSHOT_API_KEY，已使用规则推荐。"}
    if not recommendations:
        return {"enabled": False, "reason": "暂无候选组合，无法进行智能体分析。"}

    model = MODEL
    prompt = build_agent_prompt(user_text, form_data, recommendations)
    try:
        from openai import OpenAI
    except ImportError:
        return {"enabled": False, "reason": "未安装 openai SDK，已回退规则推荐。"}

    try:
        client = OpenAI(api_key=api_key, base_url=BASE_URL)
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是 Kimi，由 Moonshot AI 提供的人工智能助手。"
                        "你将作为装机推荐顾问，输出安全、准确、结构化的建议。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=1.0,
        )
        output_text = ""
        if completion and completion.choices:
            output_text = str(completion.choices[0].message.content or "")
    except Exception as exc:
        return {"enabled": False, "reason": f"智能体调用失败，已回退规则推荐：{exc}"}
    parsed = _parse_agent_json(output_text)
    if not parsed:
        return {"enabled": False, "reason": "智能体返回不可解析，已回退规则推荐。"}

    choices = parsed.get("choices")
    if not isinstance(choices, list):
        choices = []

    normalized_choices = []
    for choice in choices[:3]:
        if not isinstance(choice, dict):
            continue
        combo_index = choice.get("combo_index")
        if not isinstance(combo_index, int):
            continue
        if combo_index < 1 or combo_index > len(recommendations):
            continue
        normalized_choices.append(
            {
                "rank": choice.get("rank"),
                "combo_index": combo_index,
                "reason": str(choice.get("reason", "")).strip(),
            }
        )

    return {
        "enabled": True,
        "summary": str(parsed.get("summary", "")).strip(),
        "choices": normalized_choices,
        "model": model,
    }
