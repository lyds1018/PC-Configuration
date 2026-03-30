from django.test import SimpleTestCase

from .agent import build_agent_prompt, run_agent_recommendation


class AgentRecommendationTests(SimpleTestCase):
    def test_build_agent_prompt_contains_preferences_and_combo(self):
        prompt = build_agent_prompt(
            user_text="预算一万，主要游戏",
            form_data={"budget_min": "8000", "budget_max": "12000", "workload": "game"},
            recommendations=[
                {
                    "total_price": 9999,
                    "scores": {"total_score_100": 88.2},
                    "combo_value_100": 76.3,
                    "parts": {},
                }
            ],
        )
        self.assertIn("用户偏好", prompt)
        self.assertIn("候选组合", prompt)
        self.assertIn("总分=88.2/100", prompt)

    def test_run_agent_recommendation_fallback_without_key(self):
        result = run_agent_recommendation(
            user_text="测试",
            form_data={},
            recommendations=[{"parts": {}, "scores": {}, "total_price": 1, "combo_value_100": 1}],
        )
        self.assertFalse(result["enabled"])
        self.assertIn("MOONSHOT_API_KEY", result.get("reason", ""))
