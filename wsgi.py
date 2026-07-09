import os
os.environ['ORACLE_PASSWORD'] = 'Larissa@240569'
os.environ['ORACLE_WALLET_PASSWORD'] = 'Larissa@240569'

import sys
sys.path.insert(0, '/home/ProjetoLinkteste/avarias-app')
from app import app as application
