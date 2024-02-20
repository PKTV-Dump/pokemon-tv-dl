import httplib2
import json
import os
import re
import sys
from tqdm import tqdm
import urllib.request

# Pokémon TV Ripper
# instructions:
# install requirements
# pip install httplib2
# pip install tqdm
# clone https://github.com/seiya-dev/pokemon-tv/tree/master and put this script in the root directory
# run the script, select your language
# on the second argument you can type all, seasons, movies, generations, poketoon and also a specific movie or season
# if a download gets stucks then close terminal and retry
# tested with python version 3.10.4

argc = len(sys.argv)
databasedir = "database"
outdir = "Downloads"
langs = os.listdir(databasedir)
types = [ # TODO: expand
    "series",
    "movies",
    "generations",
    "poketoon"
]
extensions = [ # NOTE: might need to be expanded
    ".mp4", # used for the majority of files
    ".mov", # seen in some pokémon generations files
    ".flv"  # i don't remember if/where this one was used
]

def sanitize_filename(filename):
    bad_chars = [
        ":", "*", "?", "<", ">", "|", "/", f"\"" # probably incomplete
    ]
    for bad_char in bad_chars:
        filename = filename.replace(bad_char, "")

    return filename

def createDirectory(path : str):
    if(os.path.isdir(path) == False):
        os.mkdir(path)

def getPlaylistJSON(mediaID : str, type : str): # mobile playlist or rtmp playlist
    with urllib.request.urlopen(f"https://production-ps.lvp.llnw.net/r/PlaylistService/media/{mediaID}/{type}") as url:
        return json.load(url)

def checkUrlOK(url : str):
    h = httplib2.Http()
    resp = h.request(url, 'HEAD')
    return int(resp[0]['status']) < 400

class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)

def download_url(url, output_path):
    url = url.replace("http://", "https://")
    with DownloadProgressBar(unit='B', unit_scale=True,
                             miniters=1, desc=url.split('/')[-1]) as t:
        urllib.request.urlretrieve(url, filename=output_path, reporthook=t.update_to)

def downloadVideo(mediaID : str, epNo : str, sNo : str, title : str, seasonName : str):
    mobilePlaylist = getPlaylistJSON(mediaID, "getMobilePlaylistByMediaId")
    list = mobilePlaylist["mediaList"][0]
    urls = list["mobileUrls"]

    # High quality WEB-DL
    for url in urls:
        if url["targetMediaPlatform"] == "HttpLiveStreaming":
            m3u8link : str = url["mobileUrl"] 
            for ext in extensions: 
                dl = m3u8link[:-46] + ext
                if checkUrlOK(dl) == True: # remove m3u8 and ID and add the extension, if url exists then download file
                    print(dl)
                    if(len(sNo) < 1):
                        if len(epNo) < 1: # movies and pokemon generations don't have a season number or episode number defined
                            filename = f"{outdir}/{title}{ext}"
                        else:
                            episodeNo = int(epNo)
                            filename = f"{seasonName} - {outdir}/E{episodeNo:02} - {title}{ext}"
                    else:
                        seasonNo = int(sNo)
                        episodeNo = int(epNo)
                        filename = f"{outdir}/Season {seasonNo:02}/{seasonName} - S{seasonNo:02}E{episodeNo:02} - {title}{ext}"
                    
                    if(os.path.exists(filename)):
                        return
                    
                    print(f"Downloading {title} (WEB-DL)")
                    download_url(dl, filename)
                    return
    
    # if there's no master video, download highest quality rtmp stream
    rtmpPlaylist = getPlaylistJSON(mediaID, "getPlaylistByMediaId")
    streams = rtmpPlaylist["playlistItems"][0]["streams"]
    for stream in streams:
        if stream["videoBitRate"] == 1600.0:
            streamUrl = stream["url"]
            strippedLink = streamUrl[42:] # strip first 42 characters to be concatenated with the next string, resulting in a normal URL to a downloadable video
            videoLink = f"https://s2.content.video.llnw.net/{strippedLink}"

            if(len(sNo) < 1):
                if len(epNo) < 1: # movies don't have a season number or episode number defined
                    filename = f"{outdir}/{title}.mp4"
                else:
                    episodeNo = int(epNo)
                    filename = f"{seasonName} - {outdir}/E{episodeNo:02} - {title}.mp4"
            else:
                seasonNo = int(sNo)
                episodeNo = int(epNo)
                filename = f"{outdir}/Season {seasonNo:02}/{seasonName} - S{seasonNo:02}E{episodeNo:02} - {title}.mp4"
            
            if(os.path.exists(filename)):
                return
                             
            print(f"Downloading {title} via RTMP")
            download_url(videoLink, filename)
            return
    print("Failed to download file.")

def downloadEpisodes(path : str):
    f = open(path, encoding="utf-8")
    data = json.load(f)
    seasonName = sanitize_filename(data["channel_name"])
    season = data["media"][0]["season"]
    if(season != ""):
        s = int(season)
        createDirectory(f"{outdir}/Season {s:02}")

    for i in range(len(data["media"])): # loop through all media in the list
        mediaData = data["media"][i]
        mediaID = mediaData["id"]
        epNum = mediaData["episode"]
        sNum = mediaData["season"]
        title = sanitize_filename(mediaData["title"]) # remove bad characters from title
        downloadVideo(mediaID, epNum, sNum, title, seasonName)

def startDownload(type : str, lang : str):
    for f in os.listdir(f"{databasedir}/{lang}/"):
        if(f.__contains__(type)):
            downloadEpisodes(f"{databasedir}/{lang}/{f}")

print(langs)
lang = input("Select Language: ")
print(os.listdir(f"{databasedir}/{lang}"))
type = input("select what to rip: ")
createDirectory(outdir)

if(type == "all"):
    for t in types:
        startDownload(t, lang)
else:
    startDownload(type, lang)
    