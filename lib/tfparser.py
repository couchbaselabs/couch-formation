##
##

import ply.lex as lex
import sys


class tfvars(object):
    reserved = {
        'variable': 'VARIABLE',
        'description': 'DESCRIPTION',
        'default': 'DEFAULT',
        'type': 'TYPE',
    }
    tokens = [
        'NUMBER',
        'EQUALS',
        'COMMA',
        'QUOTETEXT',
        'TEXT',
        'LCURLY',
        'RCURLY',
        'LBRACKET',
        'RBRACKET',
        'LPAREN',
        'RPAREN',
    ] + list(reserved.values())
    t_EQUALS = r'='
    t_COMMA = r','
    t_LCURLY = r'\{'
    t_RCURLY = r'\}'
    t_LBRACKET = r'\['
    t_RBRACKET = r'\]'
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_ignore = ' \t'

    def __init__(self):
        self.lexer = lex.lex(module=self)
        # self.parser = yacc.yacc(module=self)
        self.tf_var_file = None
        self.tf_var_data = None
        self.current_token = None
        self.next_token = None

    def t_COMMENT(self, t):
        r'\#.*'
        pass

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    def t_error(self, t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    def t_VARIABLE(self, t):
        r'variable'
        return t

    def t_DESCRIPTION(self, t):
        r'description'
        return t

    def t_DEFAULT(self, t):
        r'default'
        return t

    def t_TYPE(self, t):
        r'type'
        return t

    def t_QUOTETEXT(self, t):
        # r'"[a-zA-Z0-9/\(\)_\. -]*"'
        r'"([^"]|\\")*"'
        return t

    def t_TEXT(self, t):
        r'[a-zA-Z_][a-zA-Z_0-9\(\)-]*'
        if t.value in tfvars.reserved:
            t.type = tfvars.reserved[t.value]
        return t

    def t_NUMBER(self, t):
        r'\d+'
        t.value = int(t.value)
        return t

    def read_file(self, filename):
        variable_data = []
        try:
            with open(filename, 'r') as varFile:
                self.tf_var_data = varFile.read()
                self.tf_var_file = filename
            varFile.close()
        except OSError as e:
            print("Can not read global variable file: %s" % str(e))
            raise Exception("tfvars: read_file: can not read file %s" % filename)
        self.lexer.input(self.tf_var_data)
        while True:
            try:
                variable_parameters = self.parse_variable_block()
                variable_data.append(variable_parameters)
            except Exception as e:
                print("Syntax error: %s" % str(e))
                sys.exit(1)
            if not self.next_token:
                return variable_data

    def get_token(self):
        if self.next_token:
            tok = self.next_token
        else:
            tok = self.lexer.token()
        self.next_token = self.lexer.token()
        return tok

    def get_keyword(self, type):
        tok = self.get_token()
        if not tok:
            raise Exception("unexpected end of file")
        if tok.type != type:
            raise Exception("expecting %s at line %d position %d" % (type, tok.lineno, tok.lexpos))

    def get_value(self):
        tok = self.get_token()
        if not tok:
            raise Exception("unexpected end of file")
        if tok.type == 'LBRACKET':
            value = self.get_list()
            self.get_keyword('RBRACKET')
        elif tok.type == 'LCURLY':
            value = self.get_variable_values()
            self.get_keyword('RCURLY')
        else:
            value = tok.value
            if isinstance(value, str):
                value = value.strip('"')
        return value

    def get_list(self, list_value=None):
        if not list_value:
            list_value = []
        element = self.get_value()
        list_value.append(element)
        if self.next_token.type != 'RBRACKET':
            self.get_keyword('COMMA')
            list_value = self.get_list(list_value)
        return list_value

    def get_variable_values(self, value_block=None):
        if not value_block:
            value_block = {}
        key = self.get_value()
        self.get_keyword('EQUALS')
        value = self.get_value()
        value_block[key] = value
        if self.next_token.type == 'COMMA':
            self.get_keyword('COMMA')
        if self.next_token.type != 'RCURLY':
            value_block = self.get_variable_values(value_block)
        return value_block

    def parse_variable_block(self):
        variable_block = {}
        self.get_keyword('VARIABLE')
        variable_block['name'] = self.get_value()
        self.get_keyword('LCURLY')
        value_block = self.get_variable_values()
        variable_block.update(value_block)
        self.get_keyword('RCURLY')
        return variable_block
