from enum import Enum
import hashlib
import sys

class TokenType(Enum):
        NUMBER = 1
        SYMBOL = 2
        SPACE = 3
        LIST = 4
        STRING = 5

class LaxerContext:
        now_start_pos: int
        content: str
        tokens: list[list]

        def __init__(self, content: str):
                self.content = content
                self.tokens = [[TokenType.SPACE]]
                self.now_start_pos = 0
        def clone_without_tokens(self):
                lc = LaxerContext(self.content)
                lc.now_start_pos = self.now_start_pos
                return lc

def parser(context: LaxerContext):
        braces_stack = 0
        i = context.now_start_pos
        in_comment = False
        in_block_comment = False
        while True:
                if i < context.now_start_pos:
                        i = context.now_start_pos

                if i >= len(content):
                        return context

                ch = content[i]
                if in_block_comment:
                        if ch == '}':
                                in_block_comment = False
                elif in_comment:
                        if ch == '\n':
                                in_comment = False
                elif context.tokens[-1][0] != TokenType.STRING and ch == ';':
                        if context.tokens[-1][0] != TokenType.SPACE:
                                context.tokens.append([TokenType.SPACE,])
                        in_comment = True
                elif context.tokens[-1][0] != TokenType.STRING and ch == '{':
                        if context.tokens[-1][0] != TokenType.SPACE:
                                context.tokens.append([TokenType.SPACE,])
                        in_block_comment = True
                elif context.tokens[-1][0] == TokenType.STRING:
                        if ch == '"':
                                if content[i-1] == '\\':
                                        context.tokens[-1][1] += ch
                                else:
                                        context.tokens.append([TokenType.SPACE])
                        else:
                                context.tokens[-1][1] += ch

                elif ch == ' ' or ch == '\n':
                        if context.tokens[-1][0] != TokenType.SPACE:
                                context.tokens.append([TokenType.SPACE,])
                elif ch == '(' or ch == '[':
                        braces_stack += 1
                        context.now_start_pos += 1
                        new_context = context.clone_without_tokens()
                        new_context.now_start_pos = context.now_start_pos
                        sublist_context = parser(new_context)
                        context.now_start_pos = sublist_context.now_start_pos - 1
                        if new_context.tokens != None:
                                context.tokens.append([TokenType.LIST] + new_context.tokens)
                elif ch == ')' or ch == ']':
                        braces_stack -= 1
                        if braces_stack == -1:
                                return context
                elif ch == '-' and context.tokens[-1][0] == TokenType.SPACE:
                        context.tokens.append([TokenType.NUMBER, ch])
                elif ch == 'x' and context.tokens[-1][0] == TokenType.NUMBER:
                        context.tokens[-1][1] += ch
                elif ord(ch) >= ord('0') and ord(ch) <= ord('9'):
                        if context.tokens[-1][0] == TokenType.SYMBOL:
                                context.tokens[-1][1] += ch
                        elif context.tokens[-1][0] != TokenType.NUMBER:
                                context.tokens.append([TokenType.NUMBER, ch])
                        else:
                                context.tokens[-1][1] += ch
                elif ch == '"':
                        context.tokens.append([TokenType.STRING, ""])
                else:
                        if context.tokens[-1][0] == TokenType.NUMBER:
                                context.tokens[-1][1] += ch
                        elif context.tokens[-1][0] != TokenType.SYMBOL:
                                context.tokens.append([TokenType.SYMBOL, ch])
                        else:
                                context.tokens[-1][1] += ch

                context.now_start_pos += 1
                i+=1

def fasthash(str_):
        return '_sl' + str(hashlib.md5(bytes(str_, encoding='utf-8')).hexdigest())

class ExpanderContext():
        aliases: dict
        asm_fields: dict
        passes: dict
        def __init__(self):
                self.aliases = {}
                self.asm_fields = {}
                self.passes = {}

def process_set_ex(context, exp):
        sublist_context, sublist_exp = expand(context, exp[2])
        context.aliases[exp[0][1]] = sublist_exp
        return context, None

