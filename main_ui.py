'''
  main_ui.py
  The main UI part for volume normalizer
  version : 1.0.0   2020/10/19

  This program will calculate the replaygain value
  for normalization and add "_gnXXX" to the file name.
  If the gain is too large(over twice the volume),
  this program can change the actual volume and re-encode
  the audio stream.  
'''

#======================
# imports
#======================
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from tkinter import Menu
from tkinter import messagebox as msg
from tkinter import Spinbox
from time import  sleep         # careful - this can freeze the GUI
# from tkcalendar import Calendar, DateEntry
from tkinter import filedialog as fd
import os
import sys
from datetime import datetime
from io import StringIO
import sqlite3
import math
import pyodbc
import normalizer_core

VERSION_INFO='1.0.0'
DATE_INFO='2020/10/19'

# define the file extension type to process
ext_list = [".mpg", ".mpeg", ".vob", ".mkv", ".dat", '.mp4']


# Create instance
win = tk.Tk()   

# Add a title       
win.title("Volume Normalizer")  

tabControl = ttk.Notebook(win)          # Create Tab Control

tab1 = ttk.Frame(tabControl)            # Create a tab 
tabControl.add(tab1, text='環境設定')      # Add the tab
tab2 = ttk.Frame(tabControl)            # Add a second tab
tabControl.add(tab2, text='輸出')

tab3 = ttk.Frame(tabControl)
tabControl.add(tab3, text='更新資料庫')
tabControl.pack(expand=1, fill="both")  # Pack to make visible
#
# setting area
#
area_config = ttk.LabelFrame(tab1, text=' 目錄設定 ')
area_config.grid(column=0, row=0, padx=8, pady=4, sticky=tk.W)

def getDirName():
    fDir = os.path.dirname(os.path.abspath('__file__'))
    fName = fd.askdirectory(parent=win, title='choose KTV source dir', initialdir=fDir)
    if fName :
        filedir.set(fName)
    
ttk.Button(area_config, text="來源目錄", command=getDirName).grid(column=0, row=0, sticky=tk.W)
filedir = tk.StringVar()
filedir.set((os.path.dirname(os.path.abspath('__file__'))).replace('\\','/'))
filedirLen = 60
filedirEntry = ttk.Entry(area_config, width=filedirLen,textvariable=filedir)
filedirEntry.grid(column=1, row=0, sticky=tk.W)

'''
def gettempDirName():
    fDir = os.path.dirname(os.path.abspath('__file__'))
    fName = fd.askdirectory(parent=win, title='choose temp file dir', initialdir=fDir)
    if fName :
        tempdir.set(fName)
    
ttk.Button(area_config, text="暫存檔目錄", command=gettempDirName).grid(column=0, row=1, sticky=tk.W)
tempdir = tk.StringVar()
tempdir.set((os.path.dirname(os.path.abspath('__file__'))).replace('\\','/'))
tempdirLen = 60
tempdirEntry = ttk.Entry(area_config, width=tempdirLen,textvariable=tempdir)
tempdirEntry.grid(column=1, row=1, sticky=tk.W)
'''

# vocal string setting part
area_volumeparam = ttk.LabelFrame(tab1, text=' 參數設定 ')
area_volumeparam.grid(column=0, row=2, padx=8, pady=4, sticky=tk.W)

GnMax = tk.StringVar()
GnMax.set('2.0')
ttk.Label(area_volumeparam, text="免調整最大增益值:").grid(column=0, row=0, sticky=tk.W)
ttk.Spinbox(area_volumeparam, from_=1.0, to=5.0, increment=0.1, justify=tk.CENTER, textvariable=GnMax).grid(column=1, row=0, sticky=tk.W)


SkipFileEn = tk.IntVar()
SkipFilecb = tk.Checkbutton(area_volumeparam, text="略過已有_gn檔案", variable=SkipFileEn)
SkipFilecb.deselect()
SkipFilecb.grid(column=0, row=1, sticky=tk.W)


#############################
### ------- tab2 output 
#############################
area_execute = ttk.LabelFrame(tab2, text='啟動')
area_execute.grid(column=0, row=0, padx=8, pady=4, sticky=tk.W)

