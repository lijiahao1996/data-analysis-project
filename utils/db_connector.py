# -*- coding: utf-8 -*-
"""统一数据库连接工厂"""
import os
import yaml
from pathlib import Path
from sqlalchemy import create_engine
from contextlib import contextmanager

def load_config():
    """加载 config.yaml，支持环境变量覆盖数据库连接参数（Docker 适配）"""
    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 环境变量覆盖数据库连接（Docker 环境通过环境变量注入 host/port/user/password）
    db = config.setdefault('database', {})
    if os.environ.get('DB_HOST'):
        db['host'] = os.environ['DB_HOST']
    if os.environ.get('DB_PORT'):
        db['port'] = int(os.environ['DB_PORT'])
    if os.environ.get('DB_USER'):
        db['user'] = os.environ['DB_USER']
    if 'DB_PASSWORD' in os.environ:
        db['password'] = os.environ['DB_PASSWORD']
    if os.environ.get('DB_NAME'):
        db['database'] = os.environ['DB_NAME']

    return config

def get_engine(config=None):
    """根据配置创建 SQLAlchemy Engine"""
    if config is None:
        config = load_config()
    db = config['database']
    if db['type'] == 'mysql':
        url = f"mysql+pymysql://{db['user']}:{db.get('password', '')}@{db['host']}:{db['port']}/{db['database']}?charset={db.get('charset', 'utf8mb4')}"
        engine = create_engine(url, pool_size=5, max_overflow=10, pool_pre_ping=True)
    else:  # sqlite fallback
        db_path = Path(__file__).parent.parent / db['path']
        engine = create_engine(f"sqlite:///{db_path}")
    return engine

@contextmanager
def get_connection(config=None):
    """获取数据库连接的上下文管理器"""
    engine = get_engine(config)
    with engine.connect() as conn:
        yield conn