def process_set_hyper(context, exp):
        sublist_context, sublist_exp = expand(context, exp[2])
        return context, sublist_exp

def to_int(str_):
        if str_[0:2] == '0x':
                return int(str_[2:], base=16)
        elif str_[0:2] == '0b':
                return int(str_[2:], base=2)
        else:
                return int(str_)

def process_macro_add(context, exp):
        sublist_context1, sublist_exp1 = expand(context, exp[0])
        sublist_context2, sublist_exp2 = expand(context, exp[2])
        return context, [TokenType.NUMBER, str(to_int(sublist_exp1[1]) + to_int(sublist_exp2[1]))]

def process_macro_sub(context, exp):
        sublist_context1, sublist_exp1 = expand(context, exp[0])
        sublist_context2, sublist_exp2 = expand(context, exp[2])
        return context, [TokenType.NUMBER, str(to_int(sublist_exp1[1]) - to_int(sublist_exp2[1]))]

def process_macro_mul(context, exp):
        sublist_context1, sublist_exp1 = expand(context, exp[0])
        sublist_context2, sublist_exp2 = expand(context, exp[2])
        return context, [TokenType.NUMBER, str(to_int(sublist_exp1[1]) * to_int(sublist_exp2[1]))]

def process_macro_div(context, exp):
        sublist_context1, sublist_exp1 = expand(context, exp[0])
        sublist_context2, sublist_exp2 = expand(context, exp[2])
        return context, [TokenType.NUMBER, str(to_int(sublist_exp1[1]) / to_int(sublist_exp2[1]))]

def process_macro_if(context, exp):
        sublist_context1, sublist_exp1 = expand(context, exp[0])
        sublist_context2, sublist_exp2 = expand(context, exp[2])
        sublist_context3, sublist_exp3 = expand(context, exp[4])
        if sublist_exp1[0] == TokenType.SYMBOL and sublist_exp1[1] == '#t':
                return context, sublist_exp2
        else:
                return context, sublist_exp3

def process_macro_eq(context, exp):
        sublist_context1, sublist_exp1 = expand(context, exp[0])
        sublist_context2, sublist_exp2 = expand(context, exp[2])
        return context, [TokenType.SYMBOL, '#t' if to_int(sublist_exp1[1]) == to_int(sublist_exp2[1]) else '#f']

def process_macro_symbol_eq(context, exp):
        sublist_context1, sublist_exp1 = expand(context, exp[0])
        sublist_context2, sublist_exp2 = expand(context, exp[2])
        return context, [TokenType.SYMBOL, '#t' if sublist_exp1[1] == sublist_exp2[1] else '#f']

def get_support_keyword_list(exp):
        ret = []
        for e in exp[1:]:
                if e[0] == TokenType.SPACE:
                        continue
                ret.append(e[1])
        return ret

def process_define_pass(context, exp):
        keywords = get_support_keyword_list(exp[0])
        context.passes[exp[2][2][1]] = (keywords, exp[2], exp[4])
        return context, None

def collect_bindings(obj, bindings, support_keywords, exp, fatherexp, pos_of_fatherexp):
        if obj[0] == TokenType.SYMBOL:
                if obj[1] == '...':
                        pass
                elif obj[1] not in support_keywords:
                        bindings[obj[1]] = (fatherexp, pos_of_fatherexp, obj)
        elif obj[0] == TokenType.LIST:
                for i, e in enumerate(obj[1:]):
                        if e[0] == TokenType.SPACE:
                                pass
                        else:
                                collect_bindings(e, bindings, support_keywords, exp[i+1], exp, i+1)

