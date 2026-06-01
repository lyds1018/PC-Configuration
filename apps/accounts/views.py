"""账户模块视图层"""

# 导入 Django 内置的用户注册表单
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render


def register(request):
    """处理用户注册请求"""
    # 若为 POST 请求，处理提交的表单数据
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            # 注册成功后重定向到登录页面
            return redirect("accounts:login")
    else:
        # GET 请求，创建空表单
        form = UserCreationForm()

    # 渲染注册页面
    return render(request, "registration/register.html", {"form": form})
