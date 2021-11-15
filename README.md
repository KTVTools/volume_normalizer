# volume_normalizer

這個程式是搭配 Crazy KTV 點歌程式, 調整適當音量, 讓每首歌曲在播放時,
音量都根據 replaygain 的 -89dB 播放, 音量就不會有的歌曲太大聲, 有的太小聲.

本程式為 KTV Tools 中最後一階段的工具程式. 在此程式之前,   
需要利用 [Vocal Channel Analyzer](https://github.com/KTVTools/Vocal-Channel-Analyzer)   
先將每首歌曲的人聲/伴奏聲道判斷出來, 再利用此程式,   
計算伴奏聲道的 replaygain 值, 如果聲音太小聲,   
就會重新將聲音的部分, 調整音量後, 重新再壓縮回原始的 KTV 檔.   
有經過調整音量後的檔案, 雖然聲音會比較正常, 但是因為重新壓縮後,   
音質也會稍微損失一點.   

音量的設定方面, 一個常用的設定方式為, 將每首歌曲的預設音量(基準值),   
在 CrazyKTV 中設為 50%   
- 如果歌曲太小聲, 需要調整的幅度為原音量的兩倍以上,
  就會導致音量破 100%, 對於這種歌曲, 就需要重新調整
  原始 KTV 檔中的音軌, 需要重新壓縮檔案
- 如果歌曲太小聲, 但是需要調整的幅度在 1-2倍之間,
  這樣只要設定這首歌曲在 CrazyKTV 播放時的預設音量,
  介於 50%-100% 之間, 利用 CrazyKTV 幫我們放大音量,
  原始檔案就免調音量
- 如果音量太大聲, 需要調整為原音量的 0.99-0.02 之間,
  只要設定這首歌在 CrazyKTV 播放時的預設音量,
  介於 1%-49% 之間, 就可以讓 CrazyKTV 幫我們降低音量,
  原始檔案不需要重新壓縮
  
所以有兩個設定值需要訂定,   
一個是 CrazyKTV 中每首歌曲的預設音量(基準值),    
另一個是若音量太小, 需要調高音量超過幾倍時, 就要重新壓縮音軌,   
通常有兩套設定值, 一個是音量基準值 50, 原始檔免調音量最高倍數 2 倍.   
或者是音量基準值 40, 原始檔免調音量最高倍數 2.5 倍.   

原始檔免調音量倍數值, 會在第一階段, 若是計算出來每首歌需調音量值,   
超過免調音量值時, 就會重新調整音軌音量, 處理完畢之後, 每首歌曲的檔名,    
會加上 _gnXXX 的字串, XXX 的數值, 就是這首歌曲相對於   
-89dB 的標準音量, 需要調大/調小聲的比例值, XXX數值在 999-001,   
代表音量需要調整的倍數是 9.99 - 0.01 倍,   
如果音量需要調整的倍數, 設定在 2.0 倍的話,   
處理後的 _gnXXX 的數值, 就會在 200-001 之間.   

![image](https://github.com/KTVTools/volume_normalizer/blob/main/screenshot1.png)

[來源目錄] : 設定 KTV 歌曲所在的目錄   
[免調音量最大增益值] : 超過此增益值的倍數, 就會重新壓縮音軌調音量   
[略過已有 _gn 檔案] : 若檔名已經有 _gn 的字串, 就不處理此檔案   

![image](https://github.com/KTVTools/volume_normalizer/blob/main/screenshot2.png)
此頁開始處理音量掃描/調整

![image](https://github.com/KTVTools/volume_normalizer/blob/main/screenshot3.png)
音量基準值的設定, 會在此階段使用到. 在經過前一階段,   
已經處理完所有檔案, 檔名都有 _gnXXX 的部分. 此階段,要將每首歌預設音量結果   
設定到  CrazyKTV 的 CrazySong.mdb 的資料庫檔中, 每首歌曲在資料庫中的   
預設音量, 會是  ___預設音量基準值 * (XXX/100)___  
[資料庫檔案] : CrazyKTV 資料庫檔案   
[預設音量基準] : 音量基準值   


如果執行時, 沒有安裝 Microsoft Access database driver, 會無法開啟 .mdb 檔案,
可以到 https://www.microsoft.com/zh-tw/download/details.aspx?id=13255
安裝 driver
