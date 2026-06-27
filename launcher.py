from config import MYSQL_CONFIG
from common.database import CommonDatabase
from engine.sps_sql_generator_engine import SpsSqlGeneratorEngine


def main():
    database = CommonDatabase(MYSQL_CONFIG)

    sql_generator_engine = SpsSqlGeneratorEngine(database)

    sql = sql_generator_engine.generate_select_without_audit(
        table_name="uploaded_files"
    )
    
    print("DB CONFIG =", MYSQL_CONFIG)
    print("DATABASE NAME =", database.database_name)
    print("COLUMNS =", sql_generator_engine.get_columns("uploaded_files"))
    
    print(sql)

    database.close()


if __name__ == "__main__":
    main()

