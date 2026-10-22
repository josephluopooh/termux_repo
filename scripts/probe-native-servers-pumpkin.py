"""Check Pumpkin world metadata persistence across two clean native launches."""
import gzip
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import tempfile
import time

def exact(client, size):
    data=b''
    while len(data)<size:
        part=client.recv(size-len(data)); assert part, data
        data+=part
    return data

def varint(client):
    value=0
    for shift in range(0,35,7):
        byte=exact(client,1)[0]
        value|=(byte&127)<<shift
        if byte<128:return value
    raise AssertionError('Invalid status varint')

def boot(work, attempt):
    with (work/f'boot-{attempt}.log').open('w+') as log:
        p=subprocess.Popen(['pumpkin'],cwd=work,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True)
        try:
            deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                assert p.poll() is None, ('Pumpkin exited',p.returncode)
                try: client=socket.create_connection(('127.0.0.1',19111),timeout=1);break
                except ConnectionRefusedError: time.sleep(.25)
            else: raise AssertionError('Pumpkin status listener timed out')
            with client:
                client.settimeout(15)
                payload=b'\x00\xff\xff\xff\xff\x0f\x09localhost'+struct.pack('>H',19111)+b'\x01'
                client.sendall(bytes([len(payload)])+payload+b'\x01\x00')
                length=varint(client);assert length>2 and varint(client)==0
                size=varint(client);assert 0<size<65536
                status=json.loads(exact(client,size))
                assert status['version']['protocol']==777,status
            p.stdin.write('stop\n');p.stdin.flush()
            assert p.wait(60)==0
        finally:
            if p.poll() is None:
                p.terminate()
                try:p.wait(10)
                except subprocess.TimeoutExpired:p.kill();p.wait()
            log.seek(0);text=log.read();print(text[-16000:],flush=True)
        if attempt==1:assert 'No level.dat' not in text, 'Second launch did not load saved metadata'

def saved_seed(work):
    level=work/'world/level.dat'
    assert level.is_file() and level.stat().st_size>40,'No saved level.dat'
    raw=gzip.decompress(level.read_bytes());assert raw[0]==10 and len(raw)>40
    settings=work/'world/data/minecraft/world_gen_settings.dat'
    assert settings.is_file(),'No saved world generation settings'
    raw=gzip.decompress(settings.read_bytes())
    marker=b'\x04\x00\x04seed'
    assert raw.count(marker)==1,'Expected one NBT TAG_Long seed'
    offset=raw.index(marker)+len(marker)
    return struct.unpack_from('>q',raw,offset)[0]

with tempfile.TemporaryDirectory(prefix='pumpkin-persistence-') as temp:
    work=Path(temp)
    for key,folder in [('HOME','home'),('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config')]:
        os.environ[key]=str(work/folder);(work/folder).mkdir()
    subprocess.run(['pumpkin-server','install'],check=True,timeout=300)
    (work/'pumpkin.toml').write_text('allow_nether = false\nallow_end = false\n[networking.java]\naddress = "127.0.0.1:19111"\nview_distance = 2\nsimulation_distance = 2\n[networking.bedrock]\nenabled = false\n[telemetry]\nenabled = false\n')
    boot(work,0)
    seed=saved_seed(work)
    boot(work,1)
    assert saved_seed(work)==seed,'World seed changed after reload'
    print('PASS: Pumpkin native status, clean shutdown, level.dat and world seed persistence across restart',flush=True)
