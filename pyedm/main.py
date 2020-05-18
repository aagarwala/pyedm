from mutagen.easyid3 import EasyID3
from mutagen import MutagenError
import os 
import click
from requests_html import HTMLSession
import webbrowser

@click.command()
@click.option("--show-tags", is_flag=True, help="get tag of a song")
@click.option("--get-tags", is_flag=True, help="get tag of a song")
@click.argument("filename")
def cli(show_tags, get_tags, filename):
    if show_tags:
        try:
            audiofile = EasyID3(filename)
            if "title" in audiofile:
                click.echo("Title: {}".format(", ".join(audiofile["title"])))
            if "artist" in audiofile:
                click.echo("Artist: {}".format(", ".join(audiofile["artist"])))
            if "album" in audiofile:
                click.echo("Album: {}".format(", ".join(audiofile["album"])))
            if "genre" in audiofile:
                click.echo("Genre: {}".format(", ".join(audiofile["genre"])))
            if "bpm" in audiofile:
                click.echo("BPM: {}".format(", ".join(audiofile["bpm"])))
        except IOError as e:
            click.echo("File unable to be found {}".format(e))
    elif get_tags:
        audiofile = EasyID3(filename)
        # get_song_webpage(filename.split(".mp3")[0])
        get_song_webpage("{} {}".format(", ".join(audiofile["title"]), ", ".join(audiofile["artist"])), filename)

def get_song_webpage(song_info, filename):
    print(song_info)
    session = HTMLSession()
    r = session.get('https://www.beatport.com/search/tracks?q={}&per-page=25'.format(song_info.replace(" ", "%20")))
    search_results = r.html.find('.bucket-item')
    results_map = {}
    
    click.echo()

    with click.progressbar(search_results) as bar:
        for i, result in enumerate(bar):
            # find titles and/or remix
            primary_title = result.find('.buk-track-primary-title', first=True).text
            secondary_title = result.find('.buk-track-remixed', first=True).text
            full_title = "{} ({})".format(primary_title, secondary_title)

            # find artists
            artists = result.find('.buk-track-artists')
            artist_list = []
            for artist in artists:
                artist_list.append(artist.text)
            artist_list = ", ".join(artist_list)

            label = result.find('.buk-track-labels', first=True).text
            genre = result.find('.buk-track-genre', first=True).text
            release_date = result.find('.buk-track-released', first=True).text
            url = list(result.find('.buk-track-title', first=True).absolute_links)[0]
            results_map[i] = Song(full_title, artist_list, url)

            click.echo("{}. Title: {} | Artist: {} | Label: {} | Genre: {} | Released: {}".format(i, full_title, artist_list, label, genre, release_date))
    
    click.echo()
    song_choice = click.prompt('Please enter the song number that looks correct', type=int)
    click.echo()
    
    if song_choice not in results_map:
        click.echo("Sorry that's not a choice")
        return

    print("Title: {} Artist: {}".format(results_map[song_choice].title, results_map[song_choice].artist_list))

    if click.confirm('Open webpage first?'):
        webbrowser.open(results_map[song_choice].url)

    if click.confirm('Do you want to tag the file?'):
        song_to_tag = get_song_info(results_map[song_choice])
        song_to_tag.print_song_info()
        tag_song(song_to_tag, filename)

def get_song_info(song):
    session = HTMLSession()
    r = session.get(song.url)
    
    info_items = r.html.find('.interior-track-content-list')[0]
    
    length = info_items.find('.interior-track-length', first=True).find('.value', first=True).text
    released_date = info_items.find('.interior-track-released', first=True).find('.value', first=True).text
    bpm = info_items.find('.interior-track-bpm', first=True).find('.value', first=True).text
    genre = info_items.find('.interior-track-genre', first=True).find('.value', first=True).text
    labels_element = info_items.find('.interior-track-labels', first=True).find('.value')
    labels_list = []

    for l in labels_element:
        labels_list.append(l.text)

    labels = ", ".join(labels_list)
    
    song_to_tag = Song(song.title, song.artist_list, song.url)
    song_to_tag.labels = labels
    song_to_tag.genre = genre
    song_to_tag.release_date = released_date
    song_to_tag.bpm = int(bpm)
    song_to_tag.length = length

    return song_to_tag

def tag_song(song_to_tag, song_file_path):
    audiofile = EasyID3(song_file_path)
    
    audiofile["title"] = [song_to_tag.title]
    audiofile["artist"] = song_to_tag.artist_list
    audiofile["genre"] = [song_to_tag.genre]
    audiofile["bpm"] = [song_to_tag.bpm]
    
    audiofile.save()

class Song:
    def __init__(self, title, artist_list, url):
        self.title = title
        self.artist_list = artist_list
        self.labels = ""
        self.genre = ""
        self.release_date = ""
        self.url = url
        self.length = ""
        self.bpm = ""
    
    def print_song_info(self):
        click.echo("Title: {} | Artist: {} | Label: {} | BPM: {} | Genre: {} | Released: {}".format(self.title, self.artist_list, self.labels, self.bpm, self.genre, self.release_date))