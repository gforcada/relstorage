# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2016 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""
MySQL IDBDriver implementations.
"""
from __future__ import absolute_import
from __future__ import print_function

from ..._abstract_drivers import AbstractModuleDriver
from ..._abstract_drivers import implement_db_driver_options
from ..._sql import _Compiler

database_type = 'mysql'

class MySQLCompiler(_Compiler):

    def can_prepare(self):
        # If there are params, we can't prepare unless we're using
        # the binary protocol; otherwise we have to SET user variables
        # with extra round trips, which is worse.
        return not self.placeholders and super(MySQLCompiler, self).can_prepare()

    _PREPARED_CONJUNCTION = 'FROM'

    def _prepared_param(self, number):
        return '?'

    def _quote_query_for_prepare(self, query):
        return '"{query}"'.format(query=query)

class AbstractMySQLDriver(AbstractModuleDriver):

    # Don't try to decode pickle states as UTF-8 (or whatever the
    # environment is configured as); See
    # https://github.com/zodb/relstorage/issues/57. This varies
    # depending on Python 2/3 and which driver. Everything except
    # mysqlclient on Python 3 can handle all names being binary; that
    # driver, though, can only do that on Python 2. For Python 3, only
    # the character_set_results can be binary. (See
    # https://github.com/zodb/relstorage/issues/213)
    MY_CHARSET_STMT = 'SET names binary'

    # Does this driver need cursor.fetchall() called before a rollback?
    fetchall_on_rollback = False

    def cursor(self, conn):
        cursor = AbstractModuleDriver.cursor(self, conn)
        cursor.execute(self.MY_CHARSET_STMT)
        return cursor

    def callproc_multi_result(self, cursor, proc, args=()):
        """
        Some drivers need extra arguments to execute a statement that
        returns multiple results, and they don't all use the standard
        way to retrieve them, so use this.

        Returns a list of lists of rows: [ [[row in first], ...],
        [[row in second], ...], ... ]

        Note that, because 'CALL' potentially returns multiple result
        sets, there is potentially at least one extra database round
        trip involved when we call `cursor.nextset()`. If the
        procedure being called is very short or returns only a single
        very small result, this may add substantial overhead.

        As of PyMySQL 0.9.3, mysql-connector-python 8.0.16 and MySQLdb
        (mysqlclient) 1.4.2 using libmysqlclient.21.so (from mysql8)
        or libmysqlclient.20 (mysql 5.7), all the drivers use the
        flags from the server to detect that there are no more results
        and turn nextset() into a simple flag check. So if the CALL
        only returns one result set (because the CALLed object doesn't
        return any of its own, i.e., it only has side-effects) there
        shouldn't be any penalty.
        """
        cursor.execute('CALL ' + proc, args)

        multi_results = [cursor.fetchall()]
        while cursor.nextset():
            multi_results.append(cursor.fetchall())
        return multi_results


    sql_compiler_class = MySQLCompiler


implement_db_driver_options(
    __name__,
    'mysqlconnector', 'mysqldb', 'pymysql',
)
