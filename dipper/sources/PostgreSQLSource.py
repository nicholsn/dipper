import psycopg2
import logging
import os
from dipper.sources.Source import Source


logger = logging.getLogger(__name__)


class PostgreSQLSource(Source):
    """
    Class for interfacing with remote Postgres databases
    """

    def __init__(self, name=None):
        super().__init__(name)
        return

    def fetch_from_pgdb(self, tables, cxn, limit=None, force=False):
        """
        Will fetch all Postgres tables from the specified database in the cxn connection parameters.
        This will save them to a local file named the same as the table, in tab-delimited format, including a header.
        :param tables: Names of tables to fetch
        :param cxn: database connection details
        :param limit: A max row count to fetch for each table
        :return: None
        """

        con = None
        try:
            con = psycopg2.connect(host=cxn['host'], database=cxn['database'], port=cxn['port'],
                                   user=cxn['user'], password=cxn['password'])
            cur = con.cursor()
            for t in tables:
                logger.info("Fetching data from table %s", t)
                self._getcols(cur, t)
                query = ' '.join(("SELECT * FROM", t))
                countquery = ' '.join(("SELECT COUNT(*) FROM", t))
                if limit is not None:
                    query = ' '.join((query, "LIMIT", str(limit)))
                    countquery = ' '.join((countquery, "LIMIT", str(limit)))

                outfile = '/'.join((self.rawdir,t))

                filerowcount = -1
                tablerowcount = -1
                if not force:
                    # check local copy.  assume that if the # rows are the same, that the table is the same
                    # TODO may want to fix this assumption
                    if os.path.exists(outfile):
                        # get rows in the file
                        filerowcount = self.file_len(outfile)
                        logger.info("rows in local file: %s", filerowcount)

                    # get rows in the table
                    # tablerowcount=cur.rowcount
                    cur.execute(countquery)
                    tablerowcount = cur.fetchone()[0]

                if force or filerowcount < 0 or (filerowcount-1) != tablerowcount:  # rowcount-1 because there's a header
                    if force:
                        logger.info("Forcing download of %s", t)
                    else:
                        logger.info("%s local (%d) different from remote (%d); fetching.", t, filerowcount, tablerowcount)
                    # download the file
                    logger.info("COMMAND:%s", query)
                    outputquery = "COPY ({0}) TO STDOUT WITH DELIMITER AS '\t' CSV HEADER".format(query)
                    with open(outfile, 'w') as f:
                        cur.copy_expert(outputquery, f)
                else:
                    logger.info("local data same as remote; reusing.")

        finally:
            if con:
                con.close()
        return

    def fetch_query_from_pgdb(self, qname, query, con, cxn, limit=None, force=False):
        """
        Supply either an already established connection, or connection parameters.
        The supplied connection will override any separate cxn parameter
        :param qname:  The name of the query to save the output to
        :param query:  The SQL query itself
        :param con:  The already-established connection
        :param cxn: The postgres connection information
        :param limit: If you only want a subset of rows from the query
        :return:
        """
        if con is None and cxn is None:
            logger.error("ERROR: you need to supply connection information")
            return
        if con is None and cxn is not None:
            con = psycopg2.connect(host=cxn['host'], database=cxn['database'], port=cxn['port'],
                                   user=cxn['user'], password=cxn['password'])

        outfile = '/'.join((self.rawdir, qname))
        cur = con.cursor()
        countquery = ' '.join(("SELECT COUNT(*) FROM (", query, ") x"))  # wrap the query to get the count
        if limit is not None:
            countquery = ' '.join((countquery, "LIMIT", str(limit)))

        # check local copy.  assume that if the # rows are the same, that the table is the same
        filerowcount = -1
        tablerowcount = -1
        if not force:
            if os.path.exists(outfile):
                # get rows in the file
                filerowcount = self.file_len(outfile)
                logger.info("INFO: rows in local file: %s", filerowcount)

            # get rows in the table
            # tablerowcount=cur.rowcount
            cur.execute(countquery)
            tablerowcount = cur.fetchone()[0]

        if force or filerowcount < 0 or (filerowcount-1) != tablerowcount:  # rowcount-1 because there's a header
            if force:
                logger.info("Forcing download of %s", qname)
            else:
                logger.info("%s local (%s) different from remote (%s); fetching.", qname, filerowcount, tablerowcount)
            # download the file
            logger.debug("COMMAND:%s", query)
            outputquery = "COPY ({0}) TO STDOUT WITH DELIMITER AS '\t' CSV HEADER".format(query)
            with open(outfile, 'w') as f:
                cur.copy_expert(outputquery, f)
            # Regenerate row count to check integrity
            filerowcount = self.file_len(outfile)
            if (filerowcount-1) != tablerowcount:
                raise Exception("Download from MGI failed, %s != %s", (filerowcount-1), tablerowcount)
        else:
            logger.info("local data same as remote; reusing.")

        return

        # TODO generalize this to a set of utils
    def _getcols(self, cur, table):
        """
        Will execute a pg query to get the column names for the given table.
        :param cur:
        :param table:
        :return:
        """
        query = ' '.join(("SELECT * FROM", table, "LIMIT 0"))  # for testing

        cur.execute(query)
        colnames = [desc[0] for desc in cur.description]
        logger.info("COLS (%s): %s", table, colnames)

        return