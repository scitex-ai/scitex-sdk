import {beforeEach,expect,it} from 'vitest';
import {mountAppHeader,getAppHeader} from '../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/app-header/mount';

beforeEach(()=>{document.body.innerHTML='';});

it('adopts one canonical sibling picker only within an explicitly supplied owning region',()=>{
 const region=document.createElement('main');document.body.append(region);
 region.innerHTML='<div data-stx-app-header></div><section><div class="stx-app-project-selector" data-stx-project-picker><button aria-expanded="true">Current</button></div></section>';
 const picker=region.querySelector<HTMLElement>('[data-stx-project-picker]')!;
 const button=picker.querySelector('button')!;let clicks=0;button.addEventListener('click',()=>clicks++);
 const [header]=mountAppHeader(region);button.click();
 expect([picker.parentElement===header.projectSlot,button.getAttribute('aria-expanded'),clicks,mountAppHeader(region).length,getAppHeader()===header]).toEqual([true,'true',1,0,true]);
});

it('disposes disconnected instances and returns the actual connected header identity',()=>{
 const old=document.createElement('main');old.innerHTML='<div data-stx-app-header></div>';document.body.append(old);
 const [previous]=mountAppHeader(old);old.remove();
 const current=document.createElement('main');current.innerHTML='<div data-stx-app-header></div>';document.body.append(current);
 const [next]=mountAppHeader(current);
 expect([getAppHeader()===next,previous.headerEl.isConnected,old.querySelector('[data-stx-app-header]')!.children.length]).toEqual([true,false,0]);
});

it.each<[string, number]>([['<div data-stx-app-header></div>'.repeat(2),1],['<div data-stx-app-header></div>',2]])('refuses ambiguous header/picker regions %s', (headers,pickers)=>{
 const region=document.createElement('main');document.body.append(region);
 region.innerHTML=headers+'<section>'+ '<div class="stx-app-project-selector" data-stx-project-picker></div>'.repeat(pickers)+'</section>';
 const original=[...region.querySelectorAll('[data-stx-project-picker]')];
 mountAppHeader(region);
 expect(original.every(picker=>picker.parentElement?.tagName==='SECTION')).toBe(true);
});


it('does not erase owner content from a connected container after its header was removed',()=>{
 const region=document.createElement('main');region.innerHTML='<div data-stx-app-header></div>';document.body.append(region);
 const [previous]=mountAppHeader(region);const container=region.firstElementChild!;
 const retained=document.createElement('button');retained.textContent='Owner state';container.append(retained);
 previous.headerEl.remove();
 const next=document.createElement('main');next.innerHTML='<div data-stx-app-header></div>';document.body.append(next);
 mountAppHeader(next);
 expect([retained.isConnected,retained.textContent,container.contains(retained)]).toEqual([true,'Owner state',true]);
});
