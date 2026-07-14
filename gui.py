#!/usr/bin/env python3
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tkinter as tk
from tkinter import scrolledtext, font, ttk
from aurora import run_source

# Catppuccin Mocha palette
BG='#1e1e2e'; BG2='#313244'; BG3='#181825'
FG='#cdd6f4'; FG2='#6c7086'
PURPLE='#cba6f7'; BLUE='#89b4fa'; CYAN='#89dceb'
GREEN='#a6e3a1'; RED='#f38ba8'; YELLOW='#f9e2af'; PEACH='#fab387'

def load_examples():
    ex = {}
    edir = os.path.join(os.path.dirname(__file__), 'examples')
    # fixed display order for the combo-box
    order = ['hello','datatypes','control','functions','classes','errors','fizzbuzz',
             'collections','strings','loops','nested','mutability']
    labels = ['1 Hello World','2 Data Types','3 Control Flow',
              '4 Functions & Recursion','5 Classes','6 Error Handling','7 FizzBuzz',
              '8 Lists & Maps','9 String Methods','10 Loops & Ranges',
              '11 Nested Data','12 Mutability']
    for label, fname in zip(labels, order):
        path = os.path.join(edir, fname+'.aur')
        if os.path.exists(path):
            with open(path) as f:
                ex[label] = f.read()
    return ex

EXAMPLES = load_examples()

# Aurora keywords for syntax highlighting
KW_RE = re.compile(
    r'\b(Int|Float|String|Bool|List|Map|auto|mut|func|class|if|else|while|for|in|'
    r'return|break|import|print|true|false|null|and|or|not)\b'
)

