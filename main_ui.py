'''
  main_ui.py
  The main UI part for volume normalizer
  version : 1.0.0   2020/10/19
  version : 1.1.0   2021/11/15

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

VERSION_INFO='1.1.0'
DATE_INFO='2021/11/15'

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


# vocal string setting part
area_volumeparam = ttk.LabelFrame(tab1, text=' 參數設定 ')
area_volumeparam.grid(column=0, row=2, padx=8, pady=4, sticky=tk.W)

GnMax = tk.StringVar()
GnMax.set('2.0')
ttk.Label(area_volumeparam, text="免調音量最大增益值:").grid(column=0, row=0, sticky=tk.W)
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
    conn = pyodbc.connect(r'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ='+dbfilename.get()+';')
    cursor = conn.cursor()
    cursor.execute('select * from ktv_Song')
    
    gn_notfound_cnt=0
    gn_scaleover_cnt=0
    gn_valueover_cnt=0
    gn_total_cnt=0
    for row in cursor.fetchall():
        #for item in row:
        #    print(item)
        gnscale = find_gn(row[9])
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
            
        cmd = "update ktv_Song set Song_Volume = "+str(gnvalue)+" where Song_Id = '"+row[0]+"'"
        print(cmd, gnscale)    
        cursor.execute(cmd)
        gn_total_cnt=gn_total_cnt+1
        if gn_total_cnt==10000:
            cursor.commit()
            gn_total_cnt=0
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
                 '\n'+\
                 '   ┌─────────┐\n'+\
                 '   │ 人聲字串指定  │\n'+\
                 '   └─────────┘\n'+\
                 '[免調音量最大增益值] : 若音量需要調整的倍數,小於此值時\n'+\
                 '                       不會重新壓縮音軌調整音量, 若大於此值\n'+\
                 '                       就會重新壓縮音軌, 原始檔案會在檔名前\n'+\
                 '                       加上 _ORG_ 保留, 原檔名會被蓋寫為\n'+\
                 '                       調整過音量的檔案\n'+\
                 '[略過已有_gn檔案] : 若檔名中已有 _gn, 則不處理此檔案\n\n'+\
                 '   ┌────────┐\n'+\
                 '   │ 資料庫設定   │\n'+\
                 '   └────────┘\n'+\
                 '[資料庫檔案] : 選擇 Crazy KTV 的 CrazySong.mdb 檔案\n'+\
                 '[預設音量基準] : 在  Crazy KTV 中每首歌曲基準的音量值\n'+\
                 '                 實際設定到 CrazySong.mdb 的音量,會是\n'+\
                 '                 從檔名中 _gnXXX 抓出 XXX 的數值, 然後以\n'+\
                 '                 預設音量 * XXX / 100 的方式算出最終音量\n'+\
                 '                 例如歌曲為 _gn125, 基準音量設定為 50,\n'+\
                 '                 此歌在資料庫中音量為 50*125/100=62.5\n'+\
                 '[更新資料庫] : 開始根據預設音量基準及每首歌 _gn數值,更新資料庫\n\n'+\
                 '  程式的動作為 :\n'+\
                 '  - 先判斷須調整的音量增益\n'+\
                 '  - 如果低於[免調音量最大增益值],則直接將增益值_gnXXX串到檔名後\n'+\
                 '  - 如果高於[免調音量最大增益值],就會重新壓縮音軌,\n'+\
                 '    盡量調整到 replaygain 的 -89dB 基準,\n'+\
                 '    原始檔案會在檔名前加上 _ORG_ 保留, 若是壓縮過程有錯,\n'+\
                 '    或者調整過後的音量增益還是太大, 就在檔名前加 _ERR_\n\n')
     
# Add another Menu to the Menu Bar and an item
help_menu = Menu(menu_bar, tearoff=0)
help_menu.add_command(label="Help", command=help_Box)
help_menu.add_command(label="About", command=_msgBox)   # display messagebox when clicked
menu_bar.add_cascade(label="Help", menu=help_menu)

#======================
# Start GUI
#======================

win.mainloop()
