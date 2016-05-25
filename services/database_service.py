# coding:utf-8
from logging import getLogger
from peewee import Proxy
from playhouse.pool import PooledMySQLDatabase
from service import Service

__all__ = [ "DataBaseService" ]

DB_CONNECTION_MAX_NUM = 4

class PooledMySQLDatabaseWithReconnection(PooledMySQLDatabase):
    """Mysql connection pool support reconnection"""
    def execute_sql(self, sql, params=None, require_commit=True):
        """override and support reconnect"""
        log = getLogger('peewee.pool')
        try:
            return super(PooledMySQLDatabaseWithReconnection, self) \
                        .execute_sql(sql, params, require_commit)
        except Exception as exe:
            typeName = type( exe ).__name__
            if typeName in ('OperationalError', ):
                try:
                    log.info("try to close current connection")
                    if(not self.is_closed()):
                        log.info("try to close connection")
                        self.close()
                    log.info("try to re-execute current sql")
                    cursor = self.get_cursor()
                    cursor.execute(sql, params or ())
                    if require_commit and self.get_autocommit():
                        self.commit()
                    return cursor
                except Exception as exc:
                    raise RuntimeError('reconnection failed: %s' \
                                       % unicode( exc ))
            raise

class DataBaseService(Service):
    """Manage all services"""
    def __init__(self, env, host, port, user, passwd, db):
        super(DataBaseService, self).__init__(env)
        self._db_proxy = Proxy()
        self._conn_info = dict(host=host, port=port, \
                               user=user, passwd=passwd, \
                               db=db)

    def on_active(self):
        super(DataBaseService, self).on_active()
        conn_info = self._conn_info.copy()
        db_name = conn_info.pop('db')
        database = PooledMySQLDatabaseWithReconnection(
            db_name,
            max_connections=DB_CONNECTION_MAX_NUM,
            stale_timeout=300,
            threadlocals=True,
            **conn_info
        )
        self._db_proxy.initialize( database )
        self._db_proxy.connect()

    def get_db(self):
        return self._db_proxy