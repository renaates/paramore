import argparse
import json
import socket
import lyricsgenius
import math
import pandas as pd
import re
import requests
from lyricsgenius.types import Song
from local import *

ALBUMS = [
    "All We Know Is Falling",
    "All We Know Is Falling (10th Anniversary Edition)",
    "Riot!",
    "RIOT! (Deluxe Version)",
    "RIOT! (International Deluxe Version)",
    "Riot! (Hot Topic Exclusive)",
    "The B-Sides",
    "Twilight (Original Motion Picture Soundtrack)",
    "brand new eyes",
    "brand new eyes (Deluxe Version)",
    "brand new eyes (International Edition)",
    "Singles Club",
    "The Sims 2 (Soundtrack)",
    "Paramore",
    "Paramore (Deluxe Edition)",
    "After Laughter",
    "This Is Why",
    "Re: This Is Why",
]

# Songs that don't have an album
OTHER_SONGS = [
    "",
]

# Songs for which there is trouble retrieving them
EXTRA_SONG_API_PATHS = {
    # Decoy
    "/songs/189824": "Riot! (Hot Topic Exclusive)",
}

# Songs that are somehow duplicates / covers / etc.
IGNORE_SONGS = [
    "Hallelujah (Demo)",
    "Oh Star (Demo)",
    "Stuck On You",
    "Running Out of Time (Re: Panda Bear)",
    "The News (Re: The Linda Lindas)",
    "Thick Skull (Re: Julien Baker)",
    "This Is Why (Re: Foals)",
    "You First (Re: Remi Wolf)",
    "Running Out of Time (Re: Zane Lowe)",
    "Big Man, Little Dignity (Re: DOMi & JD BECK)",
    "Crave (Re: Claud)",
    "C’est Comme Ça (Re: Wet Leg)",
    "Figure 8 (Re: Bartees Strange)",
    "Liar (Re: Romy)",
]

ARTIST_ID = 22531
API_PATH = "https://api.genius.com"
ARTIST_URL = API_PATH + "/artists/" + str(ARTIST_ID)
CSV_PATH = "songs.csv"
LYRIC_PATH = "lyrics.csv"
LYRIC_JSON_PATH = "lyrics.json"
SONG_LIST_PATH = "song_titles.txt"


def main():
    parser = argparse.ArgumentParser()
    # Only look for songs that aren't already existing
    parser.add_argument("--append", action="store_true")
    # Append songs specifically in EXTRA_SONG_API_PATHS
    parser.add_argument("--appendpaths", action="store_true")
    args = parser.parse_args()
    existing_df, existing_songs = None, []
    if args.append or args.appendpaths:
        existing_df = pd.read_csv(CSV_PATH)
        existing_songs = list(existing_df["Title"])
    genius = lyricsgenius.Genius(access_token)
    songs = get_songs() if not args.appendpaths else []
    songs_by_album, has_failed, last_song = {}, True, ""
    while has_failed:
        songs_by_album, has_failed, last_song = sort_songs_by_album(
            genius, songs, songs_by_album, last_song, existing_songs
        )
    albums_to_songs_csv(songs_by_album, existing_df)
    songs_to_lyrics()
    lyrics_to_json()


def get_songs():
    print("Getting songs...")
    songs = []
    next_page = 1
    while next_page != None:
        request_url = ARTIST_URL + "/songs?page=" + str(next_page)
        r = requests.get(
            request_url, headers={"Authorization": "Bearer " + access_token}
        )
        song_data = json.loads(r.text)
        songs.extend(song_data["response"]["songs"])
        next_page = song_data["response"]["next_page"]
    returned_songs = []
    for song in songs:
        if (
            song["primary_artist"]["id"] == ARTIST_ID
            and "Live" not in song["title"]
            and "Remix" not in song["title"]
            and "Acoustic" not in song["title"]
            or song["title"] in OTHER_SONGS
        ):
            returned_songs.append(song)
    return returned_songs


