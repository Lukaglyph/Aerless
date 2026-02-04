import enum, re, sys, random, os, time

try:
    import msvcrt
except ImportError:
    msvcrt = None

class LoopSignal(Exception): pass
class ReturnSignal(Exception):
    def __init__(self, value): self.value = value

# --- 1. TokenType & Token (変更なし) ---
class TokenType(enum.Enum):
    IS = "is"; DO = "do"; IF = "if"; NO = "no"; OK = "ok"; NG = "ng"; GO = "go"
    DURING = "during"; SPELL = "spell"; RETURN = "return"; ARTS = "arts"; WAIT = "wait"
    PLUS = "+"; MINUS = "-"; STAR = "*"; SLASH = "/"; MOD = "%"
    EQ_EQ = "=="; GT = ">"; LT = "<"; L_BRACE = "{"; R_BRACE = "}"
    L_PAREN = "("; R_PAREN = ")"; L_BRACKET = "["; R_BRACKET = "]"
    COMMA = ","; EQUALS = "="; PIPE = "|>"; ID = "ID"; NUMBER = "NUMBER"
    STRING = "STRING"; EOF = "EOF"

class Token:
    def __init__(self, type, value): self.type = type; self.value = value

# --- 2. Lexer (変更なし) ---
class Lexer:
    def __init__(self, text):
        self.text = text; self.pos = 0
    def tokenize(self):
        tokens = []
        rules = [
            (TokenType.STRING, r'"[^"]*"'), (TokenType.NUMBER, r'\d+'), (TokenType.PIPE, r'\|>'), (TokenType.EQ_EQ, r'=='),
            *[(t, r'\b' + t.value + r'\b') for t in [TokenType.IS, TokenType.DO, TokenType.IF, TokenType.NO, TokenType.OK, TokenType.NG, TokenType.GO, TokenType.DURING, TokenType.SPELL, TokenType.RETURN, TokenType.ARTS, TokenType.WAIT]],
            (TokenType.PLUS, r'\+'), (TokenType.MINUS, r'-'), (TokenType.STAR, r'\*'), (TokenType.SLASH, r'/'), (TokenType.MOD, r'%'),
            (TokenType.GT, r'>'), (TokenType.LT, r'<'), (TokenType.EQUALS, r'='), 
            (TokenType.L_BRACE, r'\{'), (TokenType.R_BRACE, r'\}'),
            (TokenType.L_PAREN, r'\('), (TokenType.R_PAREN, r'\)'), 
            (TokenType.L_BRACKET, r'\['), (TokenType.R_BRACKET, r'\]'), (TokenType.COMMA, r','),
            (TokenType.ID, r'[a-z_][a-z0-9_]*'),
        ]
        while self.pos < len(self.text):
            if self.text[self.pos].isspace(): self.pos += 1; continue
            if self.text[self.pos] == '#':
                self.pos = self.text.find('\n', self.pos) if '\n' in self.text[self.pos:] else len(self.text); continue
            matched = False
            for t, p in rules:
                m = re.match(p, self.text[self.pos:])
                if m:
                    val = m.group(0); self.pos += len(val)
                    if t == TokenType.STRING: val = val[1:-1]
                    elif t == TokenType.NUMBER: val = int(val)
                    tokens.append(Token(t, val)); matched = True; break
            if not matched: raise SyntaxError(f"不明な文字: {self.text[self.pos]}")
        tokens.append(Token(TokenType.EOF, None)); return tokens

