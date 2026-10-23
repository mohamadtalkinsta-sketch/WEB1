"""Native, offline-first Kivy application. No WebView, HTML or external service."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex
from ledger import default_state, make_entry, summarize, today_iso, to_number

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    def fa(value: Any) -> str:
        text = str(value)
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text
except ImportError:
    def fa(value: Any) -> str:
        return str(value)

BG="#F4F6F1"; PAPER="#FFFFFF"; INK="#1E312A"; MUTED="#6A7B73"
LINE="#E2E9E1"; GREEN="#245A49"; GREEN_LIGHT="#E6F0E8"
SAND="#F5EBDD"; RED="#A33D32"; PURPLE="#75639B"; BLUE="#456D8B"

def color(value): return get_color_from_hex(value)

def money(value):
    amount=int(value or 0)
    digits=f"{amount:,}".translate(str.maketrans("0123456789","۰۱۲۳۴۵۶۷۸۹"))
    return fa(f"{digits} تومان")

class Surface(BoxLayout):
    def __init__(self, fill=PAPER, radius=16, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            self._paint_color=Color(*color(fill))
            self._rect=RoundedRectangle(pos=self.pos,size=self.size,radius=[dp(radius)])
        self.bind(pos=self._paint,size=self._paint)
    def _paint(self,*_):
        self._rect.pos=self.pos; self._rect.size=self.size

class RoundButton(Button):
    def __init__(self, caption, tone="light", **kwargs):
        tones={"primary":(GREEN,"#FFFFFF"),"light":(GREEN_LIGHT,GREEN),
               "outline":(PAPER,GREEN),"dark":("#1C4438","#FFFFFF"),
               "danger":("#FBEAE7",RED),"muted":("#EEF1EC",MUTED),
               "sand":(SAND,"#684E35")}
        fill,ink=tones.get(tone,tones["light"])
        height=kwargs.pop("height",48)
        super().__init__(text=fa(caption),color=color(ink),font_size=sp(13),bold=True,
            background_normal="",background_down="",background_color=(0,0,0,0),
            size_hint_y=None,height=dp(height),padding=(dp(10),dp(7)),**kwargs)
        self._base=color(fill)
        with self.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            self._paint_color=Color(*self._base)
            self._rect=RoundedRectangle(pos=self.pos,size=self.size,radius=[dp(13)])
        self.bind(pos=self._sync,size=self._sync,state=self._pressed)
    def _sync(self,*_):
        self._rect.pos=self.pos; self._rect.size=self.size
    def _pressed(self,_,state):
        if state=="down":
            self._paint_color.rgba=tuple(max(0,c-.045) for c in self._base[:3])+(1,)
        else:
            self._paint_color.rgba=self._base

def txt(value,size=14,ink=INK,bold=False,height=38,align="right"):
    widget=Label(text=fa(value),color=color(ink),font_size=sp(size),bold=bold,
        halign=align,valign="middle",size_hint_y=None,height=dp(height),
        text_size=(Window.width-dp(42),None),shorten=False)
    widget.bind(width=lambda instance,width:setattr(instance,"text_size",(max(dp(35),width-dp(4)),None)))
    return widget

def field(hint="",value="",input_filter=None,multiline=False,height=48):
    return TextInput(text=str(value),hint_text=fa(hint),multiline=multiline,
        input_filter=input_filter,size_hint_y=None,height=dp(height),font_size=sp(14),
        foreground_color=color(INK),hint_text_color=color("#8B9991"),cursor_color=color(GREEN),
        background_normal="",background_active="",background_color=color("#F9FBF8"),
        padding=(dp(12),dp(13)),halign="right")

def heading(title,subtitle=""):
    panel=BoxLayout(orientation="vertical",spacing=dp(2),size_hint_y=None,height=dp(64))
    panel.add_widget(txt(title,20,INK,True,34))
    if subtitle: panel.add_widget(txt(subtitle,11,MUTED,False,26))
    return panel

class DaftarKhayatiApp(App):
    title="Daftar Khayati"
    def build(self):
        Window.clearcolor=color(BG); Window.softinput_mode="pan"
        self.data_path=Path(self.user_data_dir)/"daftar_khayati.json"
        self.data=self.load_data(); self.page="home"
        self.selected_card_id=self.data.get("settings",{}).get("last_card_id","")
        self.form_type="تکمیلی"; self.picker_filter="هر دو"; self.card_filter="هر دو"
        self.root_box=BoxLayout(orientation="vertical",padding=[dp(10),dp(8),dp(10),dp(5)],spacing=dp(8))
        self.header=Surface(fill=GREEN,orientation="horizontal",size_hint_y=None,height=dp(68),
            padding=[dp(15),dp(8)],spacing=dp(10))
        brand=Surface(fill="#326B56",size_hint=(None,None),size=(dp(44),dp(44)),radius=14)
        brand.add_widget(txt("د",25,"#FFFFFF",True,44,"center")); self.header.add_widget(brand)
        title_box=BoxLayout(orientation="vertical",spacing=dp(0))
        title_box.add_widget(txt("دفتر خیاطی",18,"#FFFFFF",True,31))
        title_box.add_widget(txt("ثبت کار و حساب‌وکتاب",10,"#D5E4D9",False,22))
        self.header.add_widget(title_box); self.root_box.add_widget(self.header)
        self.content_area=BoxLayout(orientation="vertical"); self.root_box.add_widget(self.content_area)
        self.nav=BoxLayout(size_hint_y=None,height=dp(65),spacing=dp(4),padding=[dp(1),dp(3)])
        self.nav_buttons={}
        for key,title in [("home","خانه"),("daily","ثبت کار"),("cards","کارت‌ها"),("receipts","دریافتی"),("reports","گزارش")]:
            b=RoundButton(title,"light",height=56)
            b.bind(on_release=lambda instance,dest=key:self.go(dest))
            self.nav_buttons[key]=b; self.nav.add_widget(b)
        self.root_box.add_widget(self.nav); self.refresh()
        return self.root_box

    def load_data(self):
        try:
            if self.data_path.exists():
                loaded=json.loads(self.data_path.read_text(encoding="utf-8")); base=default_state()
                if isinstance(loaded,dict):
                    base.update(loaded)
                    for key in ("cards","entries","receipts","settings"):
                        if not isinstance(base.get(key),(list,dict)): base[key]=default_state()[key]
                return base
        except (OSError,ValueError,TypeError): pass
        return default_state()

    def save(self):
        try:
            self.data_path.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.data_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding="utf-8")
            temporary.replace(self.data_path); return True
        except OSError as exc:
            self.message("ذخیره‌سازی انجام نشد",str(exc)); return False

    def go(self,page):
        self.page=page; self.refresh()

    def refresh(self):
        for key,button in self.nav_buttons.items():
            button.text=fa(("● " if key==self.page else "")+{"home":"خانه","daily":"ثبت کار","cards":"کارت‌ها","receipts":"دریافتی","reports":"گزارش"}[key])
            button._base=color(GREEN_LIGHT if key==self.page else PAPER); button._paint_color.rgba=button._base
        self.content_area.clear_widgets()
        view=ScrollView(do_scroll_x=False,bar_width=dp(3),scroll_type=["bars","content"])
        body=BoxLayout(orientation="vertical",size_hint_y=None,spacing=dp(10),padding=[dp(2),dp(4),dp(2),dp(18)])
        body.bind(minimum_height=body.setter("height")); getattr(self,"page_"+self.page)(body)
        view.add_widget(body); self.content_area.add_widget(view)

    def panel(self,height=100,fill=PAPER,padding=13):
        return Surface(fill=fill,orientation="vertical",size_hint_y=None,height=dp(height),padding=dp(padding),spacing=dp(7))

    def button_row(self,parent,buttons,height=46):
        row=BoxLayout(size_hint_y=None,height=dp(height),spacing=dp(8))
        for caption,callback,tone in buttons:
            button=RoundButton(caption,tone)
            button.bind(on_release=lambda instance,cb=callback:cb()); row.add_widget(button)
        parent.add_widget(row); return row

    def metric(self,parent,caption,value,sub,fill=PAPER):
        tile=self.panel(120,fill,11)
        tile.add_widget(txt(caption,11,MUTED,True,26))
        tile.add_widget(txt(value,16,GREEN if fill!=PAPER else INK,True,34))
        tile.add_widget(txt(sub,9,MUTED,False,20)); parent.add_widget(tile)

    def page_home(self,body):
        today=today_iso(); today_entries=[e for e in self.data["entries"] if e.get("date")==today]
        totals=summarize(self.data["entries"],self.data["receipts"])
        today_total=summarize(today_entries,[])
        name=self.data["settings"].get("name","").strip() or "خیاط عزیز"
        hero=self.panel(250,GREEN,17)
        hero.add_widget(txt(datetime.now().strftime("%Y-%m-%d"),10,"#D6E6DA",False,20))
        hero.add_widget(txt(f"خوش آمدی، {name}",22,"#FFFFFF",True,40))
        hero.add_widget(txt("کارها را ثبت کن؛ محاسبهٔ دستمزد با برنامه.",12,"#E2EEE5",False,32))
        self.button_row(hero,[("＋ ثبت کار جدید",lambda:self.go("daily"),"sand"),("ثبت دریافتی",lambda:self.go("receipts"),"dark")],48)
        hero.add_widget(txt(f"امروز {today_total['qty']} عدد کار · {len(today_entries)} ثبت",10,"#D6E6DA",False,24))
        body.add_widget(hero); body.add_widget(heading("خلاصهٔ حساب","مبالغ به تومان هستند."))
        grid=GridLayout(cols=2,spacing=dp(8),size_hint_y=None); grid.bind(minimum_height=grid.setter("height"))
        self.metric(grid,"دستمزد خالص امروز",money(today_total["net"]),"بعد از کسر هزینه‌ها",GREEN_LIGHT)
        self.metric(grid,"کار امروز",f"{today_total['qty']} عدد",f"{len(today_entries)} ثبت")
        self.metric(grid,"مجموع دریافتی",money(totals["received"]),"پول دریافت‌شده")
        balance=totals["net"]-totals["received"]
        self.metric(grid,"ماندهٔ حساب",money(balance),"خالص کار منهای دریافتی","#F7EEE1" if balance<0 else PAPER)
        body.add_widget(grid); body.add_widget(heading("شروع سریع","کارت‌های آماده را می‌توانی ویرایش کنی."))
        quick=self.panel(110,PAPER,12)
        quick.add_widget(txt(f"{len(self.data['cards'])} کارت کار آماده داری.",13,INK,True,28))
        self.button_row(quick,[("مدیریت کارت‌ها",lambda:self.go("cards"),"light"),("همهٔ ثبت‌ها",lambda:self.go("reports"),"outline")])
        body.add_widget(quick); body.add_widget(heading("آخرین کارها"))
        if not self.data["entries"]:
            empty=self.panel(100,PAPER,14); empty.add_widget(txt("هنوز کاری ثبت نشده است.",14,INK,True,35))
            empty.add_widget(txt("برای شروع «ثبت کار جدید» را بزن.",11,MUTED,False,28)); body.add_widget(empty)
        else:
            for entry in sorted(self.data["entries"],key=lambda item:item.get("date",""),reverse=True)[:4]:
                body.add_widget(self.entry_row(entry))

    def page_daily(self,body):
        body.add_widget(heading("ثبت کار روزانه","اطلاعات اصلی را وارد کن؛ جزئیات اضافه اختیاری‌اند."))
        chosen=next((c for c in self.data["cards"] if c["id"]==self.selected_card_id),None)
        if chosen: self.form_type=chosen["type"]
        type_panel=self.panel(90,PAPER,10); type_panel.add_widget(txt("نوع کار",11,MUTED,True,24))
        row=BoxLayout(size_hint_y=None,height=dp(38),spacing=dp(8))
        for val in ("تکمیلی","زنجیره‌ای"):
            b=RoundButton(val,"primary" if val==self.form_type else "light",height=38)
            b.bind(on_release=lambda instance,v=val:self.set_form_type(v)); row.add_widget(b)
        type_panel.add_widget(row); body.add_widget(type_panel)
        select=self.panel(101,GREEN_LIGHT,11); select.add_widget(txt("کارت لباس یا قطعه",11,MUTED,True,23))
        card_caption=f"{chosen.get('emoji','🧵')}  {chosen['name']} · {money(chosen.get('price',0))}" if chosen else "انتخاب کارت از فهرست"
        self.button_row(select,[(card_caption,self.open_card_picker,"light")]); body.add_widget(select)
        form=self.panel(228,PAPER,13); form.add_widget(txt("تعداد و دستمزد",15,INK,True,28))
        qty_row=BoxLayout(size_hint_y=None,height=dp(72),spacing=dp(9))
        qty_box=BoxLayout(orientation="vertical",spacing=dp(3)); qty_box.add_widget(txt("تعداد",10,MUTED,True,22))
        qty=field("مثلاً ۱۲","1","int"); qty_box.add_widget(qty)
        price_box=BoxLayout(orientation="vertical",spacing=dp(3)); price_box.add_widget(txt("دستمزد هر عدد (تومان)",10,MUTED,True,22))
        price_value=str(chosen.get("price",0)) if chosen and chosen.get("price") else ""
        price=field("مثلاً ۴۵۰۰۰",price_value,"int"); price_box.add_widget(price)
        qty_row.add_widget(qty_box); qty_row.add_widget(price_box); form.add_widget(qty_row)
        form.add_widget(txt("تاریخ (سال-ماه-روز)",10,MUTED,True,22))
        entry_date=field("2026-10-23",today_iso()); form.add_widget(entry_date); body.add_widget(form)
        advanced_button=RoundButton("＋ جزئیات اختیاری (رنگ، سایز و هزینه‌ها)","outline")
        advanced=self.panel(0,"#F8FAF6",10); advanced.height=0; advanced.opacity=0; advanced.disabled=True
        color_input=field("رنگ لباس"); size_input=field("سایز"); note_input=field("توضیحات",multiline=True,height=66)
        button_cost_input=field("هزینهٔ کل دکمه (تومان)","0","int")
        external_input=field("سایر هزینه‌ها (تومان)","0","int")
        charge_buttons=[True]
        charge_button=RoundButton("هزینهٔ دکمه از دستمزد کسر شود: بله","light",height=42)
        def toggle_charge():
            charge_buttons[0]=not charge_buttons[0]
            charge_button.text=fa("هزینهٔ دکمه از دستمزد کسر شود: "+("بله" if charge_buttons[0] else "خیر"))
            charge_button._base=color(GREEN_LIGHT if charge_buttons[0] else PAPER); charge_button._paint_color.rgba=charge_button._base
        charge_button.bind(on_release=lambda *_:toggle_charge())
        for item in (color_input,size_input,note_input,button_cost_input,external_input,charge_button): advanced.add_widget(item)
        def show_advanced(instance):
            visible=advanced.height==0
            advanced.height=dp(370) if visible else 0; advanced.opacity=1 if visible else 0
            advanced.disabled=not visible; instance.text=fa("− بستن جزئیات" if visible else "＋ جزئیات اختیاری (رنگ، سایز و هزینه‌ها)")
        advanced_button.bind(on_release=show_advanced); body.add_widget(advanced_button); body.add_widget(advanced)
        preview=self.panel(90,GREEN_LIGHT,11); net_label=txt("دستمزد خالص تقریبی: ۰ تومان",15,GREEN,True,34)
        preview.add_widget(net_label); preview.add_widget(txt("عدد نهایی پس از ثبت محاسبه می‌شود.",10,MUTED,False,23))
        def update_preview(*_):
            estimate=to_number(qty.text)*to_number(price.text)-(to_number(button_cost_input.text) if charge_buttons[0] else 0)-to_number(external_input.text)
            net_label.text=fa("دستمزد خالص تقریبی: "+money(estimate))
        for input_widget in (qty,price,button_cost_input,external_input): input_widget.bind(text=update_preview)
        body.add_widget(preview)
        def save_entry():
            card=next((c for c in self.data["cards"] if c["id"]==self.selected_card_id),None)
            if not card:
                self.message("انتخاب کارت","برای ثبت کار، ابتدا یک کارت لباس یا قطعه انتخاب کن."); self.open_card_picker(); return
            if card["type"]!=self.form_type:
                self.message("نوع کار","نوع کارت با نوع کاری که انتخاب شده یکی نیست."); return
            try:
                entry=make_entry(card=card,qty=qty.text,price=price.text,entry_date=entry_date.text.strip(),
                    color=color_input.text,size=size_input.text,note=note_input.text,
                    button_cost=button_cost_input.text,charge_buttons=charge_buttons[0],external_cost=external_input.text)
            except ValueError as exc:
                self.message("بررسی اطلاعات",str(exc)); return
            entry["id"]=f"{datetime.now().timestamp():.6f}"; self.data["entries"].append(entry)
            self.data["settings"]["last_card_id"]=card["id"]
            if self.save():
                self.message("ثبت شد",f"دستمزد خالص: {money(entry['net'])}"); self.page="home"; self.refresh()
        save_panel=BoxLayout(size_hint_y=None,height=dp(57),padding=[0,dp(3)])
        save_button=RoundButton("✓ ثبت کار","primary",height=52)
        save_button.bind(on_release=lambda *_:save_entry()); save_panel.add_widget(save_button); body.add_widget(save_panel)
        body.add_widget(heading("ثبت‌های اخیر"))
        for entry in sorted(self.data["entries"],key=lambda item:item.get("date",""),reverse=True)[:8]:
            body.add_widget(self.entry_row(entry,deletable=True))

    def set_form_type(self,value):
        self.form_type=value
        chosen=next((c for c in self.data["cards"] if c["id"]==self.selected_card_id),None)
        if chosen and chosen["type"]!=value: self.selected_card_id=""
        self.refresh()

    def open_card_picker(self):
        holder=BoxLayout(orientation="vertical",spacing=dp(8),padding=dp(10))
        search=field("جست‌وجوی کارت")
        holder.add_widget(search)
        filters=BoxLayout(size_hint_y=None,height=dp(42),spacing=dp(6))
        list_box=BoxLayout(orientation="vertical",size_hint_y=None,spacing=dp(7))
        list_box.bind(minimum_height=list_box.setter("height"))
        scroll=ScrollView(do_scroll_x=False,bar_width=dp(3)); scroll.add_widget(list_box)
        self.picker_filter="هر دو"
        def render_options(*_):
            list_box.clear_widgets(); query=search.text.strip().lower()
            matches=[c for c in self.data["cards"] if
                (self.picker_filter=="هر دو" or c["type"]==self.picker_filter)
                and (query in c["name"].lower() or query in c.get("description","").lower())]
            for card in matches:
                row=Surface(fill="#F6F8F4",orientation="horizontal",size_hint_y=None,height=dp(63),padding=dp(8),spacing=dp(8))
                glyph=Surface(fill=GREEN_LIGHT,size_hint=(None,1),width=dp(48),radius=12)
                glyph.add_widget(txt(card.get("emoji","🧵"),22,GREEN,True,48,"center")); row.add_widget(glyph)
                details=BoxLayout(orientation="vertical",spacing=dp(1))
                details.add_widget(txt(card["name"],12,INK,True,27))
                details.add_widget(txt(f"{card['type']} · {money(card.get('price',0))}",9,MUTED,False,22)); row.add_widget(details)
                choose=RoundButton("انتخاب","primary",height=43,size_hint_x=None,width=dp(78))
                def select_card(item=card):
                    self.selected_card_id=item["id"]; self.form_type=item["type"]
                    self.data["settings"]["last_card_id"]=item["id"]; self.save()
                    popup.dismiss(); self.page="daily"; self.refresh()
                choose.bind(on_release=lambda *_args,cb=select_card:cb()); row.add_widget(choose); list_box.add_widget(row)
            if not matches: list_box.add_widget(txt("نتیجه‌ای پیدا نشد. از صفحهٔ کارت‌ها، کارت جدید بساز.",11,MUTED,False,58))
        def set_filter(value):
            self.picker_filter=value; render_options()
            for button,val in zip(filters.children[::-1],("هر دو","تکمیلی","زنجیره‌ای")):
                button._base=color(GREEN if val==value else GREEN_LIGHT); button._paint_color.rgba=button._base
                button.color=color("#FFFFFF" if val==value else GREEN)
        for val in ("هر دو","تکمیلی","زنجیره‌ای"):
            b=RoundButton(val,"light",height=39); b.bind(on_release=lambda instance,v=val:set_filter(v)); filters.add_widget(b)
        holder.add_widget(filters); holder.add_widget(scroll)
        popup=Popup(title=fa("انتخاب کارت کار"),content=holder,size_hint=(0.96,0.84),auto_dismiss=True)
        self.button_row(holder,[("＋ ساخت کارت جدید",lambda:(popup.dismiss(),self.open_card_editor()),"primary")],46)
        search.bind(text=render_options); popup.open(); render_options()

    def page_cards(self,body):
        body.add_widget(heading("کارت‌های کار","لباس یا قطعه را یک‌بار تعریف کن و هر روز سریع انتخابش کن."))
        self.button_row(body,[("＋ ساخت کارت جدید",self.open_card_editor,"primary")])
        search=field("جست‌وجو: پیراهن، شلوار، زیپ..."); body.add_widget(search)
        filters=BoxLayout(size_hint_y=None,height=dp(43),spacing=dp(6))
        list_box=BoxLayout(orientation="vertical",size_hint_y=None,spacing=dp(8))
        list_box.bind(minimum_height=list_box.setter("height")); body.add_widget(filters); body.add_widget(list_box)
        def render_cards(*_):
            list_box.clear_widgets(); q=search.text.strip().lower()
            cards=[c for c in self.data["cards"] if (self.card_filter=="هر دو" or c["type"]==self.card_filter)
                   and (q in c["name"].lower() or q in c.get("description","").lower())]
            for card in cards:
                panel=self.panel(122,PAPER,10)
                row=BoxLayout(size_hint_y=None,height=dp(46),spacing=dp(8))
                glyph=Surface(fill=GREEN_LIGHT,size_hint=(None,1),width=dp(47),radius=12)
                glyph.add_widget(txt(card.get("emoji","🧵"),23,GREEN,True,46,"center")); row.add_widget(glyph)
                details=BoxLayout(orientation="vertical",spacing=dp(0))
                details.add_widget(txt(card["name"],13,INK,True,26))
                details.add_widget(txt(f"{card['type']} · {money(card.get('price',0))}",10,MUTED,False,22))
                row.add_widget(details); panel.add_widget(row)
                actions=BoxLayout(size_hint_y=None,height=dp(39),spacing=dp(7))
                edit=RoundButton("ویرایش","outline",height=38)
                edit.bind(on_release=lambda *_args,c=card:self.open_card_editor(c))
                use=RoundButton("ثبت این کار","light",height=38)
                def use_card(c=card):
                    self.selected_card_id=c["id"]; self.form_type=c["type"]; self.go("daily")
                use.bind(on_release=lambda *_args,cb=use_card:cb())
                actions.add_widget(edit); actions.add_widget(use); panel.add_widget(actions); list_box.add_widget(panel)
            if not cards: list_box.add_widget(txt("کارت مطابق جست‌وجو پیدا نشد.",12,MUTED,False,55))
        def set_filter(value):
            self.card_filter=value; render_cards(); rebuild_filters()
        def rebuild_filters():
            filters.clear_widgets()
            for val in ("هر دو","تکمیلی","زنجیره‌ای"):
                b=RoundButton(val,"primary" if val==self.card_filter else "light",height=39)
                b.bind(on_release=lambda instance,v=val:set_filter(v)); filters.add_widget(b)
        search.bind(text=render_cards); rebuild_filters(); render_cards()

    def open_card_editor(self,card=None):
        holder=BoxLayout(orientation="vertical",spacing=dp(7),padding=dp(12))
        holder.add_widget(txt("نام لباس یا قطعه",11,MUTED,True,24))
        name_input=field("مثلاً کت مردانه",card["name"] if card else ""); holder.add_widget(name_input)
        holder.add_widget(txt("نوع کار",11,MUTED,True,24))
        type_choice=[card.get("type",self.form_type) if card else self.form_type]
        type_row=BoxLayout(size_hint_y=None,height=dp(42),spacing=dp(8)); type_buttons={}
        def update_type_buttons():
            for value,button in type_buttons.items():
                button._base=color(GREEN if value==type_choice[0] else GREEN_LIGHT)
                button._paint_color.rgba=button._base; button.color=color("#FFFFFF" if value==type_choice[0] else GREEN)
        for value in ("تکمیلی","زنجیره‌ای"):
            b=RoundButton(value,"light",height=41)
            b.bind(on_release=lambda *_args,v=value:(type_choice.__setitem__(0,v),update_type_buttons()))
            type_buttons[value]=b; type_row.add_widget(b)
        holder.add_widget(type_row); update_type_buttons()
        holder.add_widget(txt("دستمزد پایه (تومان)",11,MUTED,True,24))
        price_input=field("مثلاً ۴۵۰۰۰",str(card.get("price",0)) if card else "","int"); holder.add_widget(price_input)
        holder.add_widget(txt("تعداد دکمهٔ پیش‌فرض",11,MUTED,True,24))
        button_count_input=field("۰",str(card.get("button_count",0)) if card else "0","int"); holder.add_widget(button_count_input)
        holder.add_widget(txt("توضیح اختیاری",11,MUTED,True,24))
        description_input=field("توضیح کوتاه",card.get("description","") if card else ""); holder.add_widget(description_input)
        buttons=BoxLayout(size_hint_y=None,height=dp(47),spacing=dp(8))
        popup=Popup(title=fa("ویرایش کارت" if card else "ساخت کارت جدید"),content=holder,size_hint=(0.93,0.86))
        save_button=RoundButton("ذخیرهٔ کارت","primary")
        def save_card():
            name=name_input.text.strip()
            if not name: self.message("نام کارت","نام لباس یا قطعه را وارد کن."); return
            item={"id":card["id"] if card else f"card-{datetime.now().timestamp():.6f}",
                "name":name,"type":type_choice[0],"emoji":card.get("emoji",self.emoji_for(name)) if card else self.emoji_for(name),
                "price":to_number(price_input.text),"button_count":to_number(button_count_input.text),
                "button_cost":to_number(card.get("button_cost",0)) if card else 0,
                "description":description_input.text.strip()}
            if card: self.data["cards"]=[item if c["id"]==card["id"] else c for c in self.data["cards"]]
            else: self.data["cards"].append(item)
            self.selected_card_id=item["id"]; self.form_type=item["type"]
            if self.save(): popup.dismiss(); self.go("cards")
        save_button.bind(on_release=lambda *_:save_card())
        cancel=RoundButton("انصراف","outline"); cancel.bind(on_release=lambda *_:popup.dismiss())
        buttons.add_widget(cancel); buttons.add_widget(save_button); holder.add_widget(buttons); popup.open()

    @staticmethod
    def emoji_for(name):
        if "شلوار" in name: return "👖"
        if "دامن" in name or "لباس" in name or "پیراهن" in name: return "👗"
        if "مانتو" in name or "کت" in name: return "🧥"
        if "دکمه" in name: return "🔘"
        if "زیپ" in name or "درز" in name or "دوخت" in name: return "🧵"
        return "👕"

    def entry_row(self,entry,deletable=False):
        panel=self.panel(110 if deletable else 72,PAPER,9)
        row=BoxLayout(size_hint_y=None,height=dp(44),spacing=dp(8))
        glyph=Surface(fill=GREEN_LIGHT,size_hint=(None,1),width=dp(43),radius=11)
        glyph.add_widget(txt(entry.get("emoji","🧵"),20,GREEN,True,43,"center")); row.add_widget(glyph)
        detail=BoxLayout(orientation="vertical",spacing=dp(0))
        detail.add_widget(txt(entry.get("card_name","کار"),12,INK,True,23))
        detail.add_widget(txt(f"{entry.get('date','')} · {entry.get('qty',0)} عدد · {money(entry.get('price',0))}",9,MUTED,False,20))
        row.add_widget(detail); row.add_widget(txt(money(entry.get("net",0)),11,GREEN,True,43,"left")); panel.add_widget(row)
        if deletable:
            btn=RoundButton("حذف این ثبت","danger",height=32)
            btn.bind(on_release=lambda *_:self.confirm("حذف ثبت کار","این ثبت حذف شود؟",lambda:self.delete_entry(entry)))
            panel.add_widget(btn)
        return panel

    def delete_entry(self,entry):
        self.data["entries"]=[x for x in self.data["entries"] if x.get("id")!=entry.get("id")]
        if self.save(): self.refresh()

    def page_receipts(self,body):
        totals=summarize(self.data["entries"],self.data["receipts"])
        body.add_widget(heading("دریافتی‌ها","مبلغی که واقعاً گرفته‌ای جدا از دستمزد ثبت می‌شود."))
        total_panel=self.panel(96,GREEN_LIGHT,12)
        total_panel.add_widget(txt("مجموع دریافتی",11,MUTED,True,23))
        total_panel.add_widget(txt(money(totals["received"]),20,GREEN,True,38)); body.add_widget(total_panel)
        form=self.panel(334,PAPER,13); form.add_widget(txt("ثبت دریافتی جدید",15,INK,True,30))
        amount=field("مبلغ (تومان)","","int"); date_input=field("سال-ماه-روز",today_iso()); note=field("توضیح: پیش‌پرداخت، تسویه و ...")
        form.add_widget(txt("مبلغ دریافتی",10,MUTED,True,22)); form.add_widget(amount)
        form.add_widget(txt("تاریخ",10,MUTED,True,22)); form.add_widget(date_input); form.add_widget(note)
        def save_receipt():
            amount_num=to_number(amount.text)
            if amount_num<1: self.message("مبلغ نامعتبر","مبلغ دریافتی باید بیشتر از صفر باشد."); return
            try: datetime.strptime(date_input.text.strip(),"%Y-%m-%d")
            except ValueError: self.message("تاریخ نامعتبر","تاریخ را به شکل سال-ماه-روز وارد کن."); return
            self.data["receipts"].append({"id":f"{datetime.now().timestamp():.6f}","date":date_input.text.strip(),"amount":amount_num,"note":note.text.strip()})
            if self.save(): self.go("receipts")
        self.button_row(form,[("✓ ثبت دریافتی",save_receipt,"primary")]); body.add_widget(form)
        body.add_widget(heading("سوابق دریافتی"))
        receipts=sorted(self.data["receipts"],key=lambda x:x.get("date",""),reverse=True)
        if not receipts: body.add_widget(txt("هنوز دریافتی ثبت نشده است.",12,MUTED,False,54))
        for receipt in receipts[:30]:
            panel=self.panel(70,PAPER,10)
            panel.add_widget(txt(f"{receipt.get('date','')} · {receipt.get('note') or 'بدون توضیح'}",10,MUTED,False,24))
            panel.add_widget(txt(money(receipt["amount"]),14,GREEN,True,30)); body.add_widget(panel)

    def page_reports(self,body):
        totals=summarize(self.data["entries"],self.data["receipts"]); balance=totals["net"]-totals["received"]
        body.add_widget(heading("گزارش و حساب‌وکتاب","خلاصهٔ مالی بر اساس تمام ثبت‌های ذخیره‌شده."))
        grid=GridLayout(cols=2,spacing=dp(8),size_hint_y=None); grid.bind(minimum_height=grid.setter("height"))
        for caption,value,fill_color in [
            ("تعداد کل کار",f"{totals['qty']} عدد",PAPER),("دستمزد ناخالص",money(totals["gross"]),PAPER),
            ("هزینهٔ دکمه",money(totals["buttons"]),PAPER),("سایر هزینه‌ها",money(totals["external"]),PAPER),
            ("دستمزد خالص",money(totals["net"]),GREEN_LIGHT),("دریافتی واقعی",money(totals["received"]),PAPER),
            ("ماندهٔ حساب",money(balance),"#F7EEE1" if balance<0 else PAPER)]:
            self.metric(grid,caption,value,"",fill_color)
        body.add_widget(grid); body.add_widget(heading("آخرین ثبت‌ها"))
        if not self.data["entries"]: body.add_widget(txt("پس از اولین ثبت، گزارش اینجا نمایش داده می‌شود.",12,MUTED,False,52))
        for entry in sorted(self.data["entries"],key=lambda item:item.get("date",""),reverse=True)[:20]:
            body.add_widget(self.entry_row(entry,deletable=True))
        panel=self.panel(100,PAPER,12)
        panel.add_widget(txt("دریافتی از دستمزد جدا حساب می‌شود.",12,INK,True,30))
        panel.add_widget(txt("مانده = دستمزد خالص تمام کارها − مجموع دریافتی‌ها",10,MUTED,False,30))
        body.add_widget(panel)

    def page_settings(self,body):
        body.add_widget(heading("تنظیمات و پشتیبان","داده‌ها فقط داخل فضای خصوصی همین اپ ذخیره می‌شوند."))
        panel=self.panel(178,PAPER,13); panel.add_widget(txt("نام دلخواه",11,MUTED,True,24))
        name=field("مثلاً نام کارگاه",self.data.get("settings",{}).get("name","")); panel.add_widget(name)
        def save_name():
            self.data["settings"]["name"]=name.text.strip()
            if self.save(): self.message("ذخیره شد","نام در صفحهٔ اصلی نمایش داده می‌شود."); self.go("home")
        self.button_row(panel,[("ذخیرهٔ نام",save_name,"primary")]); body.add_widget(panel)
        backup=self.panel(160,GREEN_LIGHT,13)
        backup.add_widget(txt("نسخهٔ پشتیبان اطلاعات",14,GREEN,True,30))
        backup.add_widget(txt("یک فایل JSON در حافظهٔ داخلی خصوصی اپ ساخته می‌شود.",10,MUTED,False,38))
        self.button_row(backup,[("ساخت پشتیبان",self.make_backup,"light")]); body.add_widget(backup)
        privacy=self.panel(128,PAPER,13); privacy.add_widget(txt("حریم خصوصی",13,INK,True,27))
        privacy.add_widget(txt("این نسخه وب‌اپ نیست، صفحهٔ اینترنتی باز نمی‌کند و برای ثبت و محاسبه به اینترنت نیاز ندارد.",10,MUTED,False,54))
        body.add_widget(privacy)
        danger=self.panel(82,"#FBEAE7",12)
        self.button_row(danger,[("پاک‌کردن تمام اطلاعات",lambda:self.confirm("پاک‌کردن اطلاعات","کارت‌ها، ثبت‌ها و دریافتی‌ها حذف و نمونه‌های اولیه بازسازی می‌شوند.",self.reset_data),"danger")])
        body.add_widget(danger)

    def make_backup(self):
        backup_path=Path(self.user_data_dir)/"backup-daftar-khayati.json"
        try:
            backup_path.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding="utf-8")
            self.message("پشتیبان ساخته شد",f"مسیر داخلی فایل:\n{backup_path}\n\nاین نسخه هنوز دکمهٔ اشتراک‌گذاری به پوشهٔ Downloads ندارد.")
        except OSError as exc: self.message("خطا در پشتیبان",str(exc))

    def reset_data(self):
        self.data=default_state(); self.selected_card_id="shirt"; self.form_type="تکمیلی"
        if self.save(): self.go("home")

    def confirm(self,title,text,on_yes):
        holder=BoxLayout(orientation="vertical",spacing=dp(12),padding=dp(14))
        holder.add_widget(txt(text,13,INK,False,94))
        row=BoxLayout(size_hint_y=None,height=dp(46),spacing=dp(8))
        popup=Popup(title=fa(title),content=holder,size_hint=(0.9,0.42))
        cancel=RoundButton("انصراف","outline"); yes=RoundButton("تأیید","danger")
        cancel.bind(on_release=lambda *_:popup.dismiss())
        def perform(): popup.dismiss(); on_yes()
        yes.bind(on_release=lambda *_:perform()); row.add_widget(cancel); row.add_widget(yes); holder.add_widget(row); popup.open()

    def message(self,title,text):
        holder=BoxLayout(orientation="vertical",spacing=dp(10),padding=dp(13))
        holder.add_widget(txt(text,12,INK,False,88))
        popup=Popup(title=fa(title),content=holder,size_hint=(0.9,0.37))
        close=RoundButton("باشه","primary"); close.bind(on_release=lambda *_:popup.dismiss())
        holder.add_widget(close); popup.open()

if __name__=="__main__":
    DaftarKhayatiApp().run()
