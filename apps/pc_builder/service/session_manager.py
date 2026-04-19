from ..catalog import SELECTION_SESSION_KEY


def get_session_selection(request):
    """获取session中的选择"""
    return request.session.get(SELECTION_SESSION_KEY, {})


def save_session_selection(request, selected):
    """保存选择到session"""
    request.session[SELECTION_SESSION_KEY] = selected
