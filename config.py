import os

class Config:
    # Clave secreta para proteger sesiones
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'mi_clave_secreta'
    
    # Configuración de la base de datos (MySQL con PyMySQL)
    MYSQL_USER = 'waikikip_admin'
    MYSQL_PASSWORD = 'K(ivE][]T1{b'
    MYSQL_HOST = 'localhost'
    MYSQL_PORT = 3306
    MYSQL_DB = 'waikikip_waikiki'
    
    # Cadena de conexión modificada para usar PyMySQL
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False