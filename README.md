#PC-Configuration
1. 下载配置 UV  
2. 终端进入项目路径执行 
uv init --python 3.10, 
uv venv --python 3.10, 
.venv\Scripts\activate, 
uv sync  
3. 本地创建数据库 pc_db  
4. 配置数据库连接信息  
5. 终端进入项目路径执行 
.venv\Scripts\activate 
python data/sql/build_sql.py  
python data/sql/csv2sql.py  
python manage.py runserver  