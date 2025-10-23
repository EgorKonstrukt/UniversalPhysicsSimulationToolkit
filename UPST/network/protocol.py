import asyncio,json,time,hashlib,base64,zlib
ENCODING="utf-8"
PROTO_VERSION="1.0"
def now_ms():
    return int(time.time()*1000)
def _pack(msg,compress=False):
    s=json.dumps(msg,separators=(",",":"),ensure_ascii=False)
    if not compress:
        return (s+"\n").encode(ENCODING)
    b=zlib.compress(s.encode(ENCODING),9)
    h=base64.b64encode(b).decode("ascii")
    return (json.dumps({"$c":True,"d":h},separators=(",",":"))+"\n").encode(ENCODING)
def _unpack_line(line):
    s=line.decode(ENCODING)
    if not s:
        return None
    try:
        obj=json.loads(s)
        if isinstance(obj,dict) and obj.get("$c") is True:
            b=base64.b64decode(obj["d"])
            return json.loads(zlib.decompress(b).decode(ENCODING))
        return obj
    except:
        return None
async def read_message(reader:asyncio.StreamReader,timeout=None):
    try:
        line=await asyncio.wait_for(reader.readline(),timeout=timeout)
        if not line:
            return None
        return _unpack_line(line)
    except:
        return None
async def write_message(writer:asyncio.StreamWriter,msg,compress=False):
    try:
        writer.write(_pack(msg,compress=compress))
        await writer.drain()
    except:
        pass
def sig(s):
    return hashlib.sha256(str(s).encode(ENCODING)).hexdigest()[:16]
