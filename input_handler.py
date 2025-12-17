import threading
import sys
import json
from typing import TYPE_CHECKING, TextIO
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
        threading.Thread(target=self.read_input, daemon=True).start()

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

class LSPInputHandler(InputHandler):
    def __init__(self, input: TextIO, output: TextIO, controller: "Controller"):
        super().__init__(input, output, controller)
        self.file = None

    def read_message(self):
        headers = {}
        while True:
            line = self.input.readline().strip()
            if not line:
                break
            key, value = line.split(": ")
            headers[key] = value

        content_length = int(headers.get("Content-Length", 0))
        if content_length:
            body = self.input.read(content_length)
            self.queue.put(json.loads(body))

    def send_message(self, msg):
        msg['jsonrpc'] = '2.0'
        body = json.dumps(msg)
        self.output.write(
            f"Content-Length: {len(body)}\r\n\r\n{body}"
        )
        sys.stdout.flush()

    def read_input(self):
        while True:
            self.read_message()

    def process(self, msg) -> bool:
        method = msg.get('method')
        # print(msg, file=sys.stderr)
        if method is None:
            return False

        if method == "initialize":
            self.send_message({
                "id": msg["id"],
                "result": {
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
                                    'operator'
                                    # 'namespace','type','class','enum','interface','struct','typeParameter','parameter','variable','property','enumMember','event','function','method','macro','keyword','modifier','comment','string','number','regexp','operator','decorator'
                                ],
                                "tokenModifiers": [
                                    'defaultLibrary',
                                    'static'
                                ]
                            },
                            "full": True,
                            "range": False
                        }
                    }
                }
            })
            return False

        if method == "shutdown":
            self.send_message({
                "id": msg["id"],
                "result": None
            })
            return False

        if method == "exit":
            sys.exit(0)

        if method == 'textDocument/didOpen':
            self.file = msg['params']['textDocument']['uri']
            self.controller.model.code = msg['params']['textDocument']['text'].split('\n')
            return True

        if method == 'textDocument/didChange':
            self.file = msg['params']['textDocument']['uri']
            for change in msg['params']['contentChanges']:
                self.controller.model.code = change['text'].split('\n')
                print(self.controller.model.code)
            return True

        if method == 'textDocument/semanticTokens/full':
            lookup = 'comment preprocess number identifier function operator'.split()
            result = []
            # result = [0,0,5,1,0]
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

            self.send_message({
                'id': msg['id'],
                'result': {'data': result}
            })

            return False

        print(msg, file=sys.stderr)

        return False

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
