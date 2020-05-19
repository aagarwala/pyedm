from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen import MutagenError
import os 
import click
from requests_html import HTMLSession
import webbrowser

@click.command()
@click.option("--show-tags", is_flag=True, help="get tags of a song")
@click.option("--get-tags", is_flag=True, help="set tags of a song")
@click.argument("filename")
def cli(show_tags, get_tags, filename):
    if show_tags:
        try:
            audiofile = ID3(filename)
            print(audiofile.pprint())
        except IOError as e:
            click.echo("File unable to be found {}".format(e))
    elif get_tags:
        audiofile = EasyID3(filename)
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
        #song_to_tag.print_song_info()
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

    # if theres an ablum
    album_url = list(r.html.find('.interior-track-releases', first=True).find('.interior-track-release-artwork-link',first=True).absolute_links)[0]
    album_page = session.get(album_url)
    album_page_info = album_page.html.find('.interior-release-chart-content', first=True)
    album_name = album_page_info.find('h1', first=True).text
    
    song_to_tag = Song(song.title, song.artist_list, song.url)
    song_to_tag.labels = labels
    song_to_tag.genre = genre
    song_to_tag.release_date = released_date
    song_to_tag.bpm = int(bpm)
    song_to_tag.length = length
    song_to_tag.album_name = album_name

    return song_to_tag

def tag_song(song_to_tag, song_file_path):
    audiofile = EasyID3(song_file_path)
    EasyID3.RegisterTextKey("contentgroupdescription", "GRP1")

    audiofile["title"] = song_to_tag.title
    audiofile["artist"] = song_to_tag.artist_list
    audiofile["genre"] = [song_to_tag.genre]
    audiofile["bpm"] = [song_to_tag.bpm]
    audiofile["album"] = [song_to_tag.album_name]
    audiofile["contentgroupdescription"] = [song_to_tag.labels]

    click.clear()
    click.echo("New song data:\n")
    click.echo(audiofile.pprint())
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
        self.album_name = ""
    
    def print_song_info(self):
        click.echo("Title: {} | Artist: {} | Label: {} | BPM: {} | Genre: {} | Released: {} | Album: {}".format(self.title, self.artist_list, self.labels, self.bpm, self.genre, self.release_date, self.album_name))