def progressbar_update(status_text, percentage):
    status_line_l.configure(text=status_text)
    progress_b["value"]=int(percentage)
    progress_b.update()
    
def progressbar_reset():
    status_line_l.configure(text='idle')
    progress_b["value"]=0
    progress_b.update()
    
def StartCMD():
    startbtn.configure(state='disabled')
    run_state.set(STATE_RUN)
    stopbtn.configure(state='normal')
    pausebtn.configure(state='normal')
    print(GnMax.get(), SkipFileEn.get())
    
    # freeze the current setting, so the value will not be changed when UI changes
    Fsrcdir=filedir.get().replace('\\','/').rstrip('/')
    #Ftmpdir=tempdir.get().replace('\\','/').rstrip('/')
    FSkipFileEn=SkipFileEn.get()
    FGnMax = float(GnMax.get())
        
    total_items=0
    logarea.delete('1.0', tk.END)   # clear text area
    # count the total files to process 
    for dirpath, dirlist, filelist in os.walk(Fsrcdir):
        for fileitem in filelist:
            fullpath=os.path.join(dirpath, fileitem)
            filename, fileext = os.path.splitext(fileitem)
            for ext_name in ext_list:
                if fileext.lower()==ext_name: 
                    total_items=total_items+1
                    
    cur_item=0
    for dirpath, dirlist, filelist in os.walk(Fsrcdir):
        for fileitem in filelist:
            fullpath=os.path.join(dirpath, fileitem)
            filename, fileext = os.path.splitext(fileitem)
            for ext_name in ext_list:
                if fileext.lower()==ext_name:
                    if (run_state.get()==STATE_PAUSE):
                        pausebtn.configure(state='normal')
                        startbtn.wait_variable(run_state)   # wait until run_state change value
                        pausebtn.configure(state='normal')
                    if (run_state.get()==STATE_STOP):
                        startbtn.configure(state='normal')
                        stopbtn.configure(state='disabled')
                        pausebtn.configure(state='disabled')
                        logarea.insert(tk.END, 'user stopped\n')
                        progressbar_reset()

                    cur_item=cur_item+1
                    if (FSkipFileEn>0):  
                        if ((fileitem.lower().find('_gn')>=0)):
                            # skip enabled and filename has _vl or _vr
                            progressbar_update('skipping '+fileitem, cur_item*100/total_items)
                            logarea.insert(tk.END, 'skipping '+fileitem+'\n')
                            continue
                    if ((fileitem.lower().find('_vl')<=0) and (fileitem.lower().find('_vr')<=0)):
                            # skip when filename has no _vl or _vr
                            progressbar_update('no vocal ch info, skipping '+fileitem, cur_item*100/total_items)
                            logarea.insert(tk.END, 'skipping '+fileitem+'\n')
                            continue        
                    progressbar_update('processing '+fileitem, cur_item*100/total_items)
                    
                    result=normalizer_core.volume_normalize(dirpath, filename, fileext, FGnMax)
                    if result=='':
                        logarea.insert(tk.END, 'error on "'+fileitem+'"\n')
                    else:
                        now = datetime.now()
                        current_time = now.strftime("%H:%M:%S")
                        logarea.insert(tk.END, current_time+' processed "'+fileitem+'" => '+result+'\n')
                        newfilename=filename+result+fileext
                
    startbtn.configure(state='normal')
    stopbtn.configure(state='disabled')
    pausebtn.configure(state='disabled')
    run_state.set(STATE_STOP)
    progressbar_reset()
    
    
def StopCMD():
    run_state.set(STATE_STOP)
    
def PauseCMD():
    if (pausebtn.cget("text")=="暫停"):
        pausebtn.configure(text="繼續")
        run_state.set(STATE_PAUSE)
        pausebtn.configure(state='disabled')
    else:
        pausebtn.configure(text="暫停")
        run_state.set(STATE_RUN)
        pausebtn.configure(state='disabled')

STATE_STOP=0
STATE_PAUSE=1
STATE_RUN=2
run_state=tk.IntVar()
run_state.set(STATE_STOP)
        
