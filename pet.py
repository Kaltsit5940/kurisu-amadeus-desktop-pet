"""Amadeus Kurisu: offline, transparent, taskbar-anchored Windows desktop pet."""
from __future__ import annotations

import argparse
import ctypes as C
from ctypes import wintypes as W
import json
import math
import os
from pathlib import Path
import random
import sys
import time
import traceback
from PIL import Image

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
ASSETS = ROOT / 'assets'
USER_DIR = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'KurisuAmadeusPet'
META = json.loads((ASSETS / 'manifest.json').read_text(encoding='utf-8'))
STATES = META['states']
TALK_SEQUENCE = [
    ('mouth_closed', .16), ('mouth_teeth', .10), ('mouth_open', .12),
    ('mouth_wide', .08), ('mouth_open', .10), ('mouth_closed', .09),
    ('talk_pause_blink_half', .055), ('talk_pause_blink', .075),
    ('talk_pause_blink_half', .055), ('mouth_closed', .11),
    ('mouth_round', .13), ('mouth_open', .09), ('mouth_teeth', .10),
    ('mouth_closed', .19), ('mouth_teeth', .09), ('mouth_open', .12),
    ('mouth_round', .11), ('mouth_closed', .24), ('mouth_open', .11),
    ('mouth_wide', .08), ('mouth_teeth', .11), ('mouth_closed', .22),
    ('idle', .18),
]
TALK_DURATION = sum(duration for _, duration in TALK_SEQUENCE)
CHEEK_SEQUENCE = [
    ('idle', .10), ('cheek_20', .15), ('cheek_35', .17),
    ('cheek_50', .18), ('cheek_65', .18), ('cheek_80', .18),
    ('cheek_90', .16), ('cheek_100', .70), ('cheek_tap', .15),
    ('cheek_100', 1.35), ('cheek_tap', .13), ('cheek_100', .55),
    ('cheek_90', .15), ('cheek_80', .15), ('cheek_65', .17),
    ('cheek_50', .17), ('cheek_35', .16), ('cheek_20', .15),
    ('idle', .10),
]
CHEEK_DURATION = sum(duration for _, duration in CHEEK_SEQUENCE)


def speech_cel(elapsed):
    for cel, duration in TALK_SEQUENCE:
        if elapsed < duration:
            return cel
        elapsed -= duration
    return 'idle'


def cheek_cel(elapsed):
    for cel, duration in CHEEK_SEQUENCE:
        if elapsed < duration:
            return cel
        elapsed -= duration
    return 'idle'


def self_test():
    ims = {s: Image.open(ASSETS / f'{s}.png').convert('RGBA') for s in STATES}
    assert len(STATES) >= 8
    assert all(im.size == tuple(META['size']) for im in ims.values())
    alpha = ims['idle'].getchannel('A').tobytes()
    assert all(ims[s].getchannel('A').tobytes() == alpha
               for s in STATES if not s.startswith('cheek_'))
    assert 0 < META['anchor_y'] < META['size'][1]
    assert ims['idle'].getbbox() is not None
    assert all(ims[s].tobytes() != ims['idle'].tobytes() for s in STATES if s != 'idle')
    assert all(ims[s].crop((220,190,510,285)).tobytes() ==
               ims['idle'].crop((220,190,510,285)).tobytes()
               for s in STATES if s.startswith('mouth_'))
    assert len({speech_cel(t/24) for t in range(math.ceil(TALK_DURATION*24))}) >= 5
    assert all(cel in ims for cel, _ in CHEEK_SEQUENCE)
    assert len({cheek_cel(t/24) for t in range(math.ceil(CHEEK_DURATION*24))}) >= 9
    assert cheek_cel(CHEEK_DURATION) == 'idle'
    return {'ok': True, 'illustrated_keyframes': META['illustrated_keyframes'],
            'animation_cels': len(STATES), 'states': STATES,
            'source_size': META['source_size'], 'sprite_size': META['size'],
            'fps_options': [12, 18, 24, 30]}


