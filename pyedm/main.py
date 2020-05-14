import eyed3
import os 
import click
from requests_html import HTMLSession

@click.command()
@click.option("--show-tags", is_flag=True, help="get tag of a song")
@click.option("--get-tags", is_flag=True, help="get tag of a song")
@click.argument("filename")
def cli(show_tags, get_tags, filename):
    if show_tags:
        try:
            audiofile = eyed3.load(filename)
            click.echo("Title: {}".format(audiofile.tag.title))
            click.echo("Artist: {}".format(audiofile.tag.artist))
            click.echo("Album: {}".format(audiofile.tag.album))
            click.echo("Genre: {}".format(audiofile.tag.genre))
            click.echo("BPM: {}".format(audiofile.tag.bpm))
        except IOError as e:
            click.echo("File unable to be found {}".format(e))
    elif get_tags:
        get_song_webpage(filename.split(".mp3")[0])

def get_song_webpage(song_info):
    session = HTMLSession()
    r = session.get('https://www.beatport.com/search/tracks?q={}'.format(song_info.replace(" ", "%20")))
    search_results = r.html.find('.bucket-item')
    
    for i, result in enumerate(search_results):
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

        click.echo("{}. Title: {} | Artist: {} | Label: {} | Genre: {} | Released: {}".format(i, full_title, artist_list, label, genre, release_date))