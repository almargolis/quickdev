import random
import sqlite3
import subprocess

from qdcore import rdbms

random.seed()

word_list = [
    "cat",
    "dog",
    "pig",
    "carrot",
    "ham",
    "turkey",
    "fish",
    "elephant",
    "tiger",
    "snake",
    "purple",
    "orange",
    "red",
    "green",
    "violet",
    "rainbow",
    "jim",
    "bill",
    "mary",
    "jane",
    "al",
    "lizzie",
    "angie",
    "ben",
    "emily",
    "soloman",
]

test_database_def = [
    {
        "name": "movie_1",
        "fields": [
            {
                "name": "thing_1",
            },
            {
                "name": "thing_2",
            },
            {
                "name": "thing_3",
            },
        ],
    },
    {
        "name": "movie_2",
        "fields": [
            {
                "name": "thing_a",
            },
            {
                "name": "thing_b",
            },
            {
                "name": "thing_c",
            },
        ],
    },
]


def test_swap(tmpdir):
    path = tmpdir.join("test.db")
    rdb = rdbms.RdbmsSqLite(path=path)


def create_test_db():
    p = subprocess.Popen(["echo", "Hello World!"], stdout=subprocess.PIPE)
    stdout, _ = p.communicate()

    assert stdout == b"Hello World!\n"


def create_test_sqlite_db(tmpdir):
    # This creates a test database using the standard sqlite api
    path = tmpdir.join("test2.db")
    con = sqlite3.connect(path)
    cur = con.cursor()
    for ix_t, this_table in enumerate(test_database_def):
        create_query = f"CREATE TABLE {this_table['name']}("
        for ix_f, this_field in enumerate(this_table["fields"]):
            if ix_f > 0:
                create_query += ", "
            create_query += f"{this_field['name']}"
        create_query += ")"
        print(create_query)
        cur.execute(create_query)
    res = cur.execute("SELECT name FROM sqlite_master")
    schema_query_results = res.fetchall()
    schema_table_names = []
    for this_table_schema in schema_query_results:
        schema_table_names.append(this_table_schema[0])

    for this_table in test_database_def:
        # result is like [('movie',), ('movie2',)]
        assert this_table["name"] in schema_table_names
    return path


def make_data(test_table_schema):
    data = []
    for ix_r in range(5):
        data_rec = []
        for ix_f in range(len(test_table_schema["fields"])):
            data_rec.append(random.choice("word_list"))
    data.append(data_rec)
    return data


def test_rdbms_basics(tmpdir):
    path = create_test_sqlite_db(tmpdir)
    qdrdbms = rdbms.RdbmsSqLite(path=path)
    qdrdbms.connect()
    for this_table in test_database_def:
        assert this_table["name"] in qdrdbms.tables
    test_table_schema = test_database_def[0]
    test_table_name = test_table_schema["name"]
    qdtable = qdrdbms.open_table(test_table_name)
    data = make_data(test_table_schema)
    for this_data_rec in data:
        qdtable.insert(this_data_rec)
