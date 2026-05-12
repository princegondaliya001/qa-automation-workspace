#!/usr/bin/env python3
import asyncio, json, urllib.request, websockets
PORT=9223
PROMPT='QA Waydroid Bria 3.2 mobile generation tiny blue robot holding a checkmark'

def page_ws():
    pages=json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/list'))
    page=next((p for p in pages if 'chromastudio.ai' in p.get('url','') and 'visible":true' in p.get('description','')), None)
    if not page: page=next(p for p in pages if 'chromastudio.ai' in p.get('url',''))
    return page['webSocketDebuggerUrl']
async def send(ws, method, params=None):
    send.i+=1; await ws.send(json.dumps({'id':send.i,'method':method,'params':params or {}}))
    while True:
        msg=json.loads(await ws.recv())
        if msg.get('id')==send.i: return msg
send.i=0
async def evaljs(ws, expr):
    return await send(ws,'Runtime.evaluate',{'expression':expr,'awaitPromise':True,'returnByValue':True,'userGesture':True})
async def click(ws,x,y):
    for typ in ['mouseMoved','mousePressed','mouseReleased']:
        p={'type':typ,'x':x,'y':y,'button':'left' if typ!='mouseMoved' else 'none','clickCount':1}
        await send(ws,'Input.dispatchMouseEvent',p)
async def main():
    async with websockets.connect(page_ws(), max_size=10_000_000) as ws:
        await send(ws,'Runtime.enable'); await send(ws,'Page.enable')
        await send(ws,'Page.navigate',{'url':'https://chromastudio.ai/text-to-image?type=bria-3-2-t2i'})
        await asyncio.sleep(7)
        js=f"""
        (() => {{
          window.scrollTo(0,0);
          const prompt={PROMPT!r};
          const ta=document.querySelector('textarea');
          const setter=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;
          setter.call(ta,prompt);
          ta.dispatchEvent(new InputEvent('input',{{bubbles:true,inputType:'insertText',data:prompt}}));
          ta.dispatchEvent(new Event('change',{{bubbles:true}}));
          return {{val:ta.value, body:document.body.innerText}};
        }})()
        """
        print('set prompt', json.dumps(await evaljs(ws,js), indent=2)[:4000])
        await asyncio.sleep(1)
        # enable internal by real click on visible slider if needed
        pre=await evaljs(ws,"(() => ({checks:[...document.querySelectorAll('input[type=checkbox]')].map((e,i)=>({i,checked:e.checked})), btn:(()=>{const b=[...document.querySelectorAll('button')].find(b=>b.innerText.includes('Generate')); const r=b.getBoundingClientRect(); return {disabled:b.disabled,text:b.innerText,rect:{x:r.x,y:r.y,w:r.width,h:r.height}}})(), vals:[...document.querySelectorAll('textarea')].map(t=>t.value)}))()")
        print('pre internal', json.dumps(pre, indent=2)[:4000])
        checks=pre['result']['result']['value']['checks']
        if len(checks)>=3 and not checks[2]['checked']:
            await click(ws,300,360)
            await asyncio.sleep(1)
        st=await evaljs(ws,"(() => ({body:document.body.innerText, checks:[...document.querySelectorAll('input[type=checkbox]')].map((e,i)=>({i,checked:e.checked})), vals:[...document.querySelectorAll('textarea')].map(t=>t.value), btn:(()=>{const b=[...document.querySelectorAll('button')].find(b=>b.innerText.includes('Generate')); const r=b.getBoundingClientRect(); return {disabled:b.disabled,text:b.innerText,rect:{x:r.x,y:r.y,w:r.width,h:r.height}}})()}))()")
        print('pre generate', json.dumps(st, indent=2)[:5000])
        v=st['result']['result']['value']; b=v['btn']['rect']
        if v['btn']['disabled']:
            print('BLOCKED disabled'); return
        await click(ws,b['x']+b['w']/2,b['y']+b['h']/2)
        await asyncio.sleep(5)
        print('after click', json.dumps(await evaljs(ws,"(() => ({url:location.href, body:document.body.innerText, imgs:[...document.images].map(img=>({src:img.currentSrc||img.src,w:img.naturalWidth,h:img.naturalHeight})).filter(x=>x.w>100||x.h>100).slice(0,20)}))()"), indent=2)[:8000])
asyncio.run(main())
