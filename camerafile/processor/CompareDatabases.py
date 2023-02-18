from camerafile.core.MediaSetDatabase import MediaSetDatabase


class CompareDatabases:

    def __init__(self, db1, db2):
        print("Compare {db1} with {db2}".format(db1=db1, db2=db2))
        db1 = MediaSetDatabase.get(None, db_file=db1)
        db2 = MediaSetDatabase.get(None, db_file=db2)
        db1.initialize_cfm_connection()
        db2.initialize_cfm_connection()
        db1.compare(db2)