def sort_songs_by_album(genius, songs, songs_by_album, last_song, existing_songs=[]):
    def get_song_data(api_path):
        request_url = API_PATH + api_path
        r = requests.get(
            request_url, headers={"Authorization": "Bearer " + access_token}
        )
        response_data = json.loads(r.text)
        if "response" in response_data and "song" in response_data["response"]:
            return response_data["response"]["song"]
        else:
            return None

    def clean_lyrics_and_append(song_data, album_name, lyrics, songs_by_album):
        cleaned_lyrics = clean_lyrics(lyrics)
        s = Song(genius, song_data, cleaned_lyrics)
        if album_name not in songs_by_album:
            songs_by_album[album_name] = []
        songs_by_album[album_name].append(s)

    print("Sorting songs by album...")
    songs_so_far = []
    for song in songs:
        lyrics = None
        if (
            song["title"] > last_song
            and song["title"] not in existing_songs
            and song["title"] not in IGNORE_SONGS
        ):
            try:
                song_data = get_song_data(song["api_path"])
                if (
                    song_data is not None
                    and "album" in song_data
                    and song_data["lyrics_state"] == "complete"
                ):
                    album_name = (
                        song_data["album"]["name"].strip()
                        if song_data["album"]
                        else None
                    )
                    if album_name is None:
                        album_name = ""
                    lyrics = genius.lyrics(song_id=song_data["id"])
                    # Ensure that there are lyrics
                    if (
                        lyrics
                        and has_song_identifier(lyrics)
                        and (album_name or (song["title"] in OTHER_SONGS))
                    ):
                        songs_so_far.append(song["title"])
                        clean_lyrics_and_append(
                            song_data, album_name, lyrics, songs_by_album
                        )
                        print(song_data["title"])
                        print(song_data["album"]["name"].strip())
            except (requests.exceptions.Timeout, socket.timeout) as e:
                print("Failed receiving song", song["title"], "-- saving songs so far")
                return songs_by_album, True, song["title"]

    for api_path in EXTRA_SONG_API_PATHS:
        song_data = get_song_data(api_path)
        if (
            song_data is not None
            and song_data["title"] not in existing_songs
            and song_data["title"] not in songs_so_far
        ):
            lyrics = genius.lyrics(song_id=song_data["id"])
            album_name = EXTRA_SONG_API_PATHS[api_path]
            clean_lyrics_and_append(song_data, album_name, lyrics, songs_by_album)

    return songs_by_album, False, ""


def albums_to_songs_csv(songs_by_album, existing_df=None):
    print("Saving songs to CSV...")
    songs_records = []
    songs_titles = []
    for album in songs_by_album:
        if album in ALBUMS:
            for song in songs_by_album[album]:
                if song.title not in IGNORE_SONGS and song.title not in songs_titles:
                    record = {
                        "Title": song.title.strip("\u200b"),
                        "Album": album if "Lover (Target" not in album else "Lover",
                        "Lyrics": song.lyrics,
                    }
                    songs_records.append(record)
                    songs_titles.append(song.title)
        else:
            for song in songs_by_album[album]:
                if song in OTHER_SONGS and song.title not in songs_titles:
                    record = {
                        "Title": song.title,
                        "Album": album,
                        "Lyrics": song.lyrics,
                    }
                    songs_records.append(record)
                    songs_titles.append(song.title)

    song_df = pd.DataFrame.from_records(songs_records)
    if existing_df is not None:
        existing_df = existing_df[existing_df["Album"].isin(ALBUMS)]
        song_df = pd.concat([existing_df, song_df])
        song_df = song_df[~song_df["Title"].isin(IGNORE_SONGS)]
        song_df = song_df.drop_duplicates("Title", keep="last")
        print(song_df)
    song_df.to_csv(CSV_PATH, index=False)


def has_song_identifier(lyrics):
    if "[Intro" in lyrics or "[Verse" in lyrics or "[Chorus" in lyrics:
        return True
    return False


class Lyric:
    def __init__(self, lyric, prev_lyric=None, next_lyric=None):
        self.lyric = lyric
        self.prev = prev_lyric
        self.next = next_lyric

    def __eq__(self, other):
        return (
            self.lyric == other.lyric
            and self.prev == other.prev
            and self.next == other.next
        )

    def __repr__(self):
        return self.lyric

    def __hash__(self):
        return hash((self.prev or "") + self.lyric + (self.next or ""))