if sys.platform == 'win32':
    user = C.WinDLL('user32', use_last_error=True)
    gdi = C.WinDLL('gdi32', use_last_error=True)
    kernel = C.WinDLL('kernel32', use_last_error=True)
    shell = C.WinDLL('shell32', use_last_error=True)
    LRESULT = C.c_ssize_t
    WNDPROC = C.WINFUNCTYPE(LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM)

    class WNDCLASS(C.Structure):
        _fields_ = [('style', W.UINT), ('lpfnWndProc', WNDPROC), ('cbClsExtra', C.c_int),
                    ('cbWndExtra', C.c_int), ('hInstance', W.HINSTANCE), ('hIcon', W.HICON),
                    ('hCursor', W.HANDLE), ('hbrBackground', W.HBRUSH),
                    ('lpszMenuName', W.LPCWSTR), ('lpszClassName', W.LPCWSTR)]

    class BITMAPINFOHEADER(C.Structure):
        _fields_ = [('biSize', W.DWORD), ('biWidth', W.LONG), ('biHeight', W.LONG),
                    ('biPlanes', W.WORD), ('biBitCount', W.WORD), ('biCompression', W.DWORD),
                    ('biSizeImage', W.DWORD), ('biXPelsPerMeter', W.LONG),
                    ('biYPelsPerMeter', W.LONG), ('biClrUsed', W.DWORD), ('biClrImportant', W.DWORD)]

    class BLEND(C.Structure):
        _fields_ = [('op', C.c_ubyte), ('flags', C.c_ubyte),
                    ('alpha', C.c_ubyte), ('format', C.c_ubyte)]

    class GUID(C.Structure):
        _fields_ = [('Data1', W.DWORD), ('Data2', W.WORD), ('Data3', W.WORD), ('Data4', C.c_ubyte * 8)]

    class NOTIFYICONDATA(C.Structure):
        _fields_ = [('cbSize', W.DWORD), ('hWnd', W.HWND), ('uID', W.UINT),
                    ('uFlags', W.UINT), ('uCallbackMessage', W.UINT), ('hIcon', W.HICON),
                    ('szTip', W.WCHAR * 128), ('dwState', W.DWORD), ('dwStateMask', W.DWORD),
                    ('szInfo', W.WCHAR * 256), ('uTimeoutOrVersion', W.UINT),
                    ('szInfoTitle', W.WCHAR * 64), ('dwInfoFlags', W.DWORD),
                    ('guidItem', GUID), ('hBalloonIcon', W.HICON)]

    def api(lib, name, restype, *args):
        f = getattr(lib, name)
        f.restype, f.argtypes = restype, list(args)
        return f

    api(kernel, 'GetModuleHandleW', W.HMODULE, W.LPCWSTR)
    api(kernel, 'CreateMutexW', W.HANDLE, C.c_void_p, W.BOOL, W.LPCWSTR)
    api(kernel, 'CloseHandle', W.BOOL, W.HANDLE)
    api(user, 'RegisterClassW', W.ATOM, C.POINTER(WNDCLASS))
    api(user, 'CreateWindowExW', W.HWND, W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD,
        C.c_int, C.c_int, C.c_int, C.c_int, W.HWND, W.HMENU, W.HINSTANCE, C.c_void_p)
    api(user, 'DefWindowProcW', LRESULT, W.HWND, W.UINT, W.WPARAM, W.LPARAM)
    api(user, 'FindWindowW', W.HWND, W.LPCWSTR, W.LPCWSTR)
    api(user, 'GetWindowRect', W.BOOL, W.HWND, C.POINTER(W.RECT))
    api(user, 'LoadCursorW', W.HANDLE, W.HINSTANCE, C.c_void_p)
    api(user, 'LoadImageW', W.HANDLE, W.HINSTANCE, W.LPCWSTR, W.UINT, C.c_int, C.c_int, W.UINT)
    api(user, 'GetMessageW', W.BOOL, C.POINTER(W.MSG), W.HWND, W.UINT, W.UINT)
    api(user, 'TranslateMessage', W.BOOL, C.POINTER(W.MSG))
    api(user, 'DispatchMessageW', LRESULT, C.POINTER(W.MSG))
    api(user, 'UpdateLayeredWindow', W.BOOL, W.HWND, W.HDC, C.POINTER(W.POINT),
        C.POINTER(W.SIZE), W.HDC, C.POINTER(W.POINT), W.DWORD, C.POINTER(BLEND), W.DWORD)
    api(user, 'SetTimer', C.c_size_t, W.HWND, C.c_size_t, W.UINT, C.c_void_p)
    api(user, 'KillTimer', W.BOOL, W.HWND, C.c_size_t)
    api(user, 'SetCapture', W.HWND, W.HWND)
    api(user, 'ReleaseCapture', W.BOOL)
    api(user, 'GetCursorPos', W.BOOL, C.POINTER(W.POINT))
    api(user, 'ShowWindow', W.BOOL, W.HWND, C.c_int)
    api(user, 'DestroyWindow', W.BOOL, W.HWND)
    api(user, 'SetForegroundWindow', W.BOOL, W.HWND)
    api(user, 'CreatePopupMenu', W.HMENU)
    api(user, 'AppendMenuW', W.BOOL, W.HMENU, W.UINT, C.c_size_t, W.LPCWSTR)
    api(user, 'TrackPopupMenu', W.UINT, W.HMENU, W.UINT, C.c_int, C.c_int, C.c_int, W.HWND, C.c_void_p)
    api(user, 'DestroyMenu', W.BOOL, W.HMENU)
    api(user, 'SystemParametersInfoW', W.BOOL, W.UINT, W.UINT, C.c_void_p, W.UINT)
    api(user, 'MessageBoxW', C.c_int, W.HWND, W.LPCWSTR, W.LPCWSTR, W.UINT)
    api(user, 'PostQuitMessage', None, C.c_int)
    api(gdi, 'CreateCompatibleDC', W.HDC, W.HDC)
    api(gdi, 'CreateDIBSection', W.HBITMAP, W.HDC, C.POINTER(BITMAPINFOHEADER), W.UINT,
        C.POINTER(C.c_void_p), W.HANDLE, W.DWORD)
    api(gdi, 'SelectObject', W.HANDLE, W.HDC, W.HANDLE)
    api(gdi, 'DeleteObject', W.BOOL, W.HANDLE)
    api(gdi, 'DeleteDC', W.BOOL, W.HDC)
    api(shell, 'Shell_NotifyIconW', W.BOOL, W.DWORD, C.POINTER(NOTIFYICONDATA))


