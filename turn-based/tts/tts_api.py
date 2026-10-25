"""Sends Lua to a running TTS and prints the reply (External Editor API).

TTS listens on 39999 and sends replies to 39998, so we start listening on 39998 first
and send the command after that. Usage: python3 tts_api.py 'return #getObjects()'
"""
import json, socket, sys, threading

def run(script, timeout=8.0):
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 39998)); srv.listen(5); srv.settimeout(timeout)
    msgs = []
    def listen():
        try:
            while True:
                c, _ = srv.accept(); buf = b""
                while chunk := c.recv(65536): buf += chunk
                c.close()
                # TTS sends every message as indented (multi-line) JSON; splitting it line by line
                # broke it, so we decode the whole buffer in order.
                text = buf.decode("utf-8", "replace").strip()
                dec, i = json.JSONDecoder(), 0
                while i < len(text):
                    obj, i = dec.raw_decode(text, i)
                    msgs.append(obj)
                    while i < len(text) and text[i].isspace(): i += 1
                # A Global script never sends the "return" message (5), only print (2) and error (3);
                # a short silence after the first message means it is done.
                srv.settimeout(1.5)
        except socket.timeout:
            pass
    t = threading.Thread(target=listen); t.start()
    s = socket.create_connection(("127.0.0.1", 39999), timeout=3)
    # Get the result back with print: the return value doesn't come back through the API.
    wrapped = "local __r = (function() " + script + " end)() if __r ~= nil then print(tostring(__r)) end"
    s.sendall(json.dumps({"messageID": 3, "guid": "-1", "script": wrapped}).encode()); s.close()
    t.join(); srv.close()
    return msgs

if __name__ == "__main__":
    for m in run(sys.argv[1]):
        print(json.dumps(m, ensure_ascii=False)[:4000])