def use_bindings(ruleexp: list, bindings, support_keywords, ret):
        if ruleexp[0] == TokenType.LIST:
                for i, e in enumerate(ruleexp[1:]):
                        if e[0] == TokenType.SPACE:
                                pass
                        elif e[0] == TokenType.SYMBOL and e[1] == '...':
                                # todo: 删掉这段循环，或把整个复杂转换器写出来
                                for j in range(pos+2, len(from_exp), 2):
                                        import copy
                                        subbindings = {}
                                        collect_bindings(from_rule, subbindings, support_keywords, from_exp[j], from_exp[j], None)
                                        subret = copy.deepcopy(ruleexp[i-1])
                                        use_bindings(ruleexp[i-1], subbindings, support_keywords, subret)
                                        ret[i+1] = from_exp[j]
                        else:
                                from_exp, pos, from_rule = use_bindings(e, bindings, support_keywords, ret[i+1])
        elif ruleexp[0] == TokenType.SYMBOL:
                if ruleexp[1] in bindings.keys():
                        from_exp, pos, from_rule = bindings[ruleexp[1]]
                        if pos == None:
                                ret[:] = from_exp
                        else:
                                ret[:] = from_exp[pos]
                        return from_exp, pos, from_rule
        return None, None, None

def process_pass(context, exp, pass_):
        import copy
        support_keywords, from_, to = pass_
        bindings = {}
        collect_bindings(from_, bindings, support_keywords, exp, from_, None)
        ret = copy.deepcopy(to)
        use_bindings(to, bindings, support_keywords, ret)
        return context, ret

def process_progn(context, exp):
        for e in exp:
                context, sublist_exp = expand(context, e)
        return context, sublist_exp

def expand(context, exp):
        if exp[0] == TokenType.SPACE:
                pass
        elif exp[0] == TokenType.LIST and exp[2][0] == TokenType.SYMBOL:
                if exp[2][1] == 'set!':
                        context, exp = process_set_ex(context, exp[4:])
                elif exp[2][1] == 'set^':
                        context, exp[6] = process_set_hyper(context, exp[4:])
                elif exp[2][1] == '$+':
                        context, exp = process_macro_add(context, exp[4:])
                elif exp[2][1] == '$-':
                        context, exp = process_macro_sub(context, exp[4:])
                elif exp[2][1] == '$*':
                        context, exp = process_macro_mul(context, exp[4:])
                elif exp[2][1] == '$/':
                        context, exp = process_macro_div(context, exp[4:])
                elif exp[2][1] == '$if':
                        context, exp = process_macro_if(context, exp[4:])
                elif exp[2][1] == '$=':
                        context, exp = process_macro_eq(context, exp[4:])
                elif exp[2][1] == '$symbol-eq':
                        context, exp = process_macro_symbol_eq(context, exp[4:])
                elif exp[2][1] == 'define-syntax!':
                        context, exp = process_define_pass(context, exp[4:])
                elif exp[2][1] == '$progn':
                        context, exp = process_progn(context, exp[4:])
                elif exp[2][1] in context.aliases.keys():
                        exp[2] = context.aliases[exp[2][1]]
                elif exp[2][1] in context.passes.keys():
                        context, exp = process_pass(context, exp, context.passes[exp[2][1]])
                        context, exp = expand(context, exp)
                else:
                        pass
        elif exp[0] == TokenType.SYMBOL and exp[1] in context.aliases.keys():
                exp = context.aliases[exp[1]]
        return context, exp

def expand_all(context, tokens, expanded_tokens):
        for exp in tokens:
                if exp[0] == TokenType.SPACE:
                        continue

                context, subexp_expanded_tokens = expand(context, exp)
                if subexp_expanded_tokens != None:
                        expanded_tokens.append(subexp_expanded_tokens)

        return  expanded_tokens

class CompilerContext:
        def __init__(self):
                self.asm = ''
                self.lambda_counter = 0

