import os
import shutil

basedir = os.path.abspath(os.path.dirname(__file__))

# Wallet path: primeiro tenta variavel de ambiente, depois local no projeto
wallet_dir = os.environ.get('ORACLE_WALLET_DIR') or os.path.join(basedir, 'Wallet_AvariasDB')

wallet_dir_simple = os.path.join(basedir, 'Wallet_AvariasDB')
if not os.path.exists(wallet_dir_simple) and os.path.exists(wallet_dir):
    shutil.copytree(wallet_dir, wallet_dir_simple, dirs_exist_ok=True)

import oracledb
oracledb.defaults.config_dir = wallet_dir_simple
oracledb.defaults.wallet_location = wallet_dir_simple
oracledb.defaults.wallet_password = os.environ.get('ORACLE_WALLET_PASSWORD', 'Larissa@240569')

ORACLE_USER = os.environ.get('ORACLE_USER', 'ADMIN')
ORACLE_PASSWORD = os.environ.get('ORACLE_PASSWORD', 'Larissa@240569')
ORACLE_DSN = os.environ.get('ORACLE_DSN', 'avariasdb_high')


def oracle_creator():
    return oracledb.connect(
        user=ORACLE_USER,
        password=ORACLE_PASSWORD,
        dsn=ORACLE_DSN,
        config_dir=wallet_dir_simple,
        wallet_location=wallet_dir_simple,
        wallet_password=oracledb.defaults.wallet_password,
        tcp_connect_timeout=20
    )


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'avarias-app-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = 'oracle+oracledb://'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'creator': oracle_creator
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
