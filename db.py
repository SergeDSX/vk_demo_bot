from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
import settings

# аргумент pre_ping используется для проверки состояния соединения и перезапуска соединения в случае возникновения ошибки
engine = create_engine(settings.db_connection, pool_pre_ping=True)
db_session = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()