startbtn=ttk.Button(area_execute, text="開始", command=StartCMD)
startbtn.grid(column=0, row=0, sticky=tk.W)
pausebtn=ttk.Button(area_execute, text="暫停", command=PauseCMD)
pausebtn.grid(column=1, row=0, sticky=tk.W)
pausebtn.configure(state='disabled')
stopbtn=ttk.Button(area_execute, text="停止", command=StopCMD)
stopbtn.grid(column=2, row=0, sticky=tk.W)
stopbtn.configure(state='disabled')

area_log = ttk.LabelFrame(tab2, text='結果')
area_log.grid(column=0, row=1, padx=8, pady=4, sticky=tk.W)
logarea = scrolledtext.ScrolledText(area_log,width=80,height=16)
logarea.grid(column=0, row=0, sticky=tk.W)


#
# status area
#
area_status = ttk.LabelFrame(tab2, text=' 進度 ')
area_status.grid(column=0, row=2, padx=8, pady=4, sticky=tk.W)

ttk.Label(area_status, text="狀態 :").grid(column=0, row=0, sticky=tk.W)
status_line_l=ttk.Label(area_status, text='idle')
status_line_l.grid(column=1, row=0, sticky=tk.W)
ttk.Label(area_status, text="進度 :").grid(column=0, row=1, sticky=tk.W)
progress_b = ttk.Progressbar(area_status, orient='horizontal', length=540, mode='determinate')
progress_b.grid(column=1, row=1)

#
#  Tab 3 : update KTV database file
#
#
# database area
#
area_database = ttk.LabelFrame(tab3, text=' 資料庫設定 ')
area_database.grid(column=0, row=0, padx=10, pady=10, sticky=tk.W)
# ------------------- 輸入資料庫檔案 ------------
def getDatabaseFileName():
    fDir = os.path.dirname('__file__')
    fName = fd.askopenfilename(parent=win, title='select database file', initialdir=fDir)
    dbfilename.set(fName)
    
ttk.Button(area_database, text="資料庫檔案", command=getDatabaseFileName).grid(column=0, row=0, padx=10, pady=10, sticky=tk.W)
dbfilename = tk.StringVar()
dbfilenameLen = 60
dbfileEntry = ttk.Entry(area_database, width=dbfilenameLen,textvariable=dbfilename)
dbfileEntry.grid(column=1, row=0, sticky=tk.W)

# ------------------- 預設音量設定 ----------
defaultGN = tk.StringVar()
defaultGN.set('50')
ttk.Label(area_database, text="預設音量基準:").grid(column=0, row=1, sticky=tk.W)
ttk.Spinbox(area_database, from_=1, to=99, increment=1, justify=tk.CENTER, textvariable=defaultGN).grid(column=1, row=1, padx=10, pady=10,sticky=tk.W)

# ------------------- 開始更新資料庫 --------
def MissingFileErrBox():
    msg.showinfo('錯誤 ', '找不到資料庫檔案\n請先設定好資料庫檔案')

def find_gn(filename):
    fname=filename.lower()
    gnpos=fname.find('_gn')
    if gnpos<=0:
        return 0    # not found
    gnpos=gnpos+3
    gnvalue=0
    while ((fname[gnpos]>='0') and (fname[gnpos]<='9')):
        gnvalue=gnvalue*10+int(fname[gnpos])
        gnpos=gnpos+1
    return gnvalue
    
def updateDatabaseFile():
    if not (os.path.isfile(dbfilename.get())):
        MissingFileErrBox()
        return
    conn = pyodbc.connect(r'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=d:/temp/crazyktv/crazysong.mdb;')
    cursor = conn.cursor()
    cursor.execute('select * from ktv_Song')
    
    gn_notfound_cnt=0
    gn_scaleover_cnt=0
    gn_valueover_cnt=0
    for row in cursor.fetchall():
        gnscale = find_gn(row[10])
        if gnscale>999:
            gnscale=999
            gn_scaleover_cnt=gn_scaleover_cnt+1
        if gnscale==0:
            gnvalue=int(defaultGN.get())
            gn_notfound_cnt=gn_notfound_cnt+1
        else:
            gnvalue=int(int(defaultGN.get())*float(gnscale)/100.0)
            if gnvalue>99:
                gnvalue=99
                gn_valueover_cnt=gn_valueover_cnt+1
            
        cmd = "update ktv_Song set Song_Volume = "+str(gnvalue)+" where Song_Id = '"+row[1]+"'"
        print(cmd, gnscale)    
        cursor.execute(cmd)
    cursor.commit() 
    print("gain adjustment -\n not found:",gn_notfound_cnt,\
          "\n scale overflow:",gn_scaleover_cnt,"\n value overflow:",gn_valueover_cnt)
          
