import threading
import sys
import json
from typing import TYPE_CHECKING, TextIO, Any
from queue import Queue

from graphite.tokenizer import tokenize
from graphite.model import builtins

if TYPE_CHECKING:
    from graphite.__main__ import Controller

class InputHandler:
    def __init__(self, input: TextIO, output: TextIO, controller: "Controller"):
        self.input = input
        self.output = output
        self.controller = controller
        self.queue = Queue()
        self.input_thread = threading.Thread(target=self.read_input, daemon=False).start()

    def read_input(self):
        for line in self.input:
            self.queue.put(line.rstrip())

    def poll(self):
        refresh = False
        while not self.queue.empty():
            if self.process(self.queue.get()):
                refresh = True
        if refresh:
            self.controller.refresh()

    def process(self, msg) -> bool:
        self.controller.model.code.append(msg)
        return True

    def compiled(self):
        pass

class StreamInputHandler(InputHandler):
    def process(self, msg) -> bool:
        self.controller.model.code = msg.split('<nl>')
        return True

def method(func):
    func._isMethod = True
    return func

class LSPInputHandler(InputHandler):
    def __init__(self, input: TextIO, output: TextIO, controller: "Controller"):
        super().__init__(input, output, controller)
        self.file = None

        self.methods = {}
        for name in dir(self):
            method = getattr(self, name)
            if not hasattr(method, "_isMethod"): continue
            self.methods[name.replace('_', '/')] = method

    def read_message(self):
        headers = {}
        while True:
            line = self.input.readline()
            if line == '': return True
            line = line.rstrip()
            if not line:
                break
            key, value = line.split(": ")
            headers[key] = value

        content_length = int(headers.get("Content-Length", 0))
        if content_length:
            body = self.input.read(content_length)
            self.queue.put(json.loads(body))

    def send_message(self, msg):
        body = json.dumps(msg)
        self.output.write(
            f"Content-Length: {len(body)}\r\n\r\n{body}"
        )
        sys.stdout.flush()

    def read_input(self):
        while True:
            if self.read_message(): break

    @method
    def initialize(self, params) -> tuple[bool, Any]:
        return False, {
            "capabilities": {
                "textDocumentSync": {
                    "openClose": True,
                    "change": 1,
                    "save": True
                },
                "semanticTokensProvider": {
                    "legend": {
                        "tokenTypes": [
                            'comment',
                            'modifier',
                            'number',
                            'variable',
                            'function',
                            'operator',
                            'string'
                            # 'namespace','type','class','enum','interface','struct','typeParameter','parameter','variable','property','enumMember','event','function','method','macro','keyword','modifier','comment','string','number','regexp','operator','decorator'
                        ],
                        "tokenModifiers": [
                            'defaultLibrary',
                            'static'
                        ]
                    },
                    "full": True,
                    "range": True
                },
                "executeCommandProvider": {
                    "commands": [
                        "graphite.usercmd",
                    ]
                }
            }
        }

    @method
    def shutdown(self, params) -> tuple[bool, Any]:
        return False, None

    @method
    def exit(self, params) -> tuple[bool, Any]:
        exit(0)

    @method
    def textDocument_didOpen(self, params) -> tuple[bool, Any]:
        self.file = params['textDocument']['uri']
        self.controller.model.code = params['textDocument']['text'].split('\n')
        return True, False

    @method
    def textDocument_didChange(self, params) -> tuple[bool, Any]:
        self.file = params['textDocument']['uri']
        for change in params['contentChanges']:
            self.controller.model.code = change['text'].split('\n')
            print(self.controller.model.code)
        return True, False

    @method
    def textDocument_semanticTokens_full(self, params) -> tuple[bool, Any]:
        lookup = 'comment preprocess number identifier function operator string'.split()
        result = []
        prevLine = 0
        for i, line in enumerate(self.controller.model.code):
            try:
                tokens = tokenize(line)
            except Exception:
                continue

            prevChar = 0
            for token in tokens:
                if token[0] == 'other': continue
                # result += [i - prevLine, token[2] - prevChar, len(token[1]), i, 0] # type: ignore
                mod = 0
                type = lookup.index(token[0]) # type: ignore
                if token[1] in builtins.functions:
                    type = lookup.index('function')
                    # mod = 1

                if token[1] in builtins.variables:
                    mod = 2

                result += [i - prevLine, token[2] - prevChar, len(token[1]), type, mod] # type: ignore
                prevLine = i
                prevChar = token[2]

        return False, {'data': result}

    @method
    def workspace_executeCommand(self, params) -> tuple[bool, Any]:
        cmd = params['command']
        args = params['arguments']
        res = 'Invalid command'
        if cmd == 'graphite.usercmd':
            res = self.controller.runCommand(''.join(args))
        return False, res

    def process(self, msg) -> bool:
        method = msg.get('method')
        print(method, file=sys.stderr)
        if method is None:
            return False

        mtd = self.methods.get(method)
        if mtd is None:
            print('Call to unimplemented method:', msg, file=sys.stderr)
            return False

        refresh, result = mtd(msg.get('params'))

        if result != False:
            response = {
                'jsonrpc': '2.0',
                'id': msg['id'],
            }
            # if result is not None:
            response['result'] = result
            self.send_message(response)
        return refresh

    def compiled(self):
        if self.file is None: return

        diagnostics = []
        model = self.controller.model

        for i, err in enumerate(model.errors):
            if not err: continue
            diagnostics.append({
                'range': {
                    'start': {'line': i, 'character': 0},
                    'end': {'line': i, 'character': len(model.code[i-1]) - 1}
                },
                'severity': 1,
                'message': err,
                'source': 'graphite'
            })

        self.send_message({
            "method": "textDocument/publishDiagnostics",
            "params": {
                "uri": self.file,
                "diagnostics": diagnostics
            }
        })

