import eyed3
import os 
import click

@click.command()
@click.option("--get-tag", is_flag=True, help="get tag of a song")
@click.argument("filename")
def cli(get_tag, filename):
    if get_tag:
        try:
            audiofile = eyed3.load(filename)
            click.echo("Title: {}".format(audiofile.tag.title))
            click.echo("Artist: {}".format(audiofile.tag.artist))
            click.echo("Album: {}".format(audiofile.tag.album))
            click.echo("Genre: {}".format(audiofile.tag.genre))
            click.echo("BPM: {}".format(audiofile.tag.bpm))
        except IOError as e:
            click.echo("File unable to be found {}".format(e))