# --- 3. Parser (変更なし) ---
class Parser:
    def __init__(self, tokens): self.tokens = tokens; self.pos = 0
    def eat(self, t):
        if self.tokens[self.pos].type == t: self.pos += 1; return self.tokens[self.pos-1]
        raise SyntaxError(f"Expected {t} but got {self.tokens[self.pos].type}")

    def parse(self):
        stmts = []
        while self.tokens[self.pos].type != TokenType.EOF: stmts.append(self.parse_stmt())
        return stmts

    def parse_stmt(self):
        t = self.tokens[self.pos]
        if t.type == TokenType.ARTS: self.eat(TokenType.ARTS); return ("ARTS", self.parse_expr())
        if t.type == TokenType.WAIT:
            self.eat(TokenType.WAIT); self.eat(TokenType.L_PAREN); ms = self.parse_expr(); self.eat(TokenType.R_PAREN); return ("CALL", "wait", [ms])
        if t.type == TokenType.IS:
            self.eat(TokenType.IS); n = self.eat(TokenType.ID).value; self.eat(TokenType.EQUALS); return ("IS", n, self.parse_expr())
        if t.type == TokenType.DO: self.eat(TokenType.DO); return ("DO", self.parse_expr())
        if t.type == TokenType.DURING:
            self.eat(TokenType.DURING); cond = self.parse_expr(); self.eat(TokenType.L_BRACE); body = self.parse_block(); self.eat(TokenType.R_BRACE); return ("DURING", cond, body)
        if t.type == TokenType.IF:
            self.eat(TokenType.IF); cond = self.parse_expr(); self.eat(TokenType.L_BRACE); tb = self.parse_block(); self.eat(TokenType.R_BRACE)
            fb = None
            if self.tokens[self.pos].type == TokenType.NO: self.eat(TokenType.NO); self.eat(TokenType.L_BRACE); fb = self.parse_block(); self.eat(TokenType.R_BRACE)
            return ("IF", cond, tb, fb)
        if t.type == TokenType.SPELL:
            self.eat(TokenType.SPELL); name = self.eat(TokenType.ID).value; self.eat(TokenType.L_PAREN); params = []
            if self.tokens[self.pos].type != TokenType.R_PAREN:
                params.append(self.eat(TokenType.ID).value)
                while self.tokens[self.pos].type == TokenType.COMMA: self.eat(TokenType.COMMA); params.append(self.eat(TokenType.ID).value)
            self.eat(TokenType.R_PAREN); self.eat(TokenType.L_BRACE); body = self.parse_block(); self.eat(TokenType.R_BRACE); return ("SPELL_DEF", name, params, body)
        if t.type == TokenType.RETURN: self.eat(TokenType.RETURN); return ("RETURN", self.parse_expr())
        if t.type == TokenType.ID and self.pos+1 < len(self.tokens) and self.tokens[self.pos+1].type == TokenType.EQUALS:
            n = self.eat(TokenType.ID).value; self.eat(TokenType.EQUALS); return ("ASSIGN", n, self.parse_expr())
        return ("EXPR", self.parse_expr())

    def parse_block(self):
        b = []
        while self.tokens[self.pos].type not in (TokenType.R_BRACE, TokenType.EOF): b.append(self.parse_stmt())
        return b

    def parse_expr(self):
        l = self.parse_math()
        while self.tokens[self.pos].type == TokenType.PIPE: self.eat(TokenType.PIPE); l = ("PIPE", l, self.parse_math())
        return l

    def parse_math(self):
        l = self.parse_mul()
        while self.tokens[self.pos].type in (TokenType.PLUS, TokenType.MINUS, TokenType.GT, TokenType.LT, TokenType.EQ_EQ):
            op = self.tokens[self.pos].type; self.pos += 1; l = (op.name, l, self.parse_mul())
        return l

    def parse_mul(self):
        l = self.parse_term()
        while self.tokens[self.pos].type in (TokenType.STAR, TokenType.SLASH, TokenType.MOD):
            op = self.tokens[self.pos].type; self.pos += 1; l = (op.name, l, self.parse_term())
        return l

    def parse_term(self):
        t = self.tokens[self.pos]
        if t.type == TokenType.L_BRACKET:
            self.eat(TokenType.L_BRACKET); els = []
            if self.tokens[self.pos].type != TokenType.R_BRACKET:
                els.append(self.parse_expr())
                while self.tokens[self.pos].type == TokenType.COMMA: self.eat(TokenType.COMMA); els.append(self.parse_expr())
            self.eat(TokenType.R_BRACKET); return ("LIST", els)
        if t.type == TokenType.MINUS: self.eat(TokenType.MINUS); return ("MINUS", ("NUM", 0), self.parse_term())
        if t.type == TokenType.NUMBER: return ("NUM", self.eat(TokenType.NUMBER).value)
        if t.type == TokenType.STRING:
            v = self.eat(TokenType.STRING).value; p = re.split(r'\{(.*?)\}', v); return ("STR_I", p) if len(p) > 1 else ("STR", v)
        if t.type == TokenType.ID:
            n = self.eat(TokenType.ID).value
            if self.tokens[self.pos].type == TokenType.L_PAREN:
                self.eat(TokenType.L_PAREN); args = []
                if self.tokens[self.pos].type != TokenType.R_PAREN:
                    args.append(self.parse_expr())
                    while self.tokens[self.pos].type == TokenType.COMMA: self.eat(TokenType.COMMA); args.append(self.parse_expr())
                self.eat(TokenType.R_PAREN); return ("CALL", n, args)
            return ("VAR", n)
        if t.type in (TokenType.OK, TokenType.NG): return ("BOOL", self.eat(t.type).type == TokenType.OK)
        if t.type == TokenType.L_PAREN: self.eat(TokenType.L_PAREN); e = self.parse_expr(); self.eat(TokenType.R_PAREN); return e
        raise SyntaxError(f"Unexpected token: {t.value}")