ttk.Button(area_database, text="更新資料庫", command=updateDatabaseFile).grid(column=1, row=2, padx=10, pady=10, sticky=tk.W)

#######################################
# main menu part
#######################################
# Exit GUI cleanly
def _quit():
    win.quit()
    win.destroy()
    exit() 
    
# Creating a Menu Bar
menu_bar = Menu(win)
win.config(menu=menu_bar)

# Add menu items
file_menu = Menu(menu_bar, tearoff=0)
#file_menu.add_command(label="New")
#file_menu.add_separator()
file_menu.add_command(label="Exit", command=_quit)
menu_bar.add_cascade(label="File", menu=file_menu)

# Display a Message Box
def _msgBox():
    msg.showinfo('Volume Normalizer', '版本 :'+VERSION_INFO+'\n日期 :'+DATE_INFO+'\n')  

def help_Box():
    msg.showinfo('環境設定說明',\
                 '   ┌──────┐\n'+\
                 '   │ 目錄設定 │\n'+\
                 '   └──────┘\n'+\
                 '[來源目錄]: 指定待處理影片所在目錄\n'+\
                 '[暫存檔目錄]: 指定處理影片時,暫存檔使用的目錄\n'+\
                 '              若指定於 ramdisk, 建議要有 500MB 可使用空間\n\n'+\
                 '   ┌─────────┐\n'+\
                 '   │ 人聲字串指定  │\n'+\
                 '   └─────────┘\n'+\
                 '  針對單音軌(左右聲道)與多重音軌(第一第二音軌)\n'+\
                 '  偵測出人聲的聲道後,加入檔名的字串定義\n'+\
                 '  建議單音軌左聲道為人聲, 使用字串 _vL, 多重音軌第一軌人聲, 使用 _VL\n'+\
                 '  就可以用字串來辨別是單音軌或多音軌,\n'+\
                 '  若有特殊原因需要更改定義, 請自行勾選不同字串\n\n'+\
                 '   ┌─────────┐\n'+\
                 '   │ 分析區間設定  │\n'+\
                 '   └─────────┘\n'+\
                 '  人聲分離過程, 需要花很多時間, 其實只要分析歌曲其中一部分,\n'+\
                 '  裏頭有包含人聲部分, 就可以正確判斷出人聲的音軌,\n'+\
                 '  分析區間設定, 用來設定要拿歌曲那一個區間做分析\n\n'+\
                 '   ┌──────┐\n'+\
                 '   │ 輸出設定 │\n'+\
                 '   └──────┘\n'+\
                 '[略過已有_vL_vR檔案]: 若檔名已經有 _vL 或 _vR 的識別字串\n'+\
                 '                        就不再處理這檔案\n'+\
                 '[輸出選擇] : 選擇判斷結果的輸出,\n'+\
                 '     [純測試不輸出]: 結果只輸出到狀態視窗, 不影響檔名\n'+\
                 '     [直接修改檔名]: 將判斷結果的 _vL _vR 字串,直接更新到檔名.\n'+\
                 '     [輸出到BAT檔] : 將修改檔名的動作改存到 .bat 檔案,\n'+\
                 '                     讓使用者再自行執行 .bat 檔案更改檔名\n'+\
                 '[指定BAT檔] : 設定 .bat 檔的檔名, 若上方選擇 [輸出到BAT檔]\n'+\
                 '              就會將結果輸出到此指定的 BAT 檔中\n' )
                 
# Add another Menu to the Menu Bar and an item
help_menu = Menu(menu_bar, tearoff=0)
help_menu.add_command(label="Help", command=help_Box)
help_menu.add_command(label="About", command=_msgBox)   # display messagebox when clicked
menu_bar.add_cascade(label="Help", menu=help_menu)

#======================
# Start GUI
#======================

win.mainloop()