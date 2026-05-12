#!/usr/bin/env python3
import asyncio, json, urllib.request, websockets, time
PORT=9223
PROMPT='QA Waydroid Bria 3.2 mobile generation tiny blue robot holding a checkmark'

def page_ws():
    pages=json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/list'))
    page=next((p for p in pages if 'chromastudio.ai' in p.get('url','') and 'visible":true' in p.get('description','')), None)
    if not page: page=next(p for p in pages if 'chromastudio.ai' in p.get('url',''))
    return page['webSocketDebuggerUrl']

async def send(ws, method, params=None):
    send.i += 1
    await ws.send(json.dumps({'id':send.i,'method':method,'params':params or {}}))
    while True:
        msg=json.loads(await ws.recv())
        if msg.get('id')==send.i:
            return msg
send.i=0

async def evaljs(ws, expr):
    return await send(ws,'Runtime.evaluate',{'expression':expr,'awaitPromise':True,'returnByValue':True,'userGesture':True})

async def click(ws,x,y):
    await send(ws,'Input.dispatchMouseEvent',{'type':'mouseMoved','x':x,'y':y,'button':'none'})
    await send(ws,'Input.dispatchMouseEvent',{'type':'mousePressed','x':x,'y':y,'button':'left','clickCount':1})
    await send(ws,'Input.dispatchMouseEvent',{'type':'mouseReleased','x':x,'y':y,'button':'left','clickCount':1})

async def main():
    async with websockets.connect(page_ws(), max_size=10_000_000) as ws:
        await send(ws,'Runtime.enable')
        await send(ws,'Page.enable')
        # hard navigate fresh
        await send(ws,'Page.navigate',{'url':'https://chromastudio.ai/text-to-image?type=bria-3-2-t2i'})
        await asyncio.sleep(7)
        # scroll top, then find textarea rect
        state=await evaljs(ws,"(() => { window.scrollTo(0,0); const ta=document.querySelector('textarea'); const r=ta.getBoundingClientRect(); return {url:location.href, body:document.body.innerText, ta:{x:r.x,y:r.y,w:r.width,h:r.height}, val:ta.value}; })()")
        print('initial', json.dumps(state, indent=2)[:4000])
        val=state['result']['result']['value']; r=val['ta']
        await click(ws, r['x']+r['w']/2, r['y']+40)
        await asyncio.sleep(.5)
        await send(ws,'Input.insertText',{'text':PROMPT})
        await asyncio.sleep(1)
        # click visible internal mode switch/slider if off
        st=await evaljs(ws,"(() => { const arr=[...document.querySelectorAll('input[type=checkbox]')].map((e,i)=>({i,checked:e.checked,rect:(()=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})()})); const btn=[...document.querySelectorAll('button')].find(b=>b.innerText.includes('Generate')); const br=btn.getBoundingClientRect(); return {textareas:[...document.querySelectorAll('textarea')].map(t=>t.value), checks:arr, button:{disabled:btn.disabled,text:btn.innerText,rect:{x:br.x,y:br.y,w:br.width,h:br.height}}}; })()")
        print('after text', json.dumps(st, indent=2)[:4000])
        # internal mode visual switch point from elementFromPoint test
        checks=st['result']['result']['value']['checks']
        if len(checks) >= 3 and not checks[2]['checked']:
            await click(ws, 300, 360)
            await asyncio.sleep(1)
        st2=await evaljs(ws,"(() => { const btn=[...document.querySelectorAll('button')].find(b=>b.innerText.includes('Generate')); const br=btn.getBoundingClientRect(); return {body:document.body.innerText, textareas:[...document.querySelectorAll('textarea')].map(t=>t.value), checks:[...document.querySelectorAll('input[type=checkbox]')].map((e,i)=>({i,checked:e.checked})), button:{disabled:btn.disabled,text:btn.innerText,rect:{x:br.x,y:br.y,w:br.width,h:br.height}}}; })()")
        print('pre click', json.dumps(st2, indent=2)[:5000])
        b=st2['result']['result']['value']['button']['rect']
        if st2['result']['result']['value']['button']['disabled']:
            print('BLOCKED: generate disabled')
            return
        await click(ws, b['x']+b['w']/2, b['y']+b['h']/2)
        await asyncio.sleep(3)
        st3=await evaljs(ws,"(() => ({url:location.href, body:document.body.innerText, imgs:[...document.images].map(img=>({src:img.currentSrc||img.src,w:img.naturalWidth,h:img.naturalHeight})).filter(x=>x.w>100||x.h>100).slice(0,20)}))()")
        print('after click', json.dumps(st3, indent=2)[:8000])
asyncio.run(main())
