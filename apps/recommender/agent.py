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
    user_text: str,
    form_data: Mapping[str, object],
    recommendations: Sequence[Mapping[str, object]],
) -> str:
    """构建 JSON 输出的提示词模板。"""
    prefs = {
        "user_text": user_text or "",
        "budget_min": form_data.get("budget_min", ""),
        "budget_max": form_data.get("budget_max", ""),
        "workload": form_data.get("workload", ""),
        "cpu_brand": form_data.get("cpu_brand", ""),
        "gpu_chip_brand": form_data.get("gpu_chip_brand", ""),
        "top_k": form_data.get("top_k", 3),
    }
    brief_recommendations = recommendations[:OUTPUT_CANDIDATES]
    combos = [
        combo_to_text(i + 1, item) for i, item in enumerate(brief_recommendations)
    ]

    prompt_template = (
        "你是 DIY 装机推荐助手，请基于用户偏好与候选组合给出推荐。\n"
        "要求：\n"
        "1) 从候选中推荐最多 {top_k} 套，按推荐优先级排序，尽量选择有所差异的。\n"
        "2) 每套理由控制在 1-2 句话，不能不写，突出场景匹配、预算、性能或性价比。\n"
        "3) summary 写 3 句左右，先结合 user_text 分析用户真实需求，再说明预算与性能取舍，最后给出选择建议。\n"
        "4) 如果用户写了具体游戏、软件、分辨率、剪辑/渲染等需求，summary 必须点名回应这些需求。\n"
        "5) 不要编造候选组合里没有的配件，不要输出 Markdown。\n"
        "6) 仅输出 JSON。\n"
        "JSON 格式：\n"
        "{{\n"
        '  "summary": "三句左右的需求分析与总体建议",\n'
        '  "choices": [\n'
        '    {{"rank": 1, "combo_index": 2, "reason": "理由"}},\n'
        '    {{"rank": 2, "combo_index": 1, "reason": "理由"}}\n'
        "  ]\n"
        "}}\n\n"
        "用户偏好:\n{prefs_json}\n\n"
        "候选组合(仅前 {max_combos} 条):\n{combos_text}"
    )

    return prompt_template.format(
        top_k=prefs["top_k"],
        prefs_json=json.dumps(prefs, ensure_ascii=False),
        max_combos=OUTPUT_CANDIDATES,
        combos_text="\n".join(combos)
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
    user_text: str,
    form_data: Mapping[str, object],
    recommendations: Sequence[Mapping[str, object]],
) -> Dict[str, object]:
    api_key = os.getenv(API_KEY_ENV_VAR, "").strip()
    if not api_key:
        return {
            "enabled": False,
            "reason": "未配置 " + API_KEY_ENV_VAR + "，已使用规则推荐。",
        }
    if not recommendations:
        return {"enabled": False, "reason": "暂无候选组合，无法进行智能体分析。"}

    model = MODEL
    prompt = build_agent_prompt(user_text, form_data, recommendations)
    client = get_agent_client()
    if client is None:
        return {"enabled": False, "reason": "未安装 openai SDK，已回退规则推荐。"}

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你将作为装机推荐顾问，为用户输出安全、准确、结构化的建议。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=TEMPERATURE,
            extra_body={"thinking": {"type": THINKING_TYPE}},
            timeout=AGENT_TIMEOUT_SECONDS,
        )
        output_text = ""
        if completion and completion.choices:
            output_text = str(completion.choices[0].message.content or "")
    except Exception as exc:
        return {"enabled": False, "reason": f"智能体调用失败，已回退规则推荐：{exc}"}
    parsed = parse_agent_json(output_text)
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
