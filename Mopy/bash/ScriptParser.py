# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash.  If not, see <https://www.gnu.org/licenses/>.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2023 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================
from __future__ import annotations

# Parser.py =======================================
#  A generic class for handling parsing of
#  scripts and equations.
#  - The following operators are supported by default:
#   + Addition
#   - Subtraction
#   * Multiplication
#   / Division
#   % Modulus
#   ^ Exponent
#   () Parenthesis
#  - The parser follows the order of operations
#  - Variables are also handled, all are treated
#    as float's.  The variable is initialized
#    on its first appearance to '0.0'.  Multiple
#    assignment is allowed, but only the default
#    assignment operator is defined by default
#  - Constants can be defined
#  - Keywords can be defined
#  - Functions can be defined
#
# Defined functions to use are:
#  SetOperator
#  SetKeyword
#  SetFunction
#  SetConstant
#  SetVariable
#  PushFlow
#  PopFlow
#  PeekFlow
#  LenFlow
#  PurgeFlow
#  RunLine
#  error
#  ExecuteTokens
#  TokensToRPN
#  ExecuteRPN
#==================================================
import operator
import os
from collections import defaultdict
from string import digits, whitespace

from . import bolt # no other Bash imports!

#--------------------------------------------------
name_start = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'
name_chars = f'{name_start}0123456789'

# validName ---------------------------------------
#  Test if a string can be used as a valid name
#--------------------------------------------------
def validName(string):
    try:
        if string[0] not in name_start: return False
        for i in string:
            if i not in name_chars: return False
        return True
    except (TypeError, KeyError): # TypeError means not iterable
        return False

# validNumber -------------------------------------
#  Test if a string can be used as a valid number
#--------------------------------------------------
def validNumber(string):
    try:
        float(string)
        if string == '.': return False
        return True
    except ValueError:
        return False

# Define Some Constants ---------------------------

# Some error string
def err_too_few_args(obj_type, obj_name, got, expected):
    error(f"Too few arguments to {obj_type} '{obj_name}':  got {got}, "
          f"expected {expected}.")
def err_too_many_args(obj_type, obj_name, got, expected):
    error(f"Too many arguments to {obj_type} '{obj_name}':  got {got}, "
          f"expected {expected}.")
def err_cant_set(obj_type, obj_name, type_enum):
    error(f"Cannot set {obj_type} '{obj_name}': type is '{Types[type_enum]}'.")

class KEY(object):
    # Constants for keyword args
    NO_MAX = -1     # No maximum arguments
    NA = 0          # Not a variable argument keyword

class OP(object):
    # Constants for operator precedences
    PAR = 0     # Parenthesis
    EXP = 1     # Exponent
    UNA = 2     # Unary (++, --)
    MUL = 3     # Multiplication (*, /, %)
    ADD = 4     # Addition (+, -)
    CO1 = 5     # Comparison (>=,<=,>,<)
    CO2 = 6     # Comparison (!=, ==)
    MEM = 7     # Membership test (a in b)
    NOT = 8     # Logical not (not, !)
    AND = 9     # Logical and (and, &)
    OR  = 10    # Logical or (or, |)
    ASS = 11    # Assignment (=,+=,etc

# Constants for operator associations
LEFT = 0
RIGHT = 1

# Constants for the type of a token
UNKNOWN = 0
NAME = 1            # Can be a name token, but not used yet
CONSTANT = 2
VARIABLE = 3
FUNCTION = 4
KEYWORD = 5
OPERATOR = 6
INTEGER = 7
DECIMAL = 8
OPEN_PARENS = 9
CLOSE_PARENS = 10
COMMA = 11
WHITESPACE = 12
STRING = 13
OPEN_BRACKET = 14
CLOSE_BRACKET = 15
COLON = 16

Types = {UNKNOWN:u'UNKNOWN',
         NAME:u'NAME',
         CONSTANT:u'CONSTANT',
         VARIABLE:u'VARIABLE',
         FUNCTION:u'FUNCTION',
         KEYWORD:u'KEYWORD',
         OPERATOR:u'OPERATOR',
         INTEGER:u'INTEGER',
         DECIMAL:u'DECIMAL',
         OPEN_PARENS:u'OPEN_PARENS',
         CLOSE_PARENS:u'CLOSE_PARENS',
         COMMA:u'COMMA',
         WHITESPACE:u'WHITESPACE',
         STRING:u'STRING',
         OPEN_BRACKET:u'OPEN_BRACKET',
         CLOSE_BRACKET:u'CLOSE_BRACKET',
         COLON:u'COLON',
}

# FlowControl -------------------------------------
#  Flow control object, to hold info about a flow
#  control statement
#--------------------------------------------------
class FlowControl(object):
    def __init__(self, statement_type, active, keywords=[], **attribs):
        self.type = statement_type
        self.active = active
        self.keywords = keywords
        for i in attribs:
            setattr(self, i, attribs[i])

# Token -------------------------------------------
#  Token object, to hold info about a token
#--------------------------------------------------

# ParserError -------------------------------------
#  So when we catch exceptions we know if it's a
#  problem with the parser, or a problem with the
#  script
#--------------------------------------------------
##: Refactor to use exception.ParserError instead?
class ParserError(SyntaxError): pass
gParser: 'Parser' = None
def error(msg):
    if gParser:
        raise ParserError(
            f'(Line {gParser.cLine}, Column {gParser.cCol}): {msg}')
    else:
        raise ParserError(msg)

# Parser ------------------------------------------
#  This is where the magic happens
#--------------------------------------------------
def _get_type_basic(token_or_num):
    """Determines a token's type without considering a parser's type system."""
    if isinstance(token_or_num, str): return STRING
    if isinstance(token_or_num, int): return INTEGER
    if isinstance(token_or_num, float): return DECIMAL
    return UNKNOWN

