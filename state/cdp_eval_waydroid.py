#!/usr/bin/env python3
import asyncio, json, urllib.request, sys
import websockets

PORT=int(sys.argv[1]) if len(sys.argv)>1 else 9223
expr=sys.argv[2] if len(sys.argv)>2 else 'document.body.innerText'

def get_ws():
    pages=json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/list'))
    page=next((p for p in pages if 'chromastudio.ai' in p.get('url','') and 'visible":true' in p.get('description','')), None)
    if not page:
        page=next(p for p in pages if 'chromastudio.ai' in p.get('url',''))
    return page['webSocketDebuggerUrl']

async def main():
    wsurl=get_ws()
    async with websockets.connect(wsurl, max_size=10_000_000) as ws:
        msg_id=1
        await ws.send(json.dumps({'id':msg_id,'method':'Runtime.enable'})); msg_id+=1
        # drain until response to Runtime.enable
        while True:
            msg=json.loads(await ws.recv())
            if msg.get('id')==1: break
        await ws.send(json.dumps({'id':msg_id,'method':'Runtime.evaluate','params':{
            'expression': expr,
            'awaitPromise': True,
            'returnByValue': True,
            'userGesture': True,
        }}))
        want=msg_id
        while True:
            msg=json.loads(await ws.recv())
            if msg.get('id')==want:
                print(json.dumps(msg, indent=2)[:20000])
                break
asyncio.run(main())