class AuroraIDE(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Aurora Language IDE  v2.0')
        self.geometry('1280x760')
        self.configure(bg=BG)
        self._make_fonts()
        self._layout()
        keys = list(EXAMPLES.keys())
        if keys:
            self._load(keys[0])

    def _make_fonts(self):
        self.cf = font.Font(family='Courier New', size=12)
        self.of = font.Font(family='Courier New', size=11)
        self.lf = font.Font(family='Arial', size=10, weight='bold')
        self.tf = font.Font(family='Arial', size=15, weight='bold')

    def _layout(self):
        top = tk.Frame(self, bg=BG3, pady=7)
        top.pack(fill=tk.X, side=tk.TOP)
        tk.Label(top, text='\U0001f305 Aurora IDE', font=self.tf,
                 fg=PURPLE, bg=BG3).pack(side=tk.LEFT, padx=14)
        tk.Label(top, text='Examples:', fg=FG, bg=BG3,
                 font=self.lf).pack(side=tk.LEFT, padx=(20,4))
        self.ex_var = tk.StringVar()
        cb = ttk.Combobox(top, textvariable=self.ex_var,
                           values=list(EXAMPLES.keys()), width=30,
                           state='readonly', font=self.lf)
        cb.pack(side=tk.LEFT)
        cb.bind('<<ComboboxSelected>>', lambda e: self._load(self.ex_var.get()))
        tk.Button(top, text='\u25b6  Run  (F5)', command=self.run_code,
                  bg=GREEN, fg=BG, font=self.lf, padx=14, pady=2,
                  relief=tk.FLAT, cursor='hand2').pack(side=tk.RIGHT, padx=10)
        tk.Button(top, text='\u2716 Clear', command=self.clear_out,
                  bg=BG2, fg=FG, font=self.lf, padx=10, pady=2,
                  relief=tk.FLAT, cursor='hand2').pack(side=tk.RIGHT, padx=4)
        pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=BG,
                               sashwidth=6)
        pane.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        lf = tk.Frame(pane, bg=BG)
        pane.add(lf, width=660)
        tk.Label(lf, text=' Code Editor', fg=CYAN, bg=BG,
                 font=self.lf).pack(anchor=tk.W)
        self.editor = scrolledtext.ScrolledText(
            lf, font=self.cf, bg=BG2, fg=FG, insertbackground=PURPLE,
            selectbackground='#585b70', undo=True, wrap=tk.NONE,
            relief=tk.FLAT, padx=8, pady=6, tabs='1c'
        )
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.editor.bind('<Tab>', self._tab)
        self.editor.bind('<KeyRelease>', self._hi)
        self.editor.bind('<F5>', lambda e: self.run_code())
        self._tags()
        rf = tk.Frame(pane, bg=BG)
        pane.add(rf, width=560)
        tk.Label(rf, text=' Output', fg=CYAN, bg=BG,
                 font=self.lf).pack(anchor=tk.W)
        self.output = scrolledtext.ScrolledText(
            rf, font=self.of, bg=BG3, fg=GREEN,
            state=tk.DISABLED, wrap=tk.WORD, relief=tk.FLAT, padx=8, pady=6
        )
        self.output.pack(fill=tk.BOTH, expand=True)
        self.output.tag_config('err',  foreground=RED)
        self.output.tag_config('info', foreground=BLUE)
        self.status = tk.StringVar(value='Ready')
        tk.Label(self, textvariable=self.status, fg=FG2, bg=BG3,
                 anchor=tk.W, padx=8, font=('Arial',9)).pack(
                     fill=tk.X, side=tk.BOTTOM)

    def _tags(self):
        self.editor.tag_config('kw',  foreground=PURPLE)
        self.editor.tag_config('str_t', foreground=GREEN)
        self.editor.tag_config('num',  foreground=PEACH)
        self.editor.tag_config('cmt',  foreground=FG2,
            font=font.Font(family='Courier New', size=12, slant='italic'))

    def _idx(self, pos, text):
        # Convert character offset to tkinter "line.col" index
        line = text[:pos].count('\n') + 1
        col  = pos - text[:pos].rfind('\n') - 1
        return f'{line}.{col}'

    def _hi(self, event=None):
        ed = self.editor
        for tag in ('kw','str_t','num','cmt'):
            ed.tag_remove(tag, '1.0', tk.END)
        text = ed.get('1.0', tk.END)
        for m in re.finditer(r'//[^\n]*', text):
            ed.tag_add('cmt', self._idx(m.start(),text), self._idx(m.end(),text))
        for m in re.finditer(r'"[^"\\]*(?:\\.[^"\\]*)*"', text):
            ed.tag_add('str_t', self._idx(m.start(),text), self._idx(m.end(),text))
        for m in re.finditer(r'\b\d+(\.\d+)?\b', text):
            ed.tag_add('num', self._idx(m.start(),text), self._idx(m.end(),text))
        for m in KW_RE.finditer(text):
            ed.tag_add('kw', self._idx(m.start(),text), self._idx(m.end(),text))

    def _tab(self, e):
        self.editor.insert(tk.INSERT, '    ')
        return 'break'

    def _load(self, key):
        self.editor.delete('1.0', tk.END)
        self.editor.insert('1.0', EXAMPLES.get(key, ''))
        self._hi()
        self.clear_out()
        self.status.set(f'Loaded: {key}')

    def run_code(self):
        source = self.editor.get('1.0', tk.END)
        self.clear_out()
        lines = []
        # Capture output via callback since run_source prints to a function
        run_source(source, output_fn=lambda s: lines.append(s))
        self.output.config(state=tk.NORMAL)
        for line in lines:
            tag = 'err' if 'Error' in line else None
            self.output.insert(tk.END, line+'\n', tag)
        if not lines:
            self.output.insert(tk.END, '(no output)\n', 'info')
        self.output.config(state=tk.DISABLED)
        self.status.set(f'Done — {len(lines)} line(s) of output')

    def clear_out(self):
        self.output.config(state=tk.NORMAL)
        self.output.delete('1.0', tk.END)
        self.output.config(state=tk.DISABLED)

if __name__ == '__main__':
    AuroraIDE().mainloop()