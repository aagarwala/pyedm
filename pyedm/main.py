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

            results_map[i] = Song(full_title, artist_list, label, genre, release_date)

            click.echo("{}. Title: {} | Artist: {} | Label: {} | Genre: {} | Released: {}".format(i, full_title, artist_list, label, genre, release_date))
    click.echo('Type a number for the song that looks correct', nl=False)
    c = click.getchar()
    click.echo()

    # do some checking to make sure its not some weird character the user inputted
    if c.isdigit():
        c = int(c)
        click.echo()
        click.echo("Excellent! Adding tags to the song choice:")
        results_map[c].print_song_info()

        #TODO: click the link of that particular song, get the full data
    else:
        click.echo()
        click.echo("Sorry, you did not enter a number")

class Song:
    def __init__(self, title, artist_list, label, genre, release_date):
        self.title = title
        self.artist_list = artist_list
        self.label = label
        self.genre = genre
        self.release_date = release_date
    
    def print_song_info(self):
        click.echo("Title: {} | Artist: {} | Label: {} | Genre: {} | Released: {}".format(self.title, self.artist_list, self.label, self.genre, self.release_date))