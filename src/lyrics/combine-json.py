import json
import os

# Get the current directory of the script
script_directory = os.path.dirname(os.path.abspath(__file__))

# Construct the file paths using the script's directory
file_path_1 = os.path.join(script_directory, 'lyrics.json')
file_path_2 = os.path.join(script_directory, 'lyrics-hw.json')

# Read the contents of the first JSON file
with open(file_path_1, 'r', encoding='utf-8') as file:
    lyrics_data_1 = json.load(file)

# Read the contents of the second JSON file
with open(file_path_2, 'r', encoding='utf-8') as file:
    lyrics_data_2 = json.load(file)

# Merge the data from both files
combined_lyrics_data = {**lyrics_data_1, **lyrics_data_2}

# Sort the data by album and song names
sorted_lyrics_data = {}
for album in sorted(combined_lyrics_data.keys()):
    sorted_album_data = {}
    for song in sorted(combined_lyrics_data[album].keys()):
        sorted_album_data[song] = combined_lyrics_data[album][song]
    sorted_lyrics_data[album] = sorted_album_data

# Write the sorted data to a new JSON file
with open('combined_lyrics.json', 'w', encoding='utf-8') as file:
    json.dump(sorted_lyrics_data, file, ensure_ascii=False, indent=4)

print("Combined lyrics data has been saved to 'combined_lyrics.json'.")
