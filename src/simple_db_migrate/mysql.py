from cli import CLI
import MySQLdb
import sys

class MySQL(object):
    
    def __init__(self, db_config_file="simple-db-migrate.conf", mysql_driver=MySQLdb, drop_db_first=False):
        self.__cli = CLI()
        
        # read configurations
        try:
            f = open(db_config_file, "r")
            exec(f.read())
        except IOError:
            self.__cli.error_and_exit("%s: file not found" % db_config_file)
        else:
            f.close()
        
        self.__mysql_driver = mysql_driver
        self.__mysql_host__ = HOST
        self.__mysql_user__ = USERNAME
        self.__mysql_passwd__ = PASSWORD
        self.__mysql_db__ = DATABASE
        self.__version_table = "__db_version__"
        
        if drop_db_first:
            self._drop_database()
            
        self._create_database_if_not_exists()
        self._create_version_table_if_not_exists()

    def __mysql_connect(self, connect_using_db_name=True):
        try:
            if connect_using_db_name:
                return self.__mysql_driver.connect(host=self.__mysql_host__, user=self.__mysql_user__, passwd=self.__mysql_passwd__, db=self.__mysql_db__)
        
            return self.__mysql_driver.connect(host=self.__mysql_host__, user=self.__mysql_user__, passwd=self.__mysql_passwd__)
        except Exception, e:
            self.__cli.error_and_exit("could not connect to database (%s)" % e)
    
    def __execute(self, sql):
        db = self.__mysql_connect()
        cursor = db.cursor()
        try:
            cursor.execute(sql)
            cursor.close()        
            db.commit()
            db.close()
        except Exception, e:
            db.rollback()
            db.close()
            self.__cli.error_and_exit("error executing migration (%s)" % e)
    
    def _drop_database(self):
        db = self.__mysql_connect(False)
        try:
            db.query("drop database %s;" % self.__mysql_db__)
        except Exception, e:
            self.__cli.error_and_exit("can't drop database '%s'; database doesn't exist" % self.__mysql_db__)
        db.close()
        
    def _create_database_if_not_exists(self):
        db = self.__mysql_connect(False)
        db.query("create database if not exists %s;" % self.__mysql_db__)
        db.close()
    
    def _create_version_table_if_not_exists(self):
        # create version table
        sql = "create table if not exists %s ( version varchar(20) NOT NULL default \"0\" );" % self.__version_table
        self.__execute(sql)
        
        # check if there is a register there
        db = self.__mysql_connect()
        cursor = db.cursor()
        cursor.execute("select count(*) from %s;" % self.__version_table)
        count = cursor.fetchone()[0]
        db.close()

        # if there is not a version register, insert one
        if count == 0:
            sql = "insert into %s (version) values (\"0\");" % self.__version_table
            self.__execute(sql)
    
    def __change_db_version(self, version, up=True):
        if up:
            # moving up and storing history
            sql = "insert into %s (version) values (\"%s\");" % (self.__version_table, str(version))
        else:
            # moving down and deleting from history
            sql = "delete from %s where version >= \"%s\";" % (self.__version_table, str(version))
        self.__execute(sql)
    
    def change(self, sql, new_db_version, up=True):
        self.__execute(sql)
        self.__change_db_version(new_db_version, up)
        
    def get_current_schema_version(self):
        db = self.__mysql_connect()
        cursor = db.cursor()
        cursor.execute("select version from %s order by version desc limit 0,1;" % self.__version_table)
        version = cursor.fetchone()[0]
        db.close()
        return version
    
    def get_all_schema_versions(self):
        versions = []
        db = self.__mysql_connect()
        cursor = db.cursor()
        cursor.execute("select version from %s order by version;" % self.__version_table)
        all_versions = cursor.fetchall()
        for version in all_versions:
            versions.append(version[0])
        db.close()
        versions.sort()
        return versions