class Parser(object):

    def getType(self, token_or_num):
        """Determine a token's type in self's type system."""
        if isinstance(token_or_num, str): ##: use a dict here?
            if token_or_num in self.constants: return CONSTANT
            if token_or_num in self.variables: return VARIABLE
            if token_or_num in self.keywords : return KEYWORD
            if token_or_num in self.functions: return FUNCTION
            if token_or_num in self.operators: return OPERATOR
            if token_or_num == u'(': return OPEN_PARENS
            if token_or_num == u')': return CLOSE_PARENS
            if token_or_num == u'[': return OPEN_BRACKET
            if token_or_num == u']': return CLOSE_BRACKET
            if token_or_num == u':': return COLON
            if token_or_num == u',': return COMMA
            if validName(token_or_num): return NAME
            if validNumber(token_or_num):
                if u'.' in token_or_num: return DECIMAL
                return INTEGER
            for i in token_or_num:
                if i not in whitespace: return UNKNOWN
            return WHITESPACE
        return _get_type_basic(token_or_num)

    class Callable:
        def __init__(self, callable_name, function, min_args=0,
                     max_args=KEY.NA, passTokens=False, passCommas=False):
            self.callable_name = callable_name
            self.function = function
            self.passTokens = passTokens
            self.passCommas = passCommas
            if max_args == KEY.NA: max_args = min_args
            if min_args > max_args >= 0: max_args = min_args
            self.minArgs = min_args
            self.maxArgs = max_args

        @property
        def Type(self): return self.__class__.__name__

        def __call__(self, *args):
            # Remove commas if necessary, pass values if necessary
            if not self.passCommas or not self.passTokens:
                args = [(x.tkn,x)[self.passTokens] for x in args if x.type != COMMA or self.passCommas]
            return self.execute(*args)

        def execute(self, *args):
            # Ensure correct number of arguments
            numArgs = len(args)
            if self.maxArgs != KEY.NO_MAX and numArgs > self.maxArgs:
                if self.minArgs == self.maxArgs:
                    err_too_many_args(self.Type, self.callable_name, numArgs,
                                      self.minArgs)
                else:
                    err_too_many_args(self.Type, self.callable_name, numArgs,
                        f'min: {self.minArgs}, max: {self.maxArgs}')
            if numArgs < self.minArgs:
                args = self.Type, self.callable_name, numArgs
                if self.maxArgs == KEY.NO_MAX:
                    err_too_few_args(*args, f'min: {self.minArgs}')
                elif self.minArgs == self.maxArgs:
                    err_too_few_args(*args, self.minArgs)
                else:
                    err_too_few_args(*args, f'min: {self.minArgs}, '
                                            f'max: {self.maxArgs}')
            return self.function(*args)

    class Operator(Callable):
        def __init__(self, operator_name, function, precedence,
                     association=LEFT, passTokens=True):
            self.precedence = precedence
            self.association = association
            if self.precedence in (OP.UNA, OP.NOT):
                min_args = 1
            else:
                min_args = 2
            super().__init__(operator_name, function, min_args,
                             passTokens=passTokens)

    class Keyword(Callable):
        def __init__(self, keyword_name, function, min_args=0, max_args=KEY.NA,
                     passTokens=False, splitCommas=True, passCommas=False):
            self.splitCommas = splitCommas
            super().__init__(keyword_name, function, min_args, max_args,
                             passTokens, passCommas)

        def __call__(self, *args):
            gParser.StripOuterParens(args)
            if not self.splitCommas:
                return super().__call__(*args)
            args = gParser.SplitAtCommas(args)
            if not self.passTokens:
                if len(args) == 1:
                    if len(args[0]) > 0:
                        args = [gParser.ExecuteTokens(args[0])]
                    else:
                        args = []
                else:
                    for i,arg in enumerate(args):
                        if len(arg) > 0:
                            args[i] = gParser.ExecuteTokens(arg)
                        else:
                            args[i] = None
            return self.execute(*args)

    class Function(Callable):
        def __init__(self, function_name, function, min_args=0,
                     max_args=KEY.NA, passTokens=False, dotFunction=False):
            """function: function that will be called with the args
               num_args: number of args required for the function
               passTokens: whether tokens or the data within should be passed as args
               dotFunction: whether this function can be called using the dot operator
               """
            super().__init__(function_name, function, min_args, max_args,
                             passTokens)
            self.dotFunction = dotFunction

    class Token(object):
        def __init__(self, token_or_text, Type=None, parser=None, line=None,
                     pos=(None, None)):
            if isinstance(token_or_text, Parser.Token):
                self.text = token_or_text.text
                self.type = token_or_text.type
                self.parser = token_or_text.parser
                self.line = token_or_text.line
                self.pos = token_or_text.pos
                self.numArgs = token_or_text.numArgs
            else:
                self.text = token_or_text
                if Type:
                    # We were passed a type, so use that
                    self.type = Type
                elif parser:
                    # We have a parser, so we can query for reliable type info
                    self.type = parser.getType(token_or_text)
                else:
                    # We do not have a parser, so we can only query for basic
                    # type info
                    self.type = _get_type_basic(token_or_text)
                self.parser = parser
                self.line = line
                self.pos = pos
                self.numArgs = 0

        def GetData(self):
            """:rtype: Parser.Function | Parser.Keyword | Parser.Operator |
            str | int | float
            """
            if self.parser:
                if self.type == FUNCTION: return self.parser.functions[self.text]
                if self.type == KEYWORD : return self.parser.keywords[self.text]
                if self.type == OPERATOR: return self.parser.operators[self.text]
                if self.type == VARIABLE: return self.parser.variables[self.text]
                if self.type == CONSTANT: return self.parser.constants[self.text]
                if self.type == DECIMAL : return float(self.text)
                if self.type == INTEGER : return int(self.text)
            return self.text
        tkn = property(GetData) # did I catch all uses ?

        # Implement rich comparisons, __cmp__ is deprecated
        def __eq__(self, other):
            if isinstance(other, Parser.Token):
                return self.tkn == other.tkn
            return self.tkn == other
        def __ne__(self, other):
            if isinstance(other, Parser.Token):
                return self.tkn != other.tkn
            return self.tkn != other
        def __lt__(self, other):
            if isinstance(other, Parser.Token):
                return self.tkn < other.tkn
            return self.tkn < other
        def __le__(self, other):
            if isinstance(other, Parser.Token):
                return self.tkn <= other.tkn
            return self.tkn <= other
        def __gt__(self, other):
            if isinstance(other, Parser.Token):
                return self.tkn > other.tkn
            return self.tkn > other
        def __ge__(self, other):
            if isinstance(other, Parser.Token):
                return self.tkn >= other.tkn
            return self.tkn >= other

        def __add__(self, other): return Parser.Token(self.tkn + other.tkn)
        def __sub__(self, other): return Parser.Token(self.tkn - other.tkn)
        def __mul__(self, other): return Parser.Token(self.tkn * other.tkn)
        def __mod__(self, other): return Parser.Token(self.tkn % other.tkn)
        def __truediv__(self, other): return Parser.Token(self.tkn / other.tkn)
        def __floordiv__(self, other): return Parser.Token(self.tkn // other.tkn)
        def __divmod__(self, other): return Parser.Token(divmod(self.tkn, other.tkn))
        def __pow__(self, other): return Parser.Token(self.tkn ** other.tkn)
        def __lshift__(self, other): return Parser.Token(self.tkn << other.tkn)
        def __rshift__(self, other): return Parser.Token(self.tkn >> other.tkn)
        def __and__(self, other): return Parser.Token(self.tkn & other.tkn)
        def __xor__(self, other): return Parser.Token(self.tkn ^ other.tkn)
        def __or__(self, other): return Parser.Token(self.tkn | other.tkn)
        def __bool__(self): return bool(self.tkn)
        def __neg__(self): return Parser.Token(-self.tkn)
        def __pos__(self): return Parser.Token(+self.tkn)
        def __abs__(self): return abs(self.tkn)
        def __int__(self): return int(self.tkn)
        def __index__(self): return operator.index(self.tkn)
        def __float__(self): return float(self.tkn)
        def __str__(self): return str(self.tkn)

        def __repr__(self): return f'<Token-{Types[self.type]}:{self.text}>'

        # Fall through to function/keyword
        def __call__(self, *args, **kwdargs): return self.tkn(*args, **kwdargs)

    # Now for the Parser class
    def __init__(self,
                 doImplicit=u'*',
                 dotOperator=u'.',
                 comment=u';',
                 constants={u'True':True,u'False':False},
                 variables=None
                 ):
        self.doImplicit = doImplicit
        self.dotOperator = dotOperator
        self.comment = comment

        self.runon = False
        self.cLineStart = 0
        self.cCol = 0
        self.cLine = 0
        self.tokens = []
        self.Flow = []

        self.opChars = u''
        self.operators = {}
        self.keywords = {}
        self.functions = {}
        self.constants = constants or {}
        self.variables = variables or {}
        self.escapes = {u'n':u'\n',
                        u't':u'\t'
                        }

        self.word = None
        self.wordStart = None

        if dotOperator:
            self.SetOperator(dotOperator, self.opDotOperator, OP.PAR)
        # Special function
        self.functions[u']index['] = Parser.Function(u'<index>', self.fnIndex,
                                                     2, 4)

        global gParser
        gParser = self

    # Dummy function for the dot operator
    def opDotOperator(self, l, r): pass

    # Indexing operator function
    _marker = object()
    def fnIndex(self, item, start, stop=None, step=None):
        try:
            fn = u'item['

            # Start
            if start is not Parser._marker:
                fn += u'%i'% start
            elif stop is None:
                fn += u':'

            # Stop
            if stop is Parser._marker:
                fn += u':'
            elif stop is not None:
                fn += u':%i' % stop

            # Step
            if step is Parser._marker:
                fn += u':'
            elif step is not None:
                fn += u':%i' % step

            fn += u']'
            return eval(fn)
        except:
            error(_(u'Index out of bounds.'))

    def SetOperator(self, op_name, *args, **kwdargs):
        type_ = self.getType(op_name)
        if type_ not in [NAME,OPERATOR,UNKNOWN]:
            err_cant_set(u'operator', op_name,  type_)
        self.operators[op_name] = Parser.Operator(op_name, *args, **kwdargs)
        for i in op_name:
            if i not in self.opChars: self.opChars += i
    def SetKeyword(self, keywrd_name, *args, **kwdargs):
        type_ = self.getType(keywrd_name)
        if type_ not in [NAME,KEYWORD]:
            err_cant_set(u'keyword', keywrd_name,  type_)
        self.keywords[keywrd_name] = Parser.Keyword(keywrd_name, *args, **kwdargs)
    def SetFunction(self, fun_name, *args, **kwdargs):
        type_ = self.getType(fun_name)
        if type_ not in [NAME,FUNCTION]:
            err_cant_set(u'function', fun_name,  type_)
        self.functions[fun_name] = Parser.Function(fun_name, *args, **kwdargs)
    def SetConstant(self, const_name, value):
        type_ = self.getType(const_name)
        if type_ not in [NAME,CONSTANT]:
            err_cant_set(u'constant', const_name,  type_)
        self.constants[const_name] = value
    def SetVariable(self, var_name, value):
        type_ = self.getType(var_name)
        if type_ not in [NAME, VARIABLE]:
            err_cant_set(u'variable', var_name,  type_)
        self.variables[var_name] = value

    # Flow control stack
    def PushFlow(self, stmnt_type, active, keywords, **attribs):
        self.Flow.append(FlowControl(stmnt_type, active, keywords, **attribs))
    def PopFlow(self): return self.Flow.pop()
    def PopFrontFlow(self): return self.Flow.pop(0)
    def PeekFlow(self,index=-1): return self.Flow[index]
    def LenFlow(self): return len(self.Flow)
    def PurgeFlow(self): self.Flow = []

    # Run a line of code: returns True if more lines are needed to make a complete line, False if not
    def RunLine(self, line):
        # First reset tokens if we're starting a new line
        if not self.runon:
            self.cLineStart = self.cLine
            self.tokens = []

        # Now parse the tokens
        self.cLine += 1
        self.TokenizeLine(line)
        if self.runon: return True

        # No tokens?
        if len(self.tokens) == 0: return False

        # See if we're in currently within a flow control construct
        if self.LenFlow() > 0:
            i = self.PeekFlow()
            if not i.active and self.tokens[0].text not in i.keywords:
                return False

        # If we have a keyword, just run it
        if self.tokens[0].type == KEYWORD:
            kwrd = self.tokens.pop(0)
            kwrd(*self.tokens)
        # It's just an expression, didnt start with a keyword
        else:
            # Convert to reverse-polish notation and execute
            self.ExecuteTokens()
        return False

    # Removes any commas from a list of tokens
    def SkipCommas(self, tokens=None):
        if tokens is None:
            self.tokens = [x for x in self.tokens if x.type != COMMA]
            return self.tokens
        tokens = [x for x in tokens if x.type != COMMA]
        return tokens

    # Split tokens at commas
    def SplitAtCommas(self, tokens=None):
        tokens = tokens or self.tokens
        parenDepth = 0
        bracketDepth = 0
        ret = [[]]
        for tok in tokens:
            if tok.type == OPEN_PARENS:
                parenDepth += 1
            elif tok.type == CLOSE_PARENS:
                parenDepth -= 1
                if parenDepth < 0:
                    error(_(u'Mismatched parenthesis.'))
            elif tok.type == OPEN_BRACKET:
                bracketDepth += 1
            elif tok.type == CLOSE_BRACKET:
                bracketDepth -= 1
                if bracketDepth < 0:
                    error(_(u'Mismatched brackets.'))
            if tok.type == COMMA and parenDepth == 0 and bracketDepth == 0:
                    ret.append([])
            else:
                ret[-1].append(tok)
        return ret

    def StripOuterParens(self, tokens=None):
        tokens = tokens or self.tokens
        while len(tokens) > 2 and tokens[0].type == OPEN_PARENS and tokens[-1].type == CLOSE_PARENS:
            tokens = tokens[1:-1]
        return tokens

    # Split a string into tokens
    def TokenizeLine(self, line):
        self.word = None
        self.wordStart = None
        self.cCol = 0
        self.runon = False

        state = self._stateSpace
        for i in line:
            state = state(i)
            if not state: return None
            self.cCol += 1
        self._emit()
        return self.tokens

    # Run a list of tokens
    def ExecuteTokens(self, tokens=None):
        tokens = tokens or self.tokens
        self.TokensToRPN(list(tokens))
        return self.ExecuteRPN()

    # Convert a list of tokens to rpn
    def TokensToRPN(self, tokens=None):
        tokens = tokens or self.tokens
        rpn = []
        stack = []

        # Add an item to the rpn, and increase arg count for
        # the last parens
        def rpnAppend(item):
            for i in reversed(stack):
                if i.type in [OPEN_PARENS,OPEN_BRACKET]:
                    i.numArgs = 1
                    break
            rpn.append(item)

        # Now the rest of it
        for idex,i in enumerate(tokens):
            if i.type in [INTEGER,DECIMAL,CONSTANT,VARIABLE,NAME,STRING]:
                rpnAppend(i)
            elif i.type == COMMA:
                while len(stack) > 0 and stack[-1].type != OPEN_PARENS:
                    rpn.append(stack.pop())
                if len(stack) == 0:
                    error(_(u"Misplaced ',' or missing parenthesis."))
                if len(stack) > 1 and stack[-2].type == FUNCTION:
                    stack[-2].numArgs += stack[-1].numArgs
                    stack[-1].numArgs = 0
            elif i.type == COLON:
                temp_tokens = []
                while len(stack) > 0 and stack[-1].type != OPEN_BRACKET:
                    temp_tokens.append(stack.pop())
                if len(stack) <= 1:
                    error(_(u"Misplaced ':' or missing bracket."))
                stack[-2].numArgs += stack[-1].numArgs
                if len(temp_tokens) == 0 and stack[-1].numArgs == 0:
                    rpn.append(Parser.Token(Parser._marker,Type=UNKNOWN,parser=self))
                    stack[-2].numArgs += 1
                else:
                    rpn.extend(temp_tokens)
                stack[-1].numArgs = 0
            elif i.type == FUNCTION:
                stack.append(i)
            elif i.type == OPERATOR:
                # Dot operator
                if i.text == self.dotOperator:
                    if idex+1 >= len(tokens):
                        error(_(u'Dot operator: no function to call.'))
                    if tokens[idex+1].type != FUNCTION:
                        error(_(u"Dot operator: cannot access non-function '%s'.") % tokens[idex+1].text)
                    if not tokens[idex+1].tkn.dotFunction:
                        error(_(u"Dot operator: cannot access function '%s'.") % tokens[idex+1].text)
                    tokens[idex+1].numArgs += 1
                # Other operators
                else:
                    while len(stack) > 0 and stack[-1].type == OPERATOR:
                        if i.tkn.association == LEFT and i.tkn.precedence >= stack[-1].tkn.precedence:
                            rpn.append(stack.pop())
                        elif i.tkn.association == RIGHT and i.tkn.precedence > stack[-1].tkn.precedence:
                            rpn.append(stack.pop())
                        else:
                            break
                    if i.text == u'-':
                        # Special unary minus type
                        if idex == 0 or tokens[idex-1].type in [OPEN_BRACKET,OPEN_PARENS,COMMA,COLON,OPERATOR,KEYWORD]:
                            rpnAppend(Parser.Token(u'0',parser=self))
                    stack.append(i)
            elif i.type == OPEN_PARENS:
                stack.append(i)
            elif i.type == OPEN_BRACKET:
                stack.append(Parser.Token(u']index[', parser=self))
                stack.append(i)
            elif i.type == CLOSE_PARENS:
                while len(stack) > 0 and stack[-1].type != OPEN_PARENS:
                    rpn.append(stack.pop())
                if len(stack) == 0:
                    error(_(u'Unmatched parenthesis.'))
                numArgs = stack[-1].numArgs
                stack.pop()
                if len(stack) > 0 and stack[-1].type == FUNCTION:
                    stack[-1].numArgs += numArgs
                    rpn.append(stack.pop())
            elif i.type == CLOSE_BRACKET:
                temp_tokens = []
                while len(stack) > 0 and stack[-1].type != OPEN_BRACKET:
                    temp_tokens.append(stack.pop())
                if len(stack) == 0:
                    error(_(u'Unmatched brackets.'))
                numArgs = stack[-1].numArgs
                stack.pop()
                if len(temp_tokens) == 0 and numArgs == 0 and stack[-1].numArgs != 0:
                    rpn.append(Parser.Token(Parser._marker,Type=UNKNOWN,parser=self))
                    numArgs += 1
                rpn.extend(temp_tokens)
                stack[-1].numArgs += numArgs + 1
                if stack[-1].numArgs == 1:
                    error(_(u'Index out of bounds.'))
                rpn.append(stack.pop())
            else:
                error(_(u"Unrecognized token: '%s', type: %s") % (i.text, Types[i.type]))
        while len(stack) > 0:
            i = stack.pop()
            if i.type in [OPEN_PARENS,CLOSE_PARENS]:
                error(_(u'Unmatched parenthesis.'))
            rpn.append(i)
        self.rpn = rpn
        return rpn

    def ExecuteRPN(self, rpn=None):
        rpn = rpn or self.rpn

        stack = []
        for i in rpn:
            if i.type == OPERATOR:
                if len(stack) < (tkn_min_args := i.tkn.minArgs):
                    err_too_few_args('operator',i.text,len(stack),tkn_min_args)
                args = []
                while len(args) < tkn_min_args:
                    args.append(stack.pop())
                args.reverse()
                ret = i(*args)
                if isinstance(ret, list):
                    stack.extend([Parser.Token(x) for x in ret])
                else:
                    stack.append(Parser.Token(ret))
            elif i.type == FUNCTION:
                if len(stack) < i.numArgs:
                    err_too_few_args('function', i.text, len(stack), i.numArgs)
                args = []
                while len(args) < i.numArgs:
                    args.append(stack.pop())
                args.reverse()
                ret = i(*args)
                if isinstance(ret, list):
                    stack.extend([Parser.Token(x) for x in ret])
                else:
                    stack.append(Parser.Token(ret))
            else:
                stack.append(i)
        if len(stack) == 1:
            return stack[0].tkn
        error(_(u'Too many values left at the end of evaluation.'))

    def error(self, msg):
        raise ParserError(f'(Line {self.cLine}, Column {self.cCol}): {msg}')

    #Functions for parsing a line into tokens
    def _grow(self, c):
        if self.word: self.word += c
        else:
            self.word = c
            self.wordStart = self.cCol

    def _emit(self, word=None, type_=None):
        word = word or self.word
        if word is None: return
        if self.wordStart is None: self.wordStart = self.cCol - 1
        type_ = type_ or self.getType(word)

        # Try to figure out if it's multiple operators bunched together
        rightWord = None
        if type_ == UNKNOWN:
            for idex in range(len(word),0,-1):
                newType = self.getType(word[0:idex])
                if newType != UNKNOWN:
                    rightWord = word[idex:]
                    rightWordStart = self.wordStart + idex
                    word = word[0:idex]
                    break

        # Implicit multiplication
        if self.doImplicit:
            if len(self.tokens) > 0:
                left = self.tokens[-1].type
                if left in [CLOSE_PARENS,CLOSE_BRACKET]:
                    if type_ in [OPEN_PARENS, DECIMAL, INTEGER, FUNCTION, VARIABLE, CONSTANT, NAME]:
                        self.tokens.append(Parser.Token(self.doImplicit,OPERATOR,self,self.cLine))
                elif left in [DECIMAL,INTEGER]:
                    if type_ in [OPEN_PARENS, FUNCTION, VARIABLE, CONSTANT, NAME]:
                        self.tokens.append(Parser.Token(self.doImplicit,OPERATOR,self,self.cLine))
                elif left in [VARIABLE, CONSTANT, NAME]:
                    if type_ == OPEN_PARENS:
                        self.tokens.append(Parser.Token(self.doImplicit,OPERATOR,self,self.cLine))
        self.tokens.append(Parser.Token(word, type_, self, self.cLine, (self.wordStart, self.cCol)))
        self.word = None
        self.wordStart = None

        if rightWord is not None:
            state = self._stateSpace
            self.cCol = rightWordStart
            for i in rightWord:
                state = state(i)
                if not state: return
                self.cCol += 1

    def _stateSpace(self, c):
        self._emit()
        if c in whitespace: return self._stateSpace
        if c == u"'": return self._stateSQuote
        if c == u'"': return self._stateDQuote
        if c == u'\\': return self._stateEscape
        if c == self.comment: return self._stateComment
        self._grow(c)
        if c in name_start: return self._stateName
        if c in self.opChars: return self._stateOperator
        if c in digits: return self._stateNumber
        if c == u'.': return self._stateDecimal
        if c == u'(': return self._stateSpace
        if c == u'[': return self._stateSpace
        if c == u')': return self._stateEndBracket
        if c == u']': return self._stateEndBracket
        if c == u',': return self._stateSpace
        error(_(u"Invalid character: '%s'") % c)

    def _stateSQuote(self, c):
        if c == u'\\': return self._stateSQuoteEscape
        if c == u"'":
            if not self.word: self.word = u''
            self._emit(type_=STRING)
            return self._stateSpace
        if c == u'\n':
            error(_(u'Unterminated single quote.'))
        self._grow(c)
        return self._stateSQuote
    def _stateSQuoteEscape(self, c):
        if c in self.escapes: self._grow(self.escapes[c])
        else: self._grow(c)
        return self._stateSQuote

    def _stateDQuote(self, c):
        if c == u'\\': return self._stateDQuoteEscape
        if c == u'"':
            if not self.word: self.word = u''
            self._emit(type_=STRING)
            return self._stateSpace
        if c == u'\n':
            error(_(u'Unterminated double quote.'))
        self._grow(c)
        return self._stateDQuote
    def _stateDQuoteEscape(self, c):
        if c in self.escapes: self._grow(self.escapes[c])
        else: self._grow(c)
        return self._stateDQuote

    def _stateEscape(self, c):
        if c == u'\n':
            self.runon = True
            return
        return self._stateSpace(c)

    def _stateComment(self, c): return self._stateComment

    def _stateName(self, c):
        if c in name_chars:
            self._grow(c)
            return self._stateName
        if c in [u"'",u'"']:
            error(_(u'Unexpected quotation %s following name token.') % c)
        if c == u':' and self.word.endswith(u'in'):
            self._grow(c)
            return self._stateOperator
        return self._stateSpace(c)

    def _stateOperator(self, c):
        if c in self.opChars:
            self._grow(c)
            return self._stateOperator
        return self._stateSpace(c)

    def _stateNumber(self, c):
        if c in digits:
            self._grow(c)
            return self._stateNumber
        if c == u'.':
            self._grow(c)
            return self._stateDecimal
        if c in [u'"',u"'"]:
            error(_(u'Unexpected quotation %s following number token.') % c)
        return self._stateSpace(c)
    def _stateDecimal(self, c):
        if c in digits:
            self._grow(c)
            return self._stateDecimal
        if c in [u'"',u"'",u'.']:
            error(_(u'Unexpected %s following decimal token.') % c)
        return self._stateSpace(c)

    def _stateEndBracket(self, c):
        if c in [u'"',u"'"]:
            error(_(u'Unexpected quotation %s following parenthesis.') % c)
        return self._stateSpace(c)

UNEXPECTED = _("Unexpected '%s'.")

class PreParser(Parser):
    def __init__(self):
        super().__init__()
        #--Constants
        self.SetConstant('SubPackages', 'SubPackages')
        #--Operators
        #Assignment
        self.SetOperator('=' , self.Ass, OP.ASS, RIGHT)
        self.SetOperator('+=', self.AssAdd, OP.ASS, RIGHT)
        self.SetOperator('-=', self.AssMin, OP.ASS, RIGHT)
        self.SetOperator('*=', self.AssMul, OP.ASS, RIGHT)
        self.SetOperator('/=', self.AssDiv, OP.ASS, RIGHT)
        self.SetOperator('%=', self.AssMod, OP.ASS, RIGHT)
        self.SetOperator('^=', self.AssExp, OP.ASS, RIGHT)
        #Comparison
        self.SetOperator('==', self.opE, OP.CO2)
        self.SetOperator('!=', self.opNE, OP.CO2)
        self.SetOperator('>=', self.opGE, OP.CO1)
        self.SetOperator('>' , self.opG, OP.CO1)
        self.SetOperator('<=', self.opLE, OP.CO1)
        self.SetOperator('<' , self.opL, OP.CO1)
        self.SetOperator('==:', self.opEc, OP.CO2, passTokens=False)  # Case insensitive ==
        self.SetOperator('!=:', self.opNEc, OP.CO2, passTokens=False) # Case insensitive !=
        self.SetOperator('>=:', self.opGEc, OP.CO1, passTokens=False) # Case insensitive >=
        self.SetOperator('>:', self.opGc, OP.CO1, passTokens=False)   # Case insensitive >
        self.SetOperator('<=:', self.opLEc, OP.CO1, passTokens=False) # Case insensitive <=
        self.SetOperator('<:', self.opLc, OP.CO1, passTokens=False)   # Case insensitive <
        #Membership operators
        self.SetOperator('in', self.opIn, OP.MEM, passTokens=False)
        self.SetOperator('in:', self.opInCase, OP.MEM, passTokens=False) # Case insensitive in
        #Boolean
        self.SetOperator('&' , self.opAnd, OP.AND)
        self.SetOperator('and', self.opAnd, OP.AND)
        self.SetOperator('|', self.opOr, OP.OR)
        self.SetOperator('or', self.opOr, OP.OR)
        self.SetOperator('!', self.opNot, OP.NOT, RIGHT)
        self.SetOperator('not', self.opNot, OP.NOT, RIGHT)
        #Pre-increment/decrement
        self.SetOperator('++', self.opInc, OP.UNA)
        self.SetOperator('--', self.opDec, OP.UNA)
        #Math
        self.SetOperator('+', self.opAdd, OP.ADD)
        self.SetOperator('-', self.opMin, OP.ADD)
        self.SetOperator('*', self.opMul, OP.MUL)
        self.SetOperator('/', self.opDiv, OP.MUL)
        self.SetOperator('%', self.opMod, OP.MUL)
        self.SetOperator('^', self.opExp, OP.EXP, RIGHT)
        #--Functions
        self.SetFunction('CompareObVersion', self.fnCompareGameVersion, 1) # Retained for compatibility
        self.SetFunction('CompareGameVersion', self.fnCompareGameVersion, 1)
        self.SetFunction('CompareOBSEVersion', self.fnCompareSEVersion, 1) # Retained for compatibility
        self.SetFunction('CompareSEVersion', self.fnCompareSEVersion, 1)
        self.SetFunction('CompareOBGEVersion', self.fnCompareGEVersion, 1) # Retained for compatibility
        self.SetFunction('CompareGEVersion', self.fnCompareGEVersion, 1)
        self.SetFunction('CompareWBVersion', self.fnCompareWBVersion, 1)
        self.SetFunction('DataFileExists', self.fnDataFileExists, 1, KEY.NO_MAX)
        self.SetFunction('GetPluginLoadOrder', self.fn_get_plugin_lo, 1, 2)
        self.SetFunction('GetEspmStatus', self.fn_get_plugin_status, 1) # Retained for compatibility
        self.SetFunction('GetPluginStatus', self.fn_get_plugin_status, 1)
        self.SetFunction('EditINI', self.fnEditINI, 4, 5)
        self.SetFunction('DisableINILine',self.fnDisableINILine, 3)
        self.SetFunction('Exec', self.fnExec, 1)
        self.SetFunction('EndExec', self.fnEndExec, 1)
        self.SetFunction('str', self.fnStr, 1)
        self.SetFunction('int', self.fnInt, 1)
        self.SetFunction('float', self.fnFloat, 1)
        #--String functions
        self.SetFunction('len', self.fnLen, 1, dotFunction=True)
        self.SetFunction('endswith', self.fnEndsWith, 2, KEY.NO_MAX, dotFunction=True)
        self.SetFunction('startswith', self.fnStartsWith, 2, KEY.NO_MAX, dotFunction=True)
        self.SetFunction('lower', self.fnLower, 1, dotFunction=True)
        self.SetFunction('find', self.fnFind, 2, 4, dotFunction=True)
        self.SetFunction('rfind', self.fnRFind, 2, 4, dotFunction=True)
        #--String pathname functions
        self.SetFunction('GetFilename', self.fnGetFilename, 1)
        self.SetFunction('GetFolder', self.fnGetFolder, 1)
        #--Keywords
        self.SetKeyword('SelectSubPackage', self.kwdSelectSubPackage, 1)
        self.SetKeyword('DeSelectSubPackage', self.kwdDeSelectSubPackage, 1)
        # The keyowrds with 'espm' in their name are retained for backwards
        # compatibility only - use their 'plugin' equivalents instead
        self.SetKeyword('SelectEspm', self.kwd_select_plugin, 1)
        self.SetKeyword('SelectPlugin', self.kwd_select_plugin, 1)
        self.SetKeyword('DeSelectEspm', self.kwd_de_select_plugin, 1)
        self.SetKeyword('DeSelectPlugin', self.kwd_de_select_plugin, 1)
        self.SetKeyword('SelectAll', self.kwdSelectAll)
        self.SetKeyword('DeSelectAll', self.kwdDeSelectAll)
        self.SetKeyword('SelectAllEspms', self.kwd_select_all_plugins)
        self.SetKeyword('SelectAllPlugins', self.kwd_select_all_plugins)
        self.SetKeyword('DeSelectAllEspms', self.kwd_de_select_all_plugins)
        self.SetKeyword('DeSelectAllPlugins', self.kwd_de_select_all_plugins)
        self.SetKeyword('RenameEspm', self.kwd_rename_plugin, 2)
        self.SetKeyword('RenamePlugin', self.kwd_rename_plugin, 2)
        self.SetKeyword('ResetEspmName', self.kwd_reset_plugin_name, 1)
        self.SetKeyword('ResetPluginName', self.kwd_reset_plugin_name, 1)
        self.SetKeyword('ResetAllEspmNames', self.kwd_reset_all_plugin_names)
        self.SetKeyword('ResetAllPluginNames',self.kwd_reset_all_plugin_names)
        self.SetKeyword('Note', self.kwdNote, 1)
        self.SetKeyword('If', self.kwdIf, 1 )
        self.SetKeyword('Elif', self.kwdElif, 1)
        self.SetKeyword('Else', self.kwdElse)
        self.SetKeyword('EndIf', self.kwdEndIf)
        self.SetKeyword('While', self.kwdWhile, 1)
        self.SetKeyword('Continue', self.kwdContinue)
        self.SetKeyword('EndWhile', self.kwdEndWhile)
        self.SetKeyword('For', self.kwdFor, 3, KEY.NO_MAX, passTokens=True, splitCommas=False)
        self.SetKeyword('from', self.kwdDummy)
        self.SetKeyword('to', self.kwdDummy)
        self.SetKeyword('by', self.kwdDummy)
        self.SetKeyword('EndFor', self.kwdEndFor)
        self.SetKeyword('SelectOne', self.kwdSelectOne, 7, KEY.NO_MAX)
        self.SetKeyword('SelectMany', self.kwdSelectMany, 4, KEY.NO_MAX)
        self.SetKeyword('Case', self.kwdCase, 1)
        self.SetKeyword('Default', self.kwdDefault)
        self.SetKeyword('Break', self.kwdBreak)
        self.SetKeyword('EndSelect', self.kwdEndSelect)
        self.SetKeyword('Return', self.kwdReturn)
        self.SetKeyword('Cancel', self.kwdCancel, 0, 1)
        self.SetKeyword('RequireVersions', self.kwdRequireVersions, 1, 4)

    # Functions that depend on Bash internals (bass/bosh/bush/load_order)
    def fnCompareGameVersion(self, other_ver): raise NotImplementedError
    def fnCompareSEVersion(self, other_ver): raise NotImplementedError
    def fnCompareGEVersion(self, other_ver): raise NotImplementedError
    def fnCompareWBVersion(self, other_ver): raise NotImplementedError
    def fnDataFileExists(self, *args): raise NotImplementedError
    def fn_get_plugin_lo(self, fname, default_val=-1):raise NotImplementedError
    def fn_get_plugin_status(self, filename): raise NotImplementedError

    # keywords that depend on wizard Pages
    def kwdFor(self): raise NotImplementedError
    def kwdReturn(self): raise NotImplementedError
    def kwdCancel(self, msg=_('No reason given')): raise NotImplementedError
    def kwdRequireVersions(self, game, se='None', ge='None', wbWant='0.0'):
        raise NotImplementedError

    # Assignment operators
    def Ass(self, l, r):
        if l.type not in [VARIABLE,NAME]:
            error(_('Cannot assign a value to %s, type is %s.') % (
                l.text, Types[l.type]))
        self.variables[l.text] = r.tkn
        return r.tkn

    def AssAdd(self, l, r): return self.Ass(l, l+r)
    def AssMin(self, l, r): return self.Ass(l, l-r)
    def AssMul(self, l, r): return self.Ass(l, l*r)
    def AssDiv(self, l, r): return self.Ass(l, l/r)
    def AssMod(self, l, r): return self.Ass(l, l%r)
    def AssExp(self, l, r): return self.Ass(l, l**r)

    # Comparison operators
    def opE(self, l, r): return l == r

    def opEc(self, l, r):
        if isinstance(l, str) and isinstance(r, str):
            return l.lower() == r.lower()
        else:
            return l == r

    def opNE(self, l, r): return l != r

    def opNEc(self, l, r):
        if isinstance(l, str) and isinstance(r, str):
            return l.lower() != r.lower()
        else:
            return l != r

    def opGE(self, l, r): return l >= r

    def opGEc(self, l, r):
        if isinstance(l, str) and isinstance(r, str):
            return l.lower() >= r.lower()
        else:
            return l >= r

    def opG(self, l, r): return l > r

    def opGc(self, l, r):
        if isinstance(l, str) and isinstance(r, str):
            return l.lower() > r.lower()
        else:
            return l > r

    def opLE(self, l, r): return l <= r

    def opLEc(self, l, r):
        if isinstance(l, str) and isinstance(r, str):
            return l.lower() <= r.lower()
        else:
            return l <= r

    def opL(self, l, r): return l < r

    def opLc(self, l, r):
        if isinstance(l, str) and isinstance(r, str):
            return l.lower() < r.lower()
        else:
            return l < r

    # Membership tests
    def opIn(self, l, r): return l in r

    def opInCase(self, l, r):
        if isinstance(l, str) and isinstance(r, str):
            return l.lower() in r.lower()
        else:
            return l in r

    # Boolean operators
    def opAnd(self, l, r): return l and r
    def opOr(self, l, r): return l or r
    def opNot(self, l): return not l

    # Pre-increment/decrement
    def opInc(self, l):
        if l.type not in [VARIABLE,NAME]:
            error(_('Cannot increment %s, type is %s.') % (l.text, Types[l.type]))
        new_val = l.tkn + 1
        self.variables[l.text] = new_val
        return new_val
    def opDec(self, l):
        if l.type not in [VARIABLE,NAME]:
            error(_('Cannot decrement %s, type is %s.') % (l.text, Types[l.type]))
        new_val = l.tkn - 1
        self.variables[l.text] = new_val
        return new_val

    # Math operators
    def opAdd(self, l, r): return l + r
    def opMin(self, l, r): return l - r
    def opMul(self, l, r): return l * r
    def opDiv(self, l, r): return l / r
    def opMod(self, l, r): return l % r
    def opExp(self, l, r): return l ** r

    def fnEditINI(self, ini_name, section, setting, value, comment=''):
        self._handleINIEdit(ini_name, section, setting, value, comment, False)

    def fnDisableINILine(self, ini_name, section, setting):
        self._handleINIEdit(ini_name, section, setting, '', '', True)

    def _handleINIEdit(self, ini_name, section, setting, value, comment,
                       disable):
        raise NotImplementedError # needs ini_files.OBSEIniFile

    def fnExec(self, strLines):
        lines = strLines.split('\n')
        # Manual EndExec calls are illegal - if we don't check here, a wizard
        # could exploit this by doing something like this:
        #   Exec("EndExec(1)\nAnythingHere\nReturn")
        # ... which doesn't really cause harm, but is pretty strange and
        # inconsistent
        if any([l.strip().startswith('EndExec(') for l in lines]):
            error(UNEXPECTED % 'EndExec')
        lines.append(f'EndExec({len(lines) + 1:d})')
        self.lines[self.cLine:self.cLine] = lines
        self.ExecCount += 1

    def fnEndExec(self, numLines):
        if self.ExecCount == 0:
            error(UNEXPECTED % 'EndExec')
        del self.lines[self.cLine-numLines:self.cLine]
        self.cLine -= numLines
        self.ExecCount -= 1

    def fnStr(self, data_): return str(data_)

    def fnInt(self, data_):
        try:
            return int(data_)
        except ValueError:
            return 0

    def fnFloat(self, data_):
        try:
            return float(data_)
        except ValueError:
            return 0.0

    def fnLen(self, data_):
        try:
            return len(data_)
        except TypeError:
            return 0

    def fnEndsWith(self, String, *args):
        if not isinstance(String, str):
            error(_("Function 'endswith' only operates on string types."))
        return String.endswith(args)

    def fnStartsWith(self, String, *args):
        if not isinstance(String, str):
            error(_("Function 'startswith' only operates on string types."))
        return String.startswith(args)

    def fnLower(self, String):
        if not isinstance(String, str):
            error(_("Function 'lower' only operates on string types."))
        return String.lower()

    def fnFind(self, String, sub, start=0, end=-1):
        if not isinstance(String, str):
            error(_("Function 'find' only operates on string types."))
        if end < 0: end += len(String) + 1
        return String.find(sub, start, end)

    def fnRFind(self, String, sub, start=0, end=-1):
        if not isinstance(String, str):
            error(_("Function 'rfind' only operates on string types."))
        if end < 0: end += len(String) + 1
        return String.rfind(sub, start, end)

    def fnGetFilename(self, String): return os.path.basename(String)
    def fnGetFolder(self, String): return os.path.dirname(String)

    # Dummy keyword, for reserving a keyword, but handled by other keywords
    # (like from, to, and by)
    def kwdDummy(self): pass

    # Keywords, mostly for flow control (If, Select, etc)
    def kwdIf(self, bActive):
        if self.LenFlow() > 0 and self.PeekFlow().type == 'If' and not self.PeekFlow().active:
            #Inactive portion of an If-Elif-Else-EndIf statement, but we hit an If, so we need
            #To not count the next 'EndIf' towards THIS one
            self.PushFlow('If', False, ['If', 'EndIf'])
            return
        self.PushFlow('If', bActive, ['If', 'Else', 'Elif', 'EndIf'], ifTrue=bActive, hitElse=False)

    def kwdElif(self, bActive):
        if self.LenFlow() == 0 or self.PeekFlow().type != 'If' or self.PeekFlow().hitElse:
            error(UNEXPECTED % 'Elif')
        if self.PeekFlow().ifTrue:
            self.PeekFlow().active = False
        else:
            self.PeekFlow().active = bActive
            self.PeekFlow().ifTrue = self.PeekFlow().active or self.PeekFlow().ifTrue

    def kwdElse(self):
        if self.LenFlow() == 0 or self.PeekFlow().type != 'If' or self.PeekFlow().hitElse:
            error(UNEXPECTED % 'Else')
        if self.PeekFlow().ifTrue:
            self.PeekFlow().active = False
            self.PeekFlow().hitElse = True
        else:
            self.PeekFlow().active = True
            self.PeekFlow().hitElse = True

    def kwdEndIf(self):
        if self.LenFlow() == 0 or self.PeekFlow().type != 'If':
            error(UNEXPECTED % 'EndIf')
        self.PopFlow()

    def kwdWhile(self, bActive):
        if self.LenFlow() > 0 and self.PeekFlow().type == 'While' and not self.PeekFlow().active:
            # Within an un-true while statement, but we hit a new While, so we
            # need to ignore the next 'EndWhile' towards THIS one
            self.PushFlow('While', False, ['While', 'EndWhile'])
            return
        self.PushFlow('While', bActive, ['While', 'EndWhile'],
                      cLine=self.cLine - 1)

    def kwdContinue(self):
        #Find the next up While or For statement to continue from
        index = self.LenFlow()-1
        iType = None
        while index >= 0:
            iType = self.PeekFlow(index).type
            if iType in ['While','For']:
                break
            index -= 1
        if index < 0:
            # No while statement was found
            error(UNEXPECTED % 'Continue')
        #Discard any flow control statments that happened after
        #the While/For, since we're resetting either back to the
        #the While/For', or the EndWhile/EndFor
        while self.LenFlow() > index+1:
            self.PopFlow()
        flow = self.PeekFlow()
        if iType == 'While':
            # Continue a While loop
            self.cLine = flow.cLine
            self.PopFlow()
        else:
            # Continue a For loop
            if flow.ForType == 0:
                # Numeric loop
                if self.variables[flow.varname] == flow.end:
                    # For loop is done
                    self.PeekFlow().active = False
                else:
                    # keep going
                    self.cLine = flow.cLine
                self.variables[flow.varname] += flow.by
            elif flow.ForType == 1:
                # Iterator type
                flow.index += 1
                if flow.index == len(flow.List):
                    # Loop is done
                    self.PeekFlow().active = False
                else:
                    # Re-loop
                    self.cLine = flow.cLine
                    self.variables[flow.varname] = flow.List[flow.index]

    def kwdEndWhile(self):
        if self.LenFlow() == 0 or self.PeekFlow().type != 'While':
            error(UNEXPECTED % 'EndWhile')
        #Re-evaluate the while loop's expression, if needed
        flow = self.PopFlow()
        if flow.active:
            self.cLine = flow.cLine

    def kwdEndFor(self):
        if self.LenFlow() == 0 or self.PeekFlow().type != 'For':
            error(UNEXPECTED % 'EndFor')
        #Increment the variable, then test to see if we should end or keep going
        flow = self.PeekFlow()
        if flow.active:
            if flow.ForType == 0:
                # Numerical loop
                if self.variables[flow.varname] == flow.end:
                    #For loop is done
                    self.PopFlow()
                else:
                    #Need to keep going
                    self.cLine = flow.cLine
                    self.variables[flow.varname] += flow.by
            elif flow.ForType == 1:
                # Iterator type
                flow.index += 1
                if flow.index == len(flow.List):
                    self.PopFlow()
                else:
                    self.cLine = flow.cLine
                    self.variables[flow.varname] = flow.List[flow.index]
        else:
            self.PopFlow()

    def kwdSelectOne(self, *args):
        self._KeywordSelect(False, 'SelectOne', *args)

    def kwdSelectMany(self, *args):
        self._KeywordSelect(True, 'SelectMany', *args)

    def _KeywordSelect(self, param, param1, param2):
        raise NotImplementedError # needs PageSelect

    def kwdCase(self, value):
        if self.LenFlow() == 0 or self.PeekFlow().type != 'Select':
            error(UNEXPECTED % 'Case')
        if value in self.PeekFlow().values or str(value) in self.PeekFlow().values:
            self.PeekFlow().hitCase = True
            self.PeekFlow().active = True

    def kwdDefault(self):
        if self.LenFlow() == 0 or self.PeekFlow().type != 'Select':
            error(UNEXPECTED % 'Default')
        if self.PeekFlow().hitCase:
            return
        self.PeekFlow().active = True
        self.PeekFlow().hitCase = True

    def kwdBreak(self):
        if self.LenFlow() > 0 and self.PeekFlow().type == 'Select':
            # Break for SelectOne/SelectMany
            self.PeekFlow().active = False
        else:
            # Test for a While/For statement earlier
            index = self.LenFlow() - 1
            while index >= 0:
                if self.PeekFlow(index).type in ('While', 'For'):
                    break
                index -= 1
            if index < 0:
                # No while or for statements found
                error(UNEXPECTED % 'Break')
            self.PeekFlow(index).active = False

            # We're going to jump to the EndWhile/EndFor, so discard
            # any flow control structs on top of the While/For one
            while self.LenFlow() > index + 1:
                self.PopFlow()
            self.PeekFlow().active = False

    def kwdEndSelect(self):
        if self.LenFlow() == 0 or self.PeekFlow().type != 'Select':
            error(UNEXPECTED % 'EndSelect')
        self.PopFlow()

    # Package selection functions
    def kwdSelectSubPackage(self, subpackage):
        self._SelectSubPackage(True, subpackage)

    def kwdDeSelectSubPackage(self, subpackage):
        self._SelectSubPackage(False, subpackage)

    def _SelectSubPackage(self, bSelect, subpackage):
        raise NotImplementedError # needs self.sublist/installer

    def kwdSelectAll(self): self._SelectAll(True)
    def kwdDeSelectAll(self): self._SelectAll(False)

    def _SelectAll(self, bSelect):
       raise NotImplementedError # needs self.sublist/_plugin_enabled

    @staticmethod
    def _set_all_values(di, common_value):
        for k in di:
            di[k] = common_value

    def kwd_select_plugin(self, plugin_name):
        self._select_plugin(True, plugin_name)

    def kwd_de_select_plugin(self, plugin_name):
        self._select_plugin(False, plugin_name)

    def _select_plugin(self, should_activate, plugin_name):
        raise NotImplementedError # needs self._plugin_enabled

    def kwd_select_all_plugins(self): self._select_all_plugins(True)
    def kwd_de_select_all_plugins(self): self._select_all_plugins(False)

    def _select_all_plugins(self, should_activate):
        raise NotImplementedError # needs self._plugin_enabled

    def kwd_rename_plugin(self, plugin_name, new_plugin_name):
        plugin_name = self._resolve_plugin_rename(plugin_name)
        if plugin_name:
            # Keep same extension
            if plugin_name.fn_ext != new_plugin_name[-4:]:
                raise ParserError(_('Cannot rename %s to %s: the extensions '
                    'must match.') % (plugin_name, new_plugin_name))
            self.plugin_renames[plugin_name] = new_plugin_name

    def kwd_reset_plugin_name(self, plugin_name):
        plugin_name = self._resolve_plugin_rename(plugin_name)
        if plugin_name and plugin_name in self.plugin_renames:
            del self.plugin_renames[plugin_name]

    def _resolve_plugin_rename(self, plugin_name: str) -> bolt.FName | None:
        raise NotImplementedError # needs self._plugin_enabled

    def kwd_reset_all_plugin_names(self):
        self.plugin_renames.clear()

    def kwdNote(self, note):
        self.notes.append(f'- {note}\n')

    # instance vars defined outside init
    def Begin(self, wizard_file, wizard_dir):
        self._reset_vars()
        self.cLine = 0
        self.reversing = 0
        self.ExecCount = 0
        self._wizard_dir = wizard_dir
        try:
            with wizard_file.open('r', encoding='utf-8-sig') as wiz_script:
                # Ensure \n line endings for the script parser
                self.lines = [bolt.to_unix_newlines(x)
                              for x in wiz_script.readlines()]
            return None
        except UnicodeError:
            return _('Could not read the wizard file.  Please ensure it is '
                     'encoded in UTF-8 format.')
        except OSError:
            return _('Could not open wizard file')

    def _reset_vars(self):
        self.variables.clear()
        self.Flow = []
        self.notes = []
        self.plugin_renames = {}
        self.iniedits = defaultdict(bolt.LowerDict)

    # codebox stuff
    codeboxRemaps = {
        'Link': {
            # These are links that have different names than their text
            'SelectOne': 'SelectOne1',
            'SelectMany': 'SelectMany1',
            '=': 'Assignment',
            '+=': 'CompountAssignmentetc',
            '-=': 'CompountAssignmentetc',
            '*=': 'CompountAssignmentetc',
            '/=': 'CompountAssignmentetc',
            '^=': 'CompountAssignmentetc',
            '+': 'Addition',
            '-': 'Subtraction',
            '*': 'Multiplication',
            '/': 'Division',
            '^': 'Exponentiation',
            'and': 'Andampand',
            '&': 'Andampand',
            'or': 'Oror',
            '|': 'Oror',
            'not': 'Notnot',
            '!': 'Notnot',
            'in': 'Inin',
            'in:': 'CaseInsensitiveInin',
            '==': 'Equal',
            '==:': 'CaseinsensitiveEqual',
            '!=': 'NotEqual',
            '!=:': 'CaseinsensitiveNotEqual',
            '>=': 'GreaterThanorEqualgt',
            '>=:': 'CaseInsensitiveGreaterThanorEqualgt',
            '>': 'GreaterThangt',
            '>:': 'CaseInsensitiveGreaterThangt',
            '<=': 'LessThanorEquallt',
            '<=:': 'CaseInsensitiveLessThanorEquallt',
            '<': 'LessThanlt',
            '<:': 'CaseInsensitiveLessThanlt',
            '.': 'DotOperator',
            'SubPackages': 'ForContinueBreakEndFor',
        },
        'Text': {
            # These are symbols that need to be replaced to be xhtml compliant
            '&': '&amp;',
            '<': '&lt;',
            '<:': '&lt;:',
            '<=': '&lt;=',
            '<=:': '&lt;=:',
            '>': '&gt;',
            '>:': '&gt;:',
            '>=': '&gt;=',
            '>=:': '&gt;=:',
        },
        'Color': {
            # These are items that we want colored differently
            'in': 'blue',
            'in:': 'blue',
            'and': 'blue',
            'or': 'blue',
            'not': 'blue',
        },
    }

    def codebox(self, lines, pre=True, br=True):
        def colorize(text_, color='black', link=True):
            href = text_
            text_ = self.codeboxRemaps['Text'].get(text_, text_)
            if color != 'black' or link:
                color = self.codeboxRemaps['Color'].get(text_, color)
                text_ = '<span style="color:%s;">%s</span>' % (color, text_)
            if link:
                href = self.codeboxRemaps['Link'].get(href,href)
                text_ = f'<a href="#{href}">{text_}</a>'
            return text_
        self.cLine = 0
        outLines = []
        lastBlank = 0
        while self.cLine < len(lines):
            line = lines[self.cLine]
            self.cLine += 1
            self.tokens = []
            self.TokenizeLine(line)
            tokens = self.tokens
            line = line.strip('\r\n')
            lastEnd = 0
            dotCount = 0
            outLine = ''
            for i in tokens:
                start,stop = i.pos
                if start is not None and stop is not None:
                    # Not an inserted token from the parser
                    if i.type == STRING:
                        start -= 1
                        stop  += 1
                    # Padding
                    padding = line[lastEnd:start]
                    outLine += padding
                    lastEnd = stop
                    # The token
                    token_txt = line[start:stop]
                    # Check for ellipses
                    if i.text == '.':
                        dotCount += 1
                        if dotCount == 3:
                            dotCount = 0
                            outLine += '...'
                        continue
                    else:
                        while dotCount > 0:
                            outLine += colorize('.')
                            dotCount -= 1
                    if i.type == KEYWORD:
                        outLine += colorize(token_txt,'blue')
                    elif i.type == FUNCTION:
                        outLine += colorize(token_txt,'purple')
                    elif i.type in (INTEGER, DECIMAL):
                        outLine += colorize(token_txt,'cyan',False)
                    elif i.type == STRING:
                        outLine += colorize(token_txt,'brown',False)
                    elif i.type == OPERATOR:
                        outLine += colorize(i.text)
                    elif i.type == CONSTANT:
                        outLine += colorize(token_txt,'cyan')
                    elif i.type == NAME:
                        outLine += f'<i>{token_txt}</i>'
                    else:
                        outLine += token_txt
            if self.runon:
                outLine += ' \\'
            if lastEnd < len(line):
                comments = line[lastEnd:]
                if ';' in comments:
                    outLine += colorize(comments, 'green', False)
            if outLine == '':
                if len(outLines) != 0:
                    lastBlank = len(outLines)
                else:
                    continue
            else:
                lastBlank = 0
            if pre:
                outLine = f'<span class="code-n" style="display: inline;">' \
                          f'{outLine}</span>\n'
            else:
                if br:
                    outLine = f'<span class="code-n">{outLine}</span><br>\n'
                else:
                    outLine = f'<span class="code-n">{outLine}</span>'
            outLines.append(outLine)
        if lastBlank:
            outLines = outLines[:lastBlank]
        return outLines