class Pet:
    def __init__(self, smoke_seconds=0, report_path=None):
        try:
            user.SetProcessDpiAwarenessContext(C.c_void_p(-4))
        except (AttributeError, OSError):
            user.SetProcessDPIAware()
        self.raw = {s: Image.open(ASSETS / f'{s}.png').convert('RGBA') for s in STATES}
        self.settings = {'height': 680, 'fps': 24, 'right_gap': 35, 'auto_expressions': True}
        try:
            self.settings.update(json.loads((USER_DIR / 'settings.json').read_text(encoding='utf-8')))
        except (OSError, ValueError):
            pass
        self.settings['height'] = min(800, max(320, int(self.settings['height'])))
        self.settings['fps'] = min(30, max(12, int(self.settings['fps'])))
        self.work = W.RECT()
        user.SystemParametersInfoW(0x30, 0, C.byref(self.work), 0)
        self.h = self.settings['height']
        self.w = round(self.h * META['size'][0] / META['size'][1])
        self.x = self.work.right - self.w - int(self.settings['right_gap'])
        self.y = self.anchor_top() - round(self.h * META['anchor_y'] / META['size'][1])
        self.state = 'idle'
        self.state_started = time.perf_counter()
        self.state_history = ['idle']
        self.returned_to_idle = []
        self.next_blink = time.perf_counter() + random.uniform(2.5, 4.5)
        self.blink_started = None
        self.next_micro = time.perf_counter() + random.uniform(9, 14)
        self.next_frame = 0.0
        self.last_anchor_check = 0.0
        self.drag = None
        self.hidden = False
        self.paused = False
        self.cache = {}
        self.drawn = None
        self.frame_count = 0
        self.unique_frames = set()
        self.errors = []
        self.smoke_seconds = smoke_seconds
        self.report_path = report_path
        self.start = time.perf_counter()
        self.smoke_step = -1
        self.wndproc = WNDPROC(self.on_message)
        self.instance = kernel.GetModuleHandleW(None)
        self.clsname = 'KurisuAmadeusIndependentPetWindow'
        wc = WNDCLASS(8,self.wndproc,0,0,self.instance,None,
                      user.LoadCursorW(None,C.c_void_p(32512)),None,None,self.clsname)
        user.RegisterClassW(C.byref(wc))
        self.hwnd = user.CreateWindowExW(0x80000|0x80|0x8|0x08000000,
            self.clsname,'红莉栖 · Amadeus 桌宠',0x80000000,
            int(self.x),int(self.y),self.w,self.h,None,None,self.instance,None)
        if not self.hwnd:
            raise C.WinError(C.get_last_error())
        self.dc = self.bitmap = self.old_bitmap = None
        self.allocate()
        self.icon = user.LoadImageW(None,str(ASSETS/'kurisu.ico'),1,32,32,0x10)
        self.tray = NOTIFYICONDATA()
        self.tray.cbSize=C.sizeof(self.tray)
        self.tray.hWnd=self.hwnd
        self.tray.uID=1
        self.tray.uFlags=1|2|4
        self.tray.uCallbackMessage=0x8001
        self.tray.hIcon=self.icon
        self.tray.szTip='红莉栖 · 右键表情 / 帧率；滚轮缩放'
        shell.Shell_NotifyIconW(0,C.byref(self.tray))
        self.draw('idle',0)
        user.ShowWindow(self.hwnd,4)
        user.SetTimer(self.hwnd,1,10,None)

    def anchor_top(self):
        rect=W.RECT()
        hwnd=user.FindWindowW('Shell_TrayWnd',None)
        if hwnd and user.GetWindowRect(hwnd,C.byref(rect)) and rect.right-rect.left > rect.bottom-rect.top:
            return rect.top
        return self.work.bottom

    def allocate(self):
        self.release_surface()
        self.dc=gdi.CreateCompatibleDC(None)
        info=BITMAPINFOHEADER(C.sizeof(BITMAPINFOHEADER),self.w,-self.h,
                              1,32,0,self.w*self.h*4,0,0,0,0)
        self.bits=C.c_void_p()
        self.bitmap=gdi.CreateDIBSection(self.dc,C.byref(info),0,C.byref(self.bits),None,0)
        if not self.bitmap:
            raise C.WinError(C.get_last_error())
        self.old_bitmap=gdi.SelectObject(self.dc,self.bitmap)
        self.cache.clear()
        self.drawn=None

    def release_surface(self):
        if getattr(self,'dc',None):
            if self.old_bitmap:gdi.SelectObject(self.dc,self.old_bitmap)
            if self.bitmap:gdi.DeleteObject(self.bitmap)
            gdi.DeleteDC(self.dc)
            self.dc=self.bitmap=self.old_bitmap=None

    def prepared(self,state,step):
        key=state
        if key not in self.cache:
            # Draw one crisp animation cel. Cross-fading two eye positions
            # creates doubled pupils, so expressions never blend whole faces.
            im=self.raw[state]
            im=im.resize((self.w,self.h),Image.Resampling.LANCZOS)
            self.cache[key]=(im.convert('RGBa').tobytes('raw','BGRa'),im.getchannel('A'))
        return self.cache[key]

    def draw(self,state,step):
        if self.hidden:return
        key=(state,step,int(self.x),int(self.y),self.w,self.h)
        if key==self.drawn:return
        data,self.alpha=self.prepared(state,step)
        C.memmove(self.bits,data,len(data))
        dst,size,src,blend=W.POINT(int(self.x),int(self.y)),W.SIZE(self.w,self.h),W.POINT(0,0),BLEND(0,0,255,1)
        if not user.UpdateLayeredWindow(self.hwnd,None,C.byref(dst),C.byref(size),
                                        self.dc,C.byref(src),0,C.byref(blend),2):
            raise C.WinError(C.get_last_error())
        self.drawn=key
        self.frame_count+=1
        self.unique_frames.add((state,step))

    def resize(self,h):
        self.h=min(800,max(320,int(h)))
        self.w=round(self.h*META['size'][0]/META['size'][1])
        self.x=min(self.work.right-self.w,max(self.work.left,self.x))
        self.y=self.anchor_top()-round(self.h*META['anchor_y']/META['size'][1])
        self.settings['height']=self.h
        self.settings['right_gap']=max(0,self.work.right-(self.x+self.w))
        self.allocate()
        self.draw('idle',0)
        self.save()

    def save(self):
        if self.smoke_seconds:return
        USER_DIR.mkdir(parents=True,exist_ok=True)
        (USER_DIR/'settings.json').write_text(json.dumps(self.settings,ensure_ascii=False),encoding='utf-8')

    def change(self,state):
        self.state=state
        self.state_started=time.perf_counter()
        self.state_history.append(state)
        self.next_frame=0
        if state=='idle':
            self.next_micro=self.state_started+random.uniform(9,14)

    def frame_for(self,now):
        if self.state=='idle':
            if self.blink_started is None and now>=self.next_blink:
                self.blink_started=now
            if self.blink_started is not None:
                p=now-self.blink_started
                if p>=.20:
                    self.blink_started=None
                    self.next_blink=now+random.uniform(3,6)
                else:
                    if p<.055 or p>=.145:return 'blink_half',0
                    return 'blink',0
            return 'idle',0
        t=now-self.state_started
        if self.state=='talking':
            if t>=TALK_DURATION:
                self.change('idle')
                self.returned_to_idle.append(True)
                return 'idle',0
            return speech_cel(t),0
        if self.state=='cheek_prop':
            if t>=CHEEK_DURATION:
                self.change('idle')
                self.returned_to_idle.append(True)
                return 'idle',0
            return cheek_cel(t),0
        duration={'surprise':1.85,'thinking':2.65,'embarrassed':2.35,
                  'joy':2.25,'annoyed':2.25,'teasing':2.1}.get(self.state,2.25)
        if t>=duration:
            self.change('idle')
            self.returned_to_idle.append(True)
            return 'idle',0
        if self.state=='thinking' and t<.18:
            return ('blink_half' if t<.055 or t>=.13 else 'blink'),0
        return self.state,0

    def tick(self):
        now=time.perf_counter()
        if self.smoke_seconds and now-self.start>=self.smoke_seconds:
            if self.report_path:
                Path(self.report_path).write_text(json.dumps({
                    'ok':not self.errors,'errors':self.errors,
                    'frames_presented':self.frame_count,
                    'unique_state_steps':len(self.unique_frames),
                    'states_seen':self.state_history,
                    'returned_to_idle':self.returned_to_idle,
                    'size':[self.w,self.h], 'anchor_y':self.y+round(self.h*META['anchor_y']/META['size'][1]),
                    'taskbar_top':self.anchor_top()},ensure_ascii=False,indent=2),encoding='utf-8')
            user.DestroyWindow(self.hwnd)
            return
        if now-self.last_anchor_check>=2:
            self.last_anchor_check=now
            target=self.anchor_top()-round(self.h*META['anchor_y']/META['size'][1])
            if target!=self.y:
                self.y=target
                self.drawn=None
        if self.paused or self.hidden or self.drag:return
        if self.smoke_seconds:
            sequence=['surprise','embarrassed','thinking','joy','annoyed','talking','cheek_prop']
            step=int((now-self.start)/3.1)
            if step!=self.smoke_step and step<len(sequence):
                self.smoke_step=step
                self.change(sequence[step])
        elif self.state=='idle' and self.settings['auto_expressions'] and now>=self.next_micro:
            self.change(random.choices(['thinking','teasing','joy','cheek_prop'],
                                       weights=[3,2,2,1])[0])
        if now<self.next_frame:return
        self.next_frame=now+1/self.settings['fps']
        state,step=self.frame_for(now)
        self.draw(state,step)

    def menu(self):
        m=user.CreatePopupMenu()
        user.AppendMenuW(m,1,0,'红莉栖 · Amadeus 独立桌宠')
        user.AppendMenuW(m,0x800,0,None)
        labels=[(101,'惊讶','surprise'),(102,'害羞','embarrassed'),
                (103,'思考','thinking'),(104,'开心','joy'),
                (105,'不满','annoyed'),(106,'说话','talking'),
                (107,'得意','teasing'),(108,'眨眼','blink'),(109,'回到常态','idle'),
                (110,'托腮','cheek_prop')]
        for ident,title,_ in labels:user.AppendMenuW(m,0,ident,title)
        user.AppendMenuW(m,0x800,0,None)
        user.AppendMenuW(m,8 if self.settings['auto_expressions'] else 0,201,'偶尔自动变换表情')
        user.AppendMenuW(m,8 if self.paused else 0,202,'暂停动画')
        for ident,h in [(301,420),(302,550),(303,680),(304,800)]:
            user.AppendMenuW(m,8 if self.h==h else 0,ident,f'大小：{h} 像素')
        for ident,fps in [(401,12),(402,18),(403,24),(404,30)]:
            user.AppendMenuW(m,8 if self.settings['fps']==fps else 0,ident,f'动画：{fps} 帧/秒')
        user.AppendMenuW(m,0x800,0,None)
        user.AppendMenuW(m,0,601,'显示' if self.hidden else '暂时隐藏')
        user.AppendMenuW(m,0,602,'使用说明')
        user.AppendMenuW(m,0,699,'退出红莉栖')
        p=W.POINT();user.GetCursorPos(C.byref(p))
        user.SetForegroundWindow(self.hwnd)
        cmd=user.TrackPopupMenu(m,0x100|2,p.x,p.y,0,self.hwnd,None)
        user.DestroyMenu(m)
        self.next_frame=0
        if 101<=cmd<=110:
            self.paused=False
            if cmd==108:
                self.change('idle')
                self.blink_started=time.perf_counter()
            else:
                self.change({i:s for i,_,s in labels}[cmd])
        elif cmd==201:self.settings['auto_expressions']=not self.settings['auto_expressions']
        elif cmd==202:self.paused=not self.paused
        elif 301<=cmd<=304:self.resize({301:420,302:550,303:680,304:800}[cmd])
        elif 401<=cmd<=404:self.settings['fps']={401:12,402:18,403:24,404:30}[cmd]
        elif cmd==601:
            self.hidden=not self.hidden
            user.ShowWindow(self.hwnd,0 if self.hidden else 4)
            self.drawn=None
        elif cmd==602:
            user.MessageBoxW(self.hwnd,'手指会贴在 Windows 任务栏上缘。右键选择托腮，可以看到抬手、轻点任务栏和放下手。拖动可水平移动，滚轮调整大小，双击触发说话。\n右键还可选择表情、12/18/24/30 帧/秒或暂时隐藏。\n托盘图标可找回她或退出。设置保存在本机，无需联网，也无需 Codex。','红莉栖 · 使用说明',0)
        elif cmd==699:user.DestroyWindow(self.hwnd)
        self.save()

    def on_message(self,hwnd,msg,wp,lp):
        try:
            if msg==0x113:self.tick();return 0
            if msg==0x84 and hasattr(self,'alpha'):
                x=C.c_short(lp&65535).value-int(self.x)
                y=C.c_short((lp>>16)&65535).value-int(self.y)
                return 1 if 0<=x<self.w and 0<=y<self.h and self.alpha.getpixel((x,y))>20 else -1
            if msg==0x21:return 3
            if msg==0x201:
                p=W.POINT();user.GetCursorPos(C.byref(p))
                self.drag=p.x-self.x
                user.SetCapture(hwnd);return 0
            if msg==0x200 and self.drag is not None:
                p=W.POINT();user.GetCursorPos(C.byref(p))
                self.x=min(self.work.right-self.w,max(self.work.left,p.x-self.drag))
                self.drawn=None
                state,step=self.frame_for(time.perf_counter())
                self.draw(state,step);return 0
            if msg==0x202 and self.drag is not None:
                self.drag=None;user.ReleaseCapture()
                self.settings['right_gap']=max(0,self.work.right-(self.x+self.w))
                self.save();return 0
            if msg==0x203:self.change('talking');return 0
            if msg==0x20A:
                self.resize(self.h+(40 if C.c_short((wp>>16)&65535).value>0 else -40));return 0
            if msg==0x205 or (msg==0x8001 and lp==0x205):self.menu();return 0
            if msg==0x8001 and lp==0x203:
                self.hidden=False;user.ShowWindow(hwnd,4);self.drawn=None;return 0
            if msg==2:
                user.KillTimer(hwnd,1)
                if hasattr(self,'tray'):shell.Shell_NotifyIconW(2,C.byref(self.tray))
                self.release_surface();self.save();user.PostQuitMessage(0);return 0
        except Exception as exc:
            self.errors.append(traceback.format_exc())
            if self.smoke_seconds and self.report_path:
                Path(self.report_path).write_text(json.dumps({'ok':False,'errors':self.errors},ensure_ascii=False),encoding='utf-8')
            user.DestroyWindow(hwnd);return 0
        return user.DefWindowProcW(hwnd,msg,wp,lp)

    def run(self):
        msg=W.MSG()
        while user.GetMessageW(C.byref(msg),None,0,0)>0:
            user.TranslateMessage(C.byref(msg));user.DispatchMessageW(C.byref(msg))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--self-test',action='store_true')
    p.add_argument('--smoke-seconds',type=float,default=0)
    p.add_argument('--report')
    args=p.parse_args()
    if args.self_test:
        result=self_test()
        if args.report:Path(args.report).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        if sys.stdout:print(json.dumps(result,ensure_ascii=False))
        return
    mutex=None
    if not args.smoke_seconds:
        mutex=kernel.CreateMutexW(None,False,'Local\\KurisuAmadeusPet')
        if C.get_last_error()==183:
            if mutex:kernel.CloseHandle(mutex)
            return
    try:Pet(args.smoke_seconds,args.report).run()
    finally:
        if mutex:kernel.CloseHandle(mutex)


if __name__=='__main__':
    try:main()
    except Exception:
        USER_DIR.mkdir(parents=True,exist_ok=True)
        (USER_DIR/'error.log').write_text(traceback.format_exc(),encoding='utf-8')
        if sys.platform=='win32' and '--smoke-seconds' not in sys.argv and '--self-test' not in sys.argv:
            user.MessageBoxW(None,'红莉栖未能启动，错误已保存：\n'+str(USER_DIR/'error.log'),'红莉栖',0x10)
        raise
