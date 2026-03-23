"""
协同过滤推荐（预留接口）

待积累足够的用户行为数据后实现：
- 基于用户的协同过滤
- 基于物品的协同过滤
- 矩阵分解
"""

from typing import Dict, List


class CollaborativeFilter:
    """协同过滤推荐器（占位符）"""

    def __init__(self):
        self.user_preferences = {}
        self.item_similarities = {}

    def load_user_data(self, user_id: int, preferences: Dict):
        """加载用户偏好数据"""
        self.user_preferences[user_id] = preferences

    def find_similar_users(self, user_id: int) -> List[int]:
        """找到相似用户"""
        # TODO: 实现用户相似度计算
        return []

    def recommend_for_user(self, user_id: int, budget: float) -> List[Dict]:
        """为用户生成推荐"""
        # TODO: 基于相似用户的偏好生成推荐
        return []

    def train(self):
        """训练模型"""
        # TODO: 实现模型训练逻辑
        pass


def placeholder_recommendation(user_id: int = None) -> Dict:
    """
    占位推荐函数

    在真实协同过滤实现前返回默认推荐
    """
    return {
        "message": "协同过滤推荐尚未启用",
        "fallback": True,
    }