def songs_to_lyrics():
    print("Generating lyrics CSV...")
    song_data = pd.read_csv(CSV_PATH)
    lyric_records = []
    song_titles = []
    for song in song_data.to_records(index=False):
        title, album, lyrics = song
        if title not in song_titles:
            song_titles.append(title)
            lyric_dict = get_lyric_list(lyrics)
            for lyric in lyric_dict:
                lyric_record = {
                    "Song": title,
                    "Album": album,
                    "Lyric": lyric.lyric,
                    "Previous Lyric": lyric.prev,
                    "Next Lyric": lyric.next,
                    "Multiplicity": lyric_dict[lyric],
                }
                lyric_records.append(lyric_record)
    lyric_df = pd.DataFrame.from_records(lyric_records)
    lyric_df.to_csv(LYRIC_PATH, index=False)
    # Writing song list to make it easy to compare changes
    with open(SONG_LIST_PATH, "w") as f:
        f.write("\n".join(sorted(set(song_titles))))
        f.close()


def get_lyric_list(lyrics):
    line = None
    lines = lyrics.split("\n")
    lyric_dict = {}
    for i in range(len(lines)):
        curr_line = lines[i].strip()
        if len(curr_line) > 0 and curr_line[0] != "[":
            prev_line = line
            line = curr_line
            next_line = (
                lines[i + 1]
                if i + 1 < len(lines)
                and len(lines[i + 1]) > 0
                and lines[i + 1][0] != "["
                else None
            )
            lyric = Lyric(line, prev_line, next_line)
            if lyric not in lyric_dict:
                lyric_dict[lyric] = 1
            else:
                lyric_dict[lyric] = lyric_dict[lyric] + 1
        # If there is a chorus / etc. indicator then set current line to "None"
        # if the previous line was not already set
        elif line is not None:
            line = None
    return lyric_dict


def lyrics_to_json():
    print("Generating lyrics JSON...")
    lyric_dict = {}
    lyric_data = pd.read_csv(LYRIC_PATH)
    for lyric in lyric_data.to_records(index=False):
        title, album, lyric, prev_lyric, next_lyric, multiplicity = lyric
        if album != album:  # handling for NaN
            album = title
        if album not in lyric_dict:
            lyric_dict[album] = {}
        if title not in lyric_dict[album]:
            lyric_dict[album][title] = []
        lyric_dict[album][title].append(
            {
                "lyric": lyric,
                "prev": "" if prev_lyric != prev_lyric else prev_lyric,  # replace NaN
                "next": "" if next_lyric != next_lyric else next_lyric,
                "multiplicity": int(multiplicity),
            }
        )
    lyric_json = json.dumps(lyric_dict, indent=4)
    with open(LYRIC_JSON_PATH, "w") as f:
        f.write(lyric_json)
        f.close()


def clean_lyrics(lyrics: str) -> str:
    # Remove first line (title + verse line)
    lyrics = lyrics.split(sep="\n", maxsplit=1)[1]
    # Replace special quotes with normal quotes
    lyrics = re.sub(r"\u2018|\u2019", "'", lyrics)
    lyrics = re.sub(r"\u201C|\u201D", '"', lyrics)
    # Replace special unicode spaces with standard space
    lyrics = re.sub(
        r"[\u00A0\u1680​\u180e\u2000-\u2009\u200a​\u200b​\u202f\u205f​\u3000]",
        " ",
        lyrics,
    )
    # Replace dashes with space and single hyphen
    lyrics = re.sub(r"\u2013|\u2014", " - ", lyrics)
    # Replace hyperlink text
    lyrics = re.sub(r"[0-9]*URLCopyEmbedCopy", "", lyrics)
    lyrics = re.sub(r"[0-9]*Embed", "", lyrics)
    lyrics = re.sub(r"[0-9]*EmbedShare", "", lyrics)
    lyrics = re.sub(
        r"See [\w\s]* LiveGet tickets as low as \$\d*You might also like", "\n", lyrics
    )

    return lyrics


if __name__ == "__main__":
    main()