def construct_asm(tokens):
        used_list = []
        dynamic_registers = {}
        ret = ''
        for opcode in tokens:
                if opcode[0] == TokenType.SPACE:
                        continue
                if opcode[2][1] == 'let':
                        for reg in opcode[6:]:
                                if reg[0] == TokenType.SPACE:
                                        continue
                                if reg[1] in used_list:
                                        continue
                                used_list.append(reg[1])
                                dynamic_registers[opcode[4][1]] = reg[1]
                                break
                else:
                        ret += '        ' + opcode[2][1] + ' '
                        for i, operand in enumerate(opcode[4:]):
                                if operand[0] == TokenType.SPACE:
                                        continue

                                if operand[0] == TokenType.LIST:
                                        if operand[2][1] in dynamic_registers.keys():
                                                tmp = '[' + dynamic_registers[operand[2][1]] + ']'
                                        else:
                                                tmp = '[' + operand[2][1] + ']'
                                elif operand[1] == 'byte':
                                        ret += 'byte'
                                        continue
                                elif operand[1] == 'word':
                                        ret += 'word'
                                        continue
                                elif operand[1] == 'dword':
                                        ret += 'dword'
                                        continue
                                elif operand[1] in dynamic_registers.keys():
                                        tmp = dynamic_registers[operand[1]]
                                else:
                                        tmp = operand[1]
                                if i == len(opcode[4:]) - 1:
                                        ret += tmp + '\n'
                                else:
                                        ret += tmp + ', '

        return ret

def compile_set_hyper(context, tokens):
        context.asm += fasthash(tokens[0][1]) + ':\n'
        if tokens[2][0] == TokenType.NUMBER:
                context.asm += '        db ' + tokens[2][1] + '\n'
        elif tokens[2][0] == TokenType.STRING:
                context.asm += '        db "' + tokens[2][1] + '"\n'
        else:
                context.asm += construct_asm(tokens[2][4:])
        return context

def compile_progn(context: CompilerContext, tokens):
        for e in tokens:
                if e[0] == TokenType.SPACE:
                        continue
                context.asm += construct_asm(e[3:]) + '\n'
        return context

def compile_to_hyper(context: CompilerContext, tokens):
        context.asm += "times " + tokens[1] + "-($-$$) db 0\n"
        return context

def compile(context, exp):
        if exp[0] == TokenType.LIST and exp[2][0] == TokenType.SYMBOL:
                if exp[2][1] == 'set^':
                        context = compile_set_hyper(context, exp[4:])
                elif exp[2][1] == 'progn':
                        context = compile_progn(context, exp[4:])
                elif exp[2][1] == 'to^':
                        context = compile_to_hyper(context, exp[4])
                else:
                        context.asm += '\n'
                        for i, operand in enumerate(exp[4:]):
                                if operand[0] == TokenType.SPACE:
                                        continue
                                if operand[0] == TokenType.NUMBER:
                                        context.asm += '        mov eax, ' + operand[1] + '\n'
                                        context.asm += '        push eax, \n'
                                elif operand[0] == TokenType.LIST:
                                        pass
                                else:
                                        context.asm += '        push ' + operand[1] + '\n'
                        context.asm += '        call ' + fasthash(exp[2][1])
        elif exp[0] == TokenType.LIST and exp[2][0] == TokenType.LIST and exp[2][2][0] == TokenType.SYMBOL and exp[2][2][1] == '#':
                d = {}
                for i, e in enumerate(exp[2][4][2:]):
                        if e[0] != TokenType.SPACE:
                                d[e[1]] = exp[4 + i]

                replace_var(exp[2][6], d)
                return compile(context, exp[2][6])
        elif exp[0] == TokenType.SYMBOL and exp[1] in context.aliases.keys():
                exp = context.aliases[exp[1]]
        return context

def compile_all(context, tokens):
        for exp in tokens:
                context = compile(context, exp)

        return context.asm

def replace_var(nested_list, replacements):
        if nested_list[0] == TokenType.LIST:
                for token in nested_list[2:]:
                        if token[0] == TokenType.SPACE:
                                pass
                        else:
                                replace_var(token, replacements)
        elif nested_list[0] == TokenType.SYMBOL and nested_list[1] in replacements.keys():
                nested_list[:] = replacements[nested_list[1]]

with open(sys.argv[1] + '.sl','r') as file:
        content = file.read()
        parser_context = parser(LaxerContext(content))
        expanded_tokens = expand_all(ExpanderContext(), parser_context.tokens, [])
        result = compile_all(CompilerContext(), expanded_tokens)
        import os
        with open(sys.argv[1] + '.asm', 'w') as asmfile:
                asmfile.write(result)
        os.system('nasm ' + sys.argv[1] + '.asm -o ' + sys.argv[1] + '.bin')