# --- 4. Interpreter: 包み紙を剥くように修正 ---
class Interpreter:
    def __init__(self):
        self.env = {}; self.spells = {}; self.pressed_key = None
        self.builtins = {
            "rand": lambda a, b: random.randint(a, b), "cls": lambda: os.system('cls' if os.name == 'nt' else 'clear'),
            "wait": lambda ms: time.sleep(ms / 1000.0), "rep": lambda s, n: str(s) * max(0, int(n)),
            "key": lambda k: self._check_key(k), "at": lambda lst, i: lst[i] if 0 <= i < len(lst) else None,
            "push": lambda lst, v: lst.append(v) or lst, "size": lambda lst: len(lst),
            "set": lambda lst, i, v: lst.__setitem__(i, v) or lst,
            "get_num": lambda p: int(input(p)), "get_op": lambda p: input(p)
        }

    def _check_key(self, k):
        if msvcrt and msvcrt.kbhit():
            char = msvcrt.getch()
            if char in (b'\x00', b'\xe0'): msvcrt.getch(); return False
            self.pressed_key = char.decode('utf-8', errors='ignore').lower()
        else: self.pressed_key = None
        return self.pressed_key == k

    def run(self, nodes):
        val = None
        for n in nodes:
            try:
                val = self.execute(n)
            except ReturnSignal as s:
                return s.value
        return val

    def execute(self, n):
        tag = n[0]
        # EXPR の場合は中身を剥いて評価する
        if tag == "EXPR":
            return self.evaluate(n[1])
        
        if tag == "CALL":
            return self.evaluate(n)
        
        if tag == "IS" or tag == "ASSIGN":
            v = self.evaluate(n[2])
            self.env[n[1]] = v
            return v
        
        if tag == "DO":
            v = self.evaluate(n[1])
            print(v)
            return None
            
        if tag == "IF":
            cond = self.evaluate(n[1])
            res = None
            if cond:
                for s in n[2]: res = self.execute(s)
            elif n[3]:
                for s in n[3]: res = self.execute(s)
            return res
            
        if tag == "DURING":
            while self.evaluate(n[1]):
                try:
                    for s in n[2]: self.execute(s)
                except LoopSignal: continue
            return None
            
        if tag == "SPELL_DEF":
            self.spells[n[1]] = (n[2], n[3])
            return f"Spell '{n[1]}' ready."
            
        if tag == "RETURN": 
            raise ReturnSignal(self.evaluate(n[1]))
            
        if tag == "ARTS":
            fname = self.evaluate(n[1])
            if os.path.exists(fname):
                with open(fname, 'r', encoding='utf-8') as f:
                    return self.run(Parser(Lexer(f.read()).tokenize()).parse())
        return None

    def evaluate(self, n):
        tag = n[0]
        # ここで直接 EXPR が来ても剥けるようにガード
        if tag == "EXPR": return self.evaluate(n[1])
        
        if tag == "NUM" or tag == "STR" or tag == "BOOL": return n[1]
        if tag == "VAR": return self.env.get(n[1], 0)
        if tag == "LIST": return [self.evaluate(e) for e in n[1]]
        if tag == "STR_I": return "".join([p if i%2==0 else str(self.env.get(p, p)) for i, p in enumerate(n[1])])
        if tag in ("PLUS", "MINUS", "STAR", "SLASH", "MOD", "GT", "LT", "EQ_EQ"):
            l, r = self.evaluate(n[1]), self.evaluate(n[2])
            if tag == "PLUS": return l + r
            if tag == "MINUS": return l - r
            if tag == "STAR": return l * r
            if tag == "SLASH": return l // r if r != 0 else 0
            if tag == "MOD": return l % r if r != 0 else 0
            if tag == "GT": return l > r
            if tag == "LT": return l < r
            if tag == "EQ_EQ": return l == r
        if tag == "CALL":
            name, args = n[1], [self.evaluate(a) for a in n[2]]
            if name in self.builtins: return self.builtins[name](*args)
            if name in self.spells:
                params, body, old_env = self.spells[name][0], self.spells[name][1], self.env.copy()
                for p, v in zip(params, args): self.env[p] = v
                res = None
                try:
                    for s in body: res = self.execute(s)
                except ReturnSignal as r: res = r.value
                self.env = old_env; return res
        if tag == "PIPE":
            val = self.evaluate(n[1])
            return self.evaluate(("CALL", n[2][1], [("VAL", val)] + n[2][2]))
        if tag == "VAL": return n[1]
        return None

# --- Main Dialog ---
def start_dialog():
    itp = Interpreter()
    print("Aerless Dialog Mode (Ver 2.7 - Truth)")
    print("ctrl＋Cで終了")
    while True:
        try:
            line = input(">> ").strip()
            if not line: continue
            if line.lower() in ("quit", "exit"): break
            
            tokens = Lexer(line).tokenize()
            nodes = Parser(tokens).parse()
            res = itp.run(nodes)
            
            if res is not None:
                print(f"=> {res}")
        except Exception as e:
            print(f"'エラー: {e}'")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            Interpreter().run(Parser(Lexer(f.read()).tokenize()).parse())
    else:
        start_dialog()