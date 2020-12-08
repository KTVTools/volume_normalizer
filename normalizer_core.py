'''
 normalizer_core.py
 This module provide the analysis core of the voice channel
 
 version : 1.0.0  2020/10/19
 version : 1.0.1  2020/12/08
           fix determine_adj_db(), if after adj, gain is still not enough,
           adjust to the max gain not to overflow both channel.
           _OVR will be added if the gain is still larger than GnMax
                the final adjusted file will be gernerate with _gnXXX
           _ERR0 _ERR1 will be added to file name if ERROR happened, and
                no adjusted file will be generated 
''' 

import os
import subprocess
from math import log10

# put ffmpeg.exe, mediainfo.exe in the same directory for the
# program to find. Spleeter package must be installed properly too.

ffmpegcmd="ffmpeg.exe"
mediainfocmd="mediainfo.exe"
spleetercmd="python\python.exe -m spleeter separate "

MP3BITRATE='256k'

def db_to_val(db):
    return(10.0**(db/20.0))

def read_mediainfo(filename):
    cmdlist=mediainfocmd+' --output=General;%AudioCount% "'+filename+'"'
    try:
        result = subprocess.check_output(cmdlist, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        return [0, 0]
    
    result=str(result,'utf-8').strip()
    try:
        audio_no = int(result)
    except:
        return[0, 0]
    
    cmdlist=mediainfocmd+' --output=General;%Duration% "'+filename+'"'
    try:
        result = subprocess.check_output(cmdlist, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        return [0, 0]
    
    result=str(result,'utf-8').strip()   # return stream length in ms
    try:
        audio_len = int(result)/1000     # turn into sec
    except:
        return [0, 0]
    
    # return values :
    # audio_no : audio streams in the file
    # audio_len : stream length in seconds
    return [audio_no, audio_len]

def calculate_replaygain(infile, audio_no, kara_ch):
    if (audio_no==1):  # only 1 audio stream
        if (kara_ch==0):   
            param='-filter_complex "[0:a]pan=stereo|c0=c0|c1=c0[out];[out]replaygain" -f null nul'
        else:
            param='-filter_complex "[0:a]pan=stereo|c0=c1|c1=c1[out];[out]replaygain" -f null nul'
    else:
        if (kara_ch==0):   
            param='-af replaygain -map 0:a:0 -f null nul'
        else:
            param='-af replaygain -map 0:a:1 -f null nul'
            
    cmdlist=ffmpegcmd+' -i "'+infile+'" '+param
    #print(cmdlist)
    try:
        result = subprocess.check_output(cmdlist, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print("error on ch0 replaygain")
        return [0.0, 0.0]
    
    if (audio_no==1):
        gain_str = str(result).find('track_gain') # single channel need search twice
    else:
        gain_str = 0
    gain_str = str(result).find('track_gain', gain_str+10)
    db_str = str(result).find('dB', gain_str)
    ch_db = float(str(result)[gain_str+13:db_str-1])
    peak_str = str(result).find('track_peak', db_str)
    tmp_str=str(result)[peak_str+13:-1].replace('\\n','\n').replace('\\r','\r')
    ch_peak = float(tmp_str.rstrip())
    
    return [ch_db, ch_peak]

def determine_adj_db(ch_kara, GnMax, ch0_db, ch1_db, ch0_peak, ch1_peak):
# return values :
#   need_adj ? : need adjustment or nor
#   ch0_adj    : volume scale for ch0
#   ch1_adj    : volume scale for ch1   
    gain0_val=db_to_val(ch0_db)
    gain1_val=db_to_val(ch1_db) 
    print(gain0_val, gain1_val, ch0_peak, ch1_peak)
    # sanity check, in some cases, peak is greater then 1.0, abnormal
    if ch0_peak>1.0:
        ch0_peak=1.0
    if ch1_peak>1.0:
        ch1_peak=1.0
    if (ch_kara==0) and (gain0_val>GnMax):
        # adjust volume based on channel 0
        # test if gain value will overflow either channel
        if (ch0_peak*gain0_val>1.0) or (ch1_peak*gain0_val>1.0):
            # overflow, we can only choose to use less gain
            if (ch0_peak>ch1_peak):
                max_gain=0.999999/(ch0_peak)
            else:
                max_gain=0.999999/(ch1_peak)
            print(gain0_val, max_gain, GnMax)
            # when peak=1, new_gain=org_gain*org_peak=org_gain/(max_gain)
            if (gain0_val/max_gain)<GnMax:
                # adjust a little
                print('adjust less :', max_gain)
                return [True, max_gain, max_gain]
            else:
                # after adjustment, the volume is still to small, 
                # adjust to the max based on ch0(ch1 may overflow)
                # return [True, 0.999999/ch0_peak, 0.999999/ch0_peak]
                # adjust a little, peak will not overflow, but gain will be higher
                return [True, max_gain, max_gain]
        else:
            # it's ok to adjust both channels to new volume level
            print('adjust full :', gain0_val)
            return [True, gain0_val, gain0_val]
  
    elif (ch_kara==1) and (gain1_val>GnMax):
        # adjust volume based on channel 1
        # test if gain value will overflow both channel
        if (ch0_peak*gain1_val>1.0) or (ch1_peak*gain1_val>1.0):
            # overflow, we can only choose to use less gain
            if (ch0_peak>ch1_peak):
                max_gain=0.999999/ch0_peak
            else:
                max_gain=0.999999/ch1_peak
            # when peak=1, new_gain=org_gain*org_peak=org_gain/(max_gain)
            if (gain1_val/max_gain)<GnMax:  # after adjustment, within threshold
                # then we will adjust both channel
                print('adjust less :', max_gain)
                return [True, max_gain, max_gain]
            else:
                # after adjustment, the volume is still too small
                # return [True, 0.999999/ch1_peak, 0.999999/ch1_peak] 
                # adjust a little, peak will not overflow, but gain will be higher
                return [True, max_gain, max_gain]                
        else:
            # it's ok to adjust both channels, after adjustment, replaygain=0
            print('adjust full :', gain1_val)
            return[ True, gain1_val, gain1_val]
   
    else:
        return [False, 0.0, 0.0]
        
    
def adj_volume(org_fullpath, fullpath, audio_no, ch0_adj, ch1_adj):
    print("adj volume ch0=", ch0_adj, "ch1=", ch1_adj)
    if audio_no==1:
        param='-map 0:a -af "volume='+str(ch0_adj)+'" -c:a libmp3lame -b:a '+MP3BITRATE
    else:
        param='-map 0:a:0 -af "volume='+str(ch0_adj)+'" -c:a libmp3lame -b:a '+MP3BITRATE+\
              ' -map 0:a:1 -af "volume='+str(ch1_adj)+'" -c:a libmp3lame -b:a '+MP3BITRATE
    cmdlist = ffmpegcmd+' -i "'+org_fullpath+'" -map 0:v -c:v copy '+param+' "'+fullpath+'"'
    #print(cmdlist)
    try:
        result = subprocess.check_output(cmdlist, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print("error on adj volume")
        return False
    return True

def run_cmd(cmdstr, errorstr):
    try:
        result = subprocess.check_output(cmdstr, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(errorstr)
        return False
    return True

def remove_tmp_dir_audiofiles(tmp_dir):
    remove_file(tmp_dir+'/ch0.wav')
    remove_file(tmp_dir+'/ch1.wav')
    
def rename_file(orgfile, newfile):
    tmplist='ren "'+orgfile+'" "'+newfile+'"'
    cmdlist=tmplist.replace('/','\\')
    run_cmd(cmdlist, "error on rename file:"+cmdlist)

def remove_file(infile):
    tmplist='del "'+infile+'"'
    cmdlist=tmplist.replace('/','\\')
    run_cmd(cmdlist, "error on remove file:"+cmdlist)

'''
    volume_normalize : this function will calculate
        the replaygain of non-vocal(kara) stream.
        1. replaygain is within Maximum gain :
           rename the file name directly with _gnXXX XXX=000-999
           XXX value is for another program to set default volume
           in KTV database
        2. replaygain is larger than Maximum gain and adjustable
           the program will try to adjust volume to replaygain level.
           The original file will be prefixed with _ORG_,
           and the new file with new volume level will be generated
        3. replaygain is too large even maximum gain is applied
           the file will be prefixed with _ERR_
        
'''
def volume_normalize(dirpath, filename, fileext, GnMax):
    fullpath=dirpath+'/'+filename+fileext
   
    if (filename.lower().find('_vr')>0):
        kara_ch=0   # if voice is on RIGHT, kara is on LEFT
    else:
        kara_ch=1
                        
    [audio_no, audio_len]=read_mediainfo(fullpath)
    if audio_no==0:
        print("no audio stream in ",fullpath)
        return ''
    #print(fullpath, GnMax, kara_ch)
    [db, peak]=calculate_replaygain(fullpath, audio_no, kara_ch)
    print('replaygain=', db)
    if db==0.0:
        return ''
    gain=db_to_val(db)
    if (gain>GnMax):
        print("need adjustment")
        if (kara_ch==0):
            ch0_db=db
            ch0_peak=peak
            [ch1_db, ch1_peak]=calculate_replaygain(fullpath, audio_no, 1)
        else:
            ch1_db=db
            ch1_peak=peak
            [ch0_db, ch0_peak]=calculate_replaygain(fullpath, audio_no, 0)
            
        [need_adj, ch0_adj, ch1_adj] = determine_adj_db(kara_ch, GnMax, ch0_db, ch1_db, ch0_peak, ch1_peak)
        if not need_adj:
            print("ERR : cannot find suitable volume !!! ch0=", ch0_adj, "ch1=", ch1_adj,"\n")
            err_filename='_ERR0_'+filename+fileext
            rename_file(fullpath, err_filename)  # rename the file with '_ERR_"
            return ''
        org_filename='_ORG_'+filename+fileext
        org_fullpath=dirpath+'/'+org_filename
        
        rename_file(fullpath, org_filename) # rename orginal file with '_ORG_'
        print("rename ",fullpath," into ", org_filename)
        if not adj_volume(org_fullpath, fullpath, audio_no, ch0_adj, ch1_adj):
            rename_file(org_fullpath, '_ERR1'+org_filename)
            return ''
        [db, peak]=calculate_replaygain(fullpath, audio_no, kara_ch)
        gain=db_to_val(db)
        if (gain>GnMax):
            print("Error : after adjustment, the gain ",gain,"is still over Max",GnMax)
            rename_file(org_fullpath, '_OVR'+org_filename)
            # the final file existed, just accept it and append gain value to filename
        
    gain_str=str(int(100*gain)).zfill(3)
    new_filename=filename+'_gn'+gain_str+fileext
    rename_file(fullpath, new_filename)
    print("rename ", fullpath, " into ", new_filename)
    
    return gain_str
