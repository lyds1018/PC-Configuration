# 从 Django 框架导入 `AppConfig` 基类，这是所有应用配置的父类
from django.apps import AppConfig

# 定义一个名为 `AccountsConfig` 的配置类，继承自 `AppConfig`
class AccountsConfig(AppConfig):
	
	# 指定应用的名称为 `accounts`
	#这是 Django 用来识别和定位该应用的 Python 包名
    name = "accounts"
