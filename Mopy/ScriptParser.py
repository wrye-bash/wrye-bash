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
#  AddBooleanOperator
#  AddBooleanOperators
#  AddAssignmentOperator
#  AddAssignmentOperators
#  AddKeyword
#  AddKeywords
#  AddConstant
#  AddConstants
#  AddVariable
#  AddVariables
#  AddFunction
#  AddFunctions
#  AddFlowControl
#  PopFlowControl
#  GetFlowControl
#  LenFlowControl
#  ClearFlowControl
#  RunLine
#  error
#  Eval
#==================================================
from string import digits, whitespace, letters
#--------------------------------------------------

# ParserError -------------------------------------
#  So when we catch exceptions we know if it's a
#  problem with the parser, or a problem with the
#  script
#--------------------------------------------------
class ParserError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
    
class Parser(object):
#    __slots__ = ( 'op_chars', 'ops_math', 'ops_bool', 'operators',
#                  'word', 'split_line', 'bStop', 'state',
#                  'parens', 'bInFn', 'Flow'
#                  'keywords', 'constants', 'vars', 'functions',
#                  'ops_ass', 'func_map'
#                  )
    op_chars = "+-/*%^="
    ops_math = ['+', '-', '*', '/', '%', '^']
    ops_ass = ['=']
    operators = ops_math

    class _flow:
        def __init__(self, type, active, keywords):
            self.type = type
            self.active = active
            self.keywords = keywords

    def _add_op_chars(self, operator):
        for i in operator:
            if i not in self.op_chars:
                self.op_chars += i

    def AddBooleanOperator(self, operator, function):
        self.func_map[operator] = function
        self.ops_bool.append(operator)
        self.operators.append(operator)
        self._add_op_chars(operator)
    def AddBooleanOperators(self, op_func_map):
        for i in op_func_map:
            self.AddBooleanOperator(i, op_func_map[i])
        
    def AddAssignmentOperator(self, operator, function):
        self.func_map[operator] = function
        self.ops_ass.append(operator)
        self.operators.append(operator)
        self._add_op_chars(operator)
    def AddAssignmentOperators(self, op_func_map):
        for i in op_func_map:
            self.AddAssignmentOperator(i, op_func_map[i])

    def AddKeyword(self, keyword, function):
        self.func_map[keyword] = function
        self.keywords.append(keyword)
    def AddKeywords(self, keyword_func_map):
        for i in keyword_func_map:
            self.AddKeyword(i, keyword_func_map[i])
            
    def AddConstant(self, constant, value=0):
        self.constants[constant] = value
    def AddConstants(self, const_val_map):
        for i in const_val_map:
            self.AddConstant(i, const_val_map[i])

    def AddVariable(self, var, value=0):
        self.vars[var] = value
    def AddVariables(self, var_val_map):
        for i in var_val_map:
            self.AddVariable(i, var_val_map[i])

    def AddFunction(self, name, function):
        self.func_map[name] = function
        self.functions.append(name)
    def AddFunctions(self, name_func_map):
        for i in name_func_map:
            self.AddFunction(i, name_func_map[i])

    def AddFlowControl(self, type, active, list_keywords, **attribs):
        obj = Parser._flow(type, active, list_keywords)
        for i in attribs:
            setattr(obj, i, attribs[i])
        self.Flow.append(obj)
    def PopFlowControl(self):
        return self.Flow.pop()
    def GetFlowControl(self, index):
        return self.Flow[index]
    def LenFlowControl(self):
        return len(self.Flow)
    def ClearFlowControl(self):
        self.Flow = []
    
    def __init__(self):
        self.bStop = False
        self.bInFn = False
        self.func_map = {}
        self.ops_bool = []
        self.keywords = []
        self.functions = []
        self.constants = {}
        self.vars = {}
        self.Flow = []
        self.AddAssignmentOperator('=',self.Assign)

    def Assign(self, var, value):
        self.vars[var] = value

    def RunLine(self, line):
        split = self._eat_line(line)

        if not split or len(split) == 0: return        

        #See if we're in a flow branching statement
        if len(self.Flow) != 0:
            i = self.GetFlowControl(-1)
            if not i.active and split[0] not in i.keywords:
                return
        if split[0] in self.keywords:
            word = split.pop(0)
            self.func_map[word](split)
        else:
            self.Eval(split)
                
    #Functions for parsing a line into tokesn
    def _eat_line(self, line):
        self.word = None
        self.state = self._state_space

        line = line.strip() + '\n'
        if not self.bStop:
            self.split_line = []
            self.bInFn = False
            self.parens = 0
        else:
            self.bStop = False

        for i in line:
            self.state(i)
            if self.bStop:
                break            

        if self.parens > 0:
            self.error("Unmatched parenthesis.")

        if self.bStop:
            return None
        return self.split_line

    def _newline(self):
        self.bStop = True

    def _emit_word(self, c=None):
        if c:
            self.split_line.append(c)
        elif self.word:
            self.split_line.append(self.word)
        else:
            self.split_line.append('')
        self.word = None

    def _grow_word(self, c):
        if self.word:
            self.word += c
        else:
            self.word = c

    def error(self, message):
        message += '\nVariables:\n' + str(self.vars) + '\n\nConstants:\n' + str(self.constants)
        raise ParserError(message)

    def _state_space(self, c):
        if c == '"':
            self.state = self._state_dquote
        elif c == "'":
            self.state = self._state_squote
        elif c == '\\':
            self.state = self._state_escape
        elif c in self.op_chars:
            self.word = c
            self.state = self._state_operator
        elif c in digits:
            self.word = c
            self.state = self._state_number
        elif c in letters or c == '_':
            self.word = c
            self.state = self._state_name
        elif c == '(':
            self.parens += 1
            self._emit_word('(')
        elif c == ')':
            self.parens -= 1
            if self.parens < 0:
                self.error("Unmatched parenthesis.")
            self._emit_word(')')
            self.state = self._state_paren
        elif c == ';':
            self.state = self._state_comment
        elif c == ',' and self.bInFn:
            self._emit_word(',')
        elif c not in whitespace:
            self.error("Unexpected character '" + c + "'.")

    def _state_comment(self, c):
        self._grow_word(c)

    def _state_squote(self, c):
        if c == '\\':
            self.state = self._state_squote_esc
        elif c == "'":
            self._emit_word()
            self.state = self._state_end_quote
        else:
            self._grow_word(c)

    def _state_dquote(self, c):
        if c == '\\':
            self.state = self._state_dquote_esc
        elif c == '"':
            self._emit_word()
            self.state = self._state_end_quote
        else:
            self._grow_word(c)

    def _state_squote_esc(self, c):
        if c == '\\' or c == "'" or c == '"':
            self._grow_word(c)
        elif c == 'n':
            self._grow_word('\n')
        elif c == 't':
            self._grow_word('\t')
        else:
            self.error("Invalid escape sequence '\\" + c + "'.")
        self.state = self._state_squote        

    def _state_dquote_esc(self, c):
        if c == '\\' or c == "'" or c == '"':
            self._grow_word(c)
        elif c == 'n':
            self._grow_word('\n')
        elif c == 't':
            self._grow_word('\t')
        else:
            self.error("Invalid escape sequence '\\" + c + "'.")
        self.state = self._state_dquote

    def _state_end_quote(self, c):
        if c == ')':
            self.parens -= 1
            if self.parens < 0:
                self.error("Unmatched parenthesis.")
            self._emit_word(')')
            self.state = self._state_paren
        elif c == ',' or c in whitespace:
            self.state = self._state_space
        elif c == ';':
            self.state = self._state_comment
        else:
            self.error("Unexpected '" + c + "' following quotation.")

    def _state_number(self, c):
        if c in digits:
            self.word += c
        elif c == '.':
            self.word += c
            self.state = self._state_decimal
        elif c in letters or c == '_':      #implicit multiplication
            self._emit_word()
            self._emit_word('*')
            self.word = c
            self.state = self._state_name
        elif c == '(':                      #implicit multiplication
            self.parens += 1
            self._emit_word()
            self._emit_word('*')
            self._emit_word('(')
            self.state = self._state_space
        elif c == ')':
            self._emit_word()
            self._emit_word(')')
            self.parens -= 1
            if self.parens < 0:
                self.error("Unmatched parenthesis.")
            self.state = self._state_paren
        elif c in self.op_chars:
            self._emit_word()
            self.word = c
            self.state = self._state_operator
        elif c == ',' and self.bInFn:
            self._emit_word()
            self._emit_word(',')
            self.state = self._state_space
        elif c in whitespace:
            self._emit_word()
            self.state = self._state_space
        elif c == ';':
            self._emit_word()
            self.state = self._state_comment
        else:
            self.error("Unexpected character '" + c + "'.")

    def _state_name(self, c):
        if c in letters or c in digits or c == '_':
            self.word += c
        elif c in whitespace:
            #Check if word is a function, if it is, error!
            if self.word in self.functions:
                self.error("Expected '(' after function '" + self.word + "'.")
            #If word isn't a var, const, or keyword, make a var
            if self.word in self.keywords and len(self.split_line) > 0:
                #Keywords should only occur as the first token on a line
                self.error("Unexpected keyword '" + self.word + "'.")
            if self.word not in self.keywords+self.constants.keys()+self.vars.keys():
                self.vars[self.word] = 0
            self._emit_word()
            self.state = self._state_space
        elif c == ',' and self.bInFn:
            if self.word in self.functions:
                self.error("Expected '(' after function '" + self.word + "'.")
            elif self.word in self.keywords:
                self.error("Unexpected keyword '" + self.word + "' inside function call.")
            elif self.word not in self.constants.keys()+self.vars.keys():
                self.vars[self.word] = 0
            self._emit_word()
            self._emit_word(',')
            self.state = self._state_space            
        elif c == ';':
            if self.word in self.functions:
                self.error("Expected '(' after function '" + self.word + "'.")
            if self.word not in self.keywords+self.constants.keys()+self.vars.keys():
                self.vars[self.word] = 0
            self._emit_word()
            self.state = self._state_comment
        elif c == '(':      #implicit multiplication
            #See if it's a function
            if self.word in self.functions:
                self._emit_word()
                self._emit_word('(')
            else:
                #it's not, so implied multiplication, see if we need to make a var first
                if self.word not in self.keywords and self.word not in self.constants and self.word not in self.vars:
                    self.vars[self.word] = 0
                self._emit_word()
                self._emit_word('*')
                self._emit_word('(')
            self.parens += 1
            self.state = self._state_space
        elif c == ')':
            self.parens -= 1
            if self.parens < 0:
                self.error("Unmatched parenthesis.")
            #Check if it's function, if it is, error!
            if self.word in self.functions:
                self.error("Unexpected ')' after function '" + self.word + "'.")
            if self.word in self.keywords:
                self.error("Unexpected ')' after keyword '" + self.word + "'.")
            if self.word not in self.constants.keys()+self.vars.keys():
                self.vars[self.word] = 0
            self._emit_word()
            self._emit_word(')')
            self.state = self._state_paren
        elif c in self.op_chars:
            if self.word in self.functions:
                self.error("Unexpected operator '" + c + "' after function '" + self.word + "'.")
            if self.word in self.keywords:
                self.error("Unexpected operator '" + c + "' after keyword '" + self.word + "'.")
            if self.word not in self.constants.keys()+self.vars.keys():
                self.vars[self.word] = 0
            self._emit_word()
            self.word = c
            self.state = self._state_operator
        else:
            self.error("Unexpected character '" + c + "'.")

    def _state_escape(self, c):
        if c == '\n':
            self._newline()
        elif c not in whitespace:
            self.error("Invalid escape sequence '\\" + c + "'.")

    def _state_paren(self, c):
        if c in whitespace:
            self.state = self._state_space
        elif c == ',' and self.bInFn:
            self._emit_word(',')
            self.state = self._state_space
        elif c == ';':
            self.state = self._state_comment
        elif c in digits:       #implicit multiplication
            self._emit_word('*')
            self.word = c
            self.state = self._state_number
        elif c in letters or c == '_':  #implicit multiplication
            self._emit_word('*')
            self.word = c
            self.state = self._state_name
        elif c == '(':      #implicit multiplication
            self.parens += 1
            self._emit_word('*')
            self._emit_word('(')
            self.state = self._state_space
        elif c == ')':
            self.parens -= 1
            if self.parens < 0:
                self.error("Unmatched parenthesis.")
            if self.parens == 0:
                self.bInFn = False
            self._emit_word(')')
        elif c in self.op_chars:
            self.word = c
            self.state = self._state_operator
        else:
            self.error("Unexpected character '" + c + "' following parenthesis.")

    def _state_decimal(self, c):
        if c in digits:
            self.word += c
        elif c == ';':
            self.word += '0'
            self._emit_word()
            self.state = self._state_comment
        elif c in letters or c == '_':  #implicit multiplication
            self.word += '0'
            self._emit_word()
            self._emit_word('*')
            self.word = c
            self.state = self._state_name
        elif c == '(':      #implicit multiplication
            self.word += '0'
            self._emit_word()
            self._emit_word('*')
            self._emit_word('(')
            self.word = c
            self.parens += 1
            self.state = self._state_space
        elif c == ')':
            self.parens -= 1
            if self.parens < 0:
                self.error("Unmatched parenthesis.")
            self.word += '0'
            self._emit_word()
            self._emit_word(')')
            self.state = self._state_paren
        elif c in self.op_chars:
            self.word += '0'
            self._emit_word()
            self.word = c
            self.state = self._state_operator
        elif c == ',' and self.bInFn:
            self.word += '0'
            self._emit_word()
            self._emit_word(',')
            self.state = self._state_space
        elif c in whitespace:
            self.word += '0'
            self._emit_word()
            self.state = self._state_space
        else:
            self.error("Unexpected character '" + c + "'.")

    def _state_operator(self, c):
        if c in self.op_chars:
            self.word += c
        elif c == '(':
            self.parens += 1
            if self.word not in self.operators:
                self.error("Invalid operator '" + self.word + "'.")
            self._emit_word()
            self._emit_word('(')
            self.state = self._state_space
        elif c in digits:
            if self.word not in self.operators:
                self.error("Invalid operator '" + self.word + "'.")
            self._emit_word()
            self.word = c
            self.state = self._state_number
        elif c in letters or c == '_':
            if self.word not in self.operators:
                self.error("Invalid operator '" + self.word + "'.")
            self._emit_word()
            self.word = c
            self.state = self._state_name
        elif c in whitespace:
            if self.word not in self.operators:
                self.error("Invalid operator '" + self.word + "'.")
            self._emit_word()
            self.state = self._state_space
        else:
            self.error("Unexpected '" + c + "' following operator '" + self.word + "'.")

    #End line parsing functions
    #------------------------------------

    def Eval(self, line):
        return self._EvalStep1(line)
    
    def _EvalStep1(self, line):
        #Step 1 - Handle assignment operators, multiple assignment is allowed
        if len(line) > 1 and line[1] in self.ops_ass:
            #Make sure first token is a variable
            if line[0] not in self.vars:
                self.error("Cannot assign a value to a non-variable.")
            #Make sure actually assigning something
            if len(line) == 2:
                self.error("Missing value following assignmen operator '" + line[1] + "'.")
            var = line.pop(0)
            op = line.pop(0)
            self.func_map[op](var, self._EvalStep1(line))
            return self.vars[var]
        #Step 1.1 - replace variables and constants with their values
        newline = []
        while len(line) > 0:
            i = line.pop(0)
            if i in self.constants:
                newline.append(self.constants[i])
            elif i in self.vars:
                newline.append(self.vars[i])
            else:
                newline.append(i)
        return self._EvalStep2(newline)

    def _EvalStep2(self, line):
        #Step 2 - Handle functions and parenthesis
        if '(' in line or ')' in line:
            newline = []
            newexpr = []
            parens = 0
            while len(line) > 0:
                i = line.pop(0)
                #Step 2.1 - handle parenthesis
                if i == '(':
                    if parens > 0:
                        newexpr.append(i)
                    parens += 1
                elif i == ')':
                    parens -= 1
                    if parens > 0:
                        newexpr.append(i)
                    else:
                        newline.append(self._EvalStep2(newexpr))
                        newexpr = []
                elif parens > 0:
                    newexpr.append(i)
                #Step 2.2 - handle functions
                elif i in self.functions:
                    parens = 1
                    line.pop(0)     #throw out next '(', it's for the function
                    params = []
                    newexpr = []
                    while parens > 0:
                        j = line.pop(0)
                        if j == '(':
                            parens += 1
                        elif j == ')':
                            parens -= 1
                        if parens == 1 and j == ',':    # Comma seperated arguments
                            if len(newexpr) > 1:
                                params.append(self._EvalStep2(newexpr))
                            elif len(newexpr) == 1:
                                params.append(newexpr[0])
                            newexpr = []
                        elif parens > 0:
                            newexpr.append(j)
                    if len(newexpr) > 1:
                        params.append(self._EvalStep2(newexpr))
                    elif len(newexpr) == 1:
                        params.append(newexpr[0])
                    #Evaluate the function
                    newline.append(self.func_map[i](params) or 0)
                #Not a parenthesis or function, so just add it on to the line
                else:
                    if parens > 0:
                        newexpr.append(i)
                    else:
                        newline.append(i)
            line = newline
            newline = []
        return self._EvalStep3(line)

    def _EvalStep3(self, line):
        #Step 3 - do boolean operators
        for op in self.ops_bool:
            if op in line:
                newline = []
                while len(line) > 0:
                    i = line.pop(0)
                    if i == op:
                        l = self._EvalStep4(newline)
                        r = self._EvalStep3(line)
                        return self.func_map[op](l, r)
                    else:
                        newline.append(i)
        return self._EvalStep4(line)

    def _EvalStep4(self, line):
        #Step 4 - do addition and subtraction
        if '+' in line or '-' in line:
            newline = []
            while True:
                i = line.pop(0)
                if i == '+':
                    l = self._EvalStep5(newline)
                    r = self._EvalStep4(line)
                    return l + r
                elif i == '-':
                    l = self._EvalStep5(newline)
                    r = self._EvalStep4(line)
                    return l - r
                else:
                    newline.append(i)
        else:
            return self._EvalStep5(line)

    def _EvalStep5(self, line):
        #Step 5 - do multiplication, division, and modulus
        if '*' in line or '/' in line or '%' in line:
            newline = []
            while True:
                i = line.pop(0)
                if i == '*':
                    l = self._EvalStep6(newline)
                    r = self._EvalStep5(line)
                    return l * r
                elif i == '/':
                    l = self._EvalStep6(newline)
                    r = self._EvalStep5(line)
                    if r == 0:
                        self.error("Division by 0")
                    else:
                        return l / r
                elif i == '%':
                    l = self._EvalStep6(newline)
                    r = self._EvalStep5(line)
                    return l % r
                else:
                    newline.append(i)
        else:
            return self._EvalStep6(line)

    def _EvalStep6(self, line):
        #Step 6 - do exponents
        if '^' in line:
            newline = []
            while True:
                i = line.pop(0)
                if i == '^':
                    if len(newline) > 1:
                        self.error("Unexpected tokens in expression: " + ' '.join(newline) + "^" + ' '.join(line))
                    try:
                        l = float(newline[0])
                    except:
                        self.error("Could not convert '" + str(newline[0]) + "' to a value.")
                    r = self._EvalStep6(line)
                    return l ** r
        else:
            if len(line) > 1:
                self.error("Unexpected tokens in expression: '" + ' '.join(line) + "'")
            try:
                return float(line[0])
            except:
                self.error("Could not convert '" + str(line[0]) + "' to a value.")
# End LineSplitter      
        
