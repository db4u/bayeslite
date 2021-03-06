# -*- coding: utf-8 -*-

#   Copyright (c) 2010-2016, MIT Probabilistic Computing Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from collections import namedtuple

from bayeslite.exception import BQLParseError
from bayeslite.util import casefold

from bayeslite.metamodels.cgpm_schema.parse import flatten
from bayeslite.metamodels.cgpm_schema.parse import intersperse

import grammar

'''
grep -o 'K_[A-Z][A-Z0-9_]*' < grammar.y | sort -u | awk '
{
    sub("^K_", "", $1);
    printf("    '\''%s'\'': grammar.K_%s,\n", tolower($1), $1);
}'
'''

KEYWORDS = {
    'cluster': grammar.K_CLUSTER,
    'context': grammar.K_CONTEXT,
    'concentration': grammar.K_CONCENTRATION,
    'dependent': grammar.K_DEPENDENT,
    'ensure': grammar.K_ENSURE,
    'in': grammar.K_IN,
    'independent': grammar.K_INDEPENDENT,
    'of': grammar.K_OF,
    'parameter': grammar.K_PARAMETER,
    'row': grammar.K_ROW,
    'rows': grammar.K_ROWS,
    'set': grammar.K_SET,
    'singleton': grammar.K_SINGLETON,
    'to': grammar.K_TO,
    'variable': grammar.K_VARIABLE,
    'variables': grammar.K_VARIABLES,
    'view': grammar.K_VIEW,
    'within': grammar.K_WITHIN,
}

PUNCTUATION = {
    '(': grammar.T_LROUND,
    ')': grammar.T_RROUND,
    '*': grammar.T_STAR,
    ',': grammar.T_COMMA,
}

def parse(tokens):
    semantics = CGpmAlterSemantics()
    parser = grammar.Parser(semantics)
    for token in tokenize(tokens):
        semantics.context.append(token)
        if len(semantics.context) > 10:
            semantics.context.pop(0)
        parser.feed(token)
    if semantics.errors:
        raise BQLParseError(semantics.errors)
    if semantics.failed:
        raise BQLParseError(['parse failed mysteriously'])
    assert semantics.phrases is not None
    return semantics.phrases

def tokenize(tokenses):
    for token in intersperse(',', [flatten(tokens) for tokens in tokenses]):
        if isinstance(token, str):
            if casefold(token) in KEYWORDS:
                yield KEYWORDS[casefold(token)], token
            elif token in PUNCTUATION:
                yield PUNCTUATION[token], token
            else:               # XXX check for alphanumeric/_
                yield grammar.L_NAME, token
        elif isinstance(token, (int, float)):
            yield grammar.L_NUMBER, token
        else:
            raise IOError('Invalid token: %r' % (token,))
    yield 0, ''                 # EOF

class CGpmAlterSemantics(object):

    def __init__(self):
        self.context = []
        self.errors = []
        self.failed = False
        self.phrases = None

    def accept(self):
        pass
    def parse_failed(self):
        self.failed = True

    def syntax_error(self, (token, text)):
        if token == -1:         # error
            self.errors.append('Bad token: %r' % (text,))
        else:
            self.errors.append("Syntax error near [%s] after [%s]" % (
                text, ' '.join([str(t) for (_t, t) in self.context[:-1]])))

    def p_alter_start(self, ps):                self.phrases = ps

    def p_phrases_one(self, p):                 return [p] if p else []
    def p_phrases_many(self, ps, p):
        if p: ps.append(p)
        return ps

    def p_phrase_none(self,):                   return None

    def p_phrase_set_var_dependency(self, cols, dep):
        return SetVarDependency(cols, dep)

    def p_phrase_set_var_cluster(self, cols0, col1):
        return SetVarCluster(cols0, col1)

    def p_phrase_set_var_cluster_singleton(self, cols):
        return SetVarCluster(cols, SingletonCluster)

    def p_phrase_set_var_cluster_conc(self, conc):
        return SetVarClusterConc(conc)

    def p_phrase_set_row_cluster(self, rows0, row1, col):
        return SetRowCluster(rows0, row1, col)

    def p_phrase_set_row_cluster_singleton(self, rows0, col):
        return SetRowCluster(rows0, SingletonCluster, col)

    def p_phrase_set_row_cluster_conc(self, col, conc):
        return SetRowClusterConc(col, conc)

    def p_dependency_independent(self):         return EnsureIndependent
    def p_dependency_dependent(self):           return EnsureDependent

    def p_columns_one(self, col):               return [col]
    def p_columns_all(self):                    return SqlAll
    def p_columns_many(self, cols):             return cols

    def p_column_list_one(self, col):           return [col]
    def p_column_list_many(self, cols, col):    cols.append(col); return cols

    def p_column_name_n(self, n):               return n

    def p_rows_one(self, row):                  return [row]
    def p_rows_all(self):                       return SqlAll
    def p_rows_many(self, rows):                return rows

    def p_row_list_one(self, row):              return [row]
    def p_row_list_many(self, rows, row):       rows.append(row); return rows

    def p_row_index_n(self, n):                 return n

    def p_concentration_c(self, n):             return n


SetVarDependency = namedtuple('SetVarCluster', [
    'columns',          # columns to modify
    'dependency'        # INDEPENDENT or DEPENDENT
])

SetVarCluster = namedtuple('SetVarCluster', [
    'columns0',         # columns to modify
    'column1'           # context column
])

SetVarClusterConc = namedtuple('SetVarClusterConc', [
    'concentration'     # real valued concentration parameter
])

SetRowCluster = namedtuple('SetRowCluster', [
    'rows0',            # rows to modify
    'row1',             # row whose cluster to move rows0 to
    'column'            # context column
])

SetRowClusterConc = namedtuple('SetRowClusterConc', [
    'column',           # context column
    'concentration'     # real valued concentration parameter
])

SqlAll = 'SqlAll'
EnsureDependent = 'EnsureDependent'
EnsureIndependent = 'EnsureIndependent'
SingletonCluster = 'SingletonCluster'
