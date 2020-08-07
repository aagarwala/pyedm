from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
from mutagen import MutagenError
import os 
import click
from requests_html import HTMLSession
import webbrowser
import re
import time
import datetime
import requests

SKIP_FOLDER = ["Music", "iTunes", "AAnster"]

lookback_description = """amount of days to cover tagging from current time. pyedm looks back exactly that many days (at most),
and stops if it goes past that number or if it reaches MAX_SONGS, whichever comes first. Default is 1 day"""

@click.command()
# @click.option("--show-tags", is_flag=True, help="get tags of a song")
# @click.option("--get-tags", is_flag=True, help="get tags from beatport so you can set them")
@click.option("-L", "--lookback", default=1, type=int, help=lookback_description)
@click.option("-N", "--no_confirmation", is_flag=True, help="if this option is set, then there is no confirmation on tagging a song")
@click.argument("max_songs")
@click.argument("music_library_path", envvar='PYEDM_LIB_PATH')
def cli(show_tags, lookback, no_confirmation, max_songs, music_library_path):
    """
    \\\\ Introduction \\\\

        This is a handy tool for quickly tagging all your recent downloaded tracks from beatport

    \\\\ Arguments documentation \\\\

        MAX_SONGS: The maximum number of songs you want to tag

        MUSIC_LIBRARY_PATH: The top level location of your music folder. To be defined by the user in command line or set as env PYEDM_LIB_PATH
    """

    def pretty_time(epoch_time):
        """
        small little function that returns a readable date/time string
        """

        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(epoch_time))

    # print(filename)
    # If there is no lookback set to default of 1 day
    if not lookback:
        lookback = 1
    else:
        lookback = int(lookback)
        print("lookback: {}".format(str(lookback)))
    # In order to get the proper lookback in epoch we need to calculate from current time to however many days back
    today = time.time()
    orig = datetime.datetime.fromtimestamp(today)
    # orig = datetime.datetime.fromtimestamp(1594089329.5821078)
    lookback = orig - datetime.timedelta(days=lookback)
    lookback = lookback.timestamp()
    click.echo()
    click.echo("lookback: {} to {}".format(pretty_time(today), pretty_time(lookback)))
    click.echo("music_library_path: {}".format(music_library_path))
    click.echo("max_songs: {}".format(max_songs))
    click.echo()
    max_songs = int(max_songs)

    # if show_tags:
    #     try:
    #         # # Looking through all the possible file names (can drag and drop multiple to cmdline)
    #         # for file in filename:
    #         audiofile = ID3(filename)
    #         print(audiofile.pprint())
    #     except IOError as e:
    #         click.echo("File unable to be found {}".format(e))
    # else:
        # for file in filename:
        # audiofile = EasyID3(file)
        #
        # song = Song("Easy (Extended Mix)", "Autograf feat. Papa Ya", "https://www.beatport.com/track/easy-feat-papa-ya-extended-mix/13113846")
        # song_to_tag = get_song_info(song)
        # tag_song(song_to_tag, "/Users/Anirudh/Music/Autograf/Autograf feat. Papa Ya - Easy (Extended Mix).mp3")

        # Sort the initial music folder path by date modified and make sure the key is passed the absolute path
    list_of_tracks = []
    # import pdb
    # pdb.set_trace()
    list_of_tracks, _ = search_latest(music_library_path, max_songs, lookback, list_of_tracks)
    total_tracks = "\n".join(list_of_tracks)
    click.echo("List of {} tracks to be tagged:".format(len(list_of_tracks)))
    click.echo(total_tracks)
    for track in list_of_tracks:
        audiofile = {}
        match = re.search(r"([^/]*) - (.*)\.mp3", track)
        if match:
            audiofile['artist'] = [match.group(1)]
            audiofile['title'] = [match.group(2)]
            # print(audiofile)
            click.echo()
            click.echo(">>> {} - {} <<<".format(match.group(1), match.group(2)))
            get_song_webpage(", ".join(audiofile["title"]), ", ".join(audiofile["artist"]), track, no_confirmation)

def search_latest(music_library_path, max_songs, lookback, list_of_tracks):
    """
    This takes the music library path and searches recurisvely for the latest max_songs only returning .mp3s
    """

    items = sorted(os.listdir(music_library_path), key=lambda fn:os.path.getmtime(os.path.join(music_library_path, fn)), reverse=True)
    for item in items:
        if not item.startswith(".") and item not in SKIP_FOLDER:
            full_path = os.path.join(music_library_path, item)
            # If the item is a folder search into it
            if os.path.isdir(full_path):
                list_of_tracks, reached_max = search_latest(full_path, max_songs, lookback, list_of_tracks)
                if reached_max:
                    break
            # If the file is an mp3 check if the date is greater than the "oldest date allowed"
            elif full_path.endswith(".mp3") and os.path.getmtime(full_path) >= lookback:
                list_of_tracks.append(full_path)
                if len(list_of_tracks) == max_songs:
                    return list_of_tracks, True

    # You have added as many tracks as you can but not yet reached max (only case though this is not true is the final return, but at that point we dont care
    # it's a throwaway variable)
    return list_of_tracks, False


def get_song_webpage(song_title, song_artist, filename, no_confirmation):
    song_choice = None
    # Put together title and artist for search
    song_info = "{} {}".format(song_title, song_artist)

    # Extract primary title + secondary title without the feat artist
    match = re.search(r"(.*)\s(feat\.|ft\.).*(\(.*)", song_title)
    if match:
        song_title = "{} {}".format(match.group(1), match.group(3))
    # Extract primary title without the feat artist
    match = re.search(r"(.*)\s(feat\.|ft\.)", song_title)
    if match:
        song_title = match.group(1)
    # Extract main artist without the feat artist
    match = re.search(r"(.*)\s(feat\.|ft\.)", song_artist)
    if match:
        song_artist = match.group(1)

    song_artist = song_artist.split(",")
    
    # print(song_info)
    # print(song_title)
    # print(song_artist)
    session = HTMLSession()
    # url = 'https://www.beatport.com/search/tracks?q={}&per-page=25'.format(song_info.replace(" ", "%20").replace("&", ""))
    # print(url)
    r = session.get('https://www.beatport.com/search/tracks?q={}&per-page=25'.format(song_info.replace(" ", "%20").replace("&", "")))
    search_results = r.html.find('.bucket-item')
    # Sort the results by release date as to get the first release (versus re-release)
    search_results.sort(key=lambda x: x.find('.buk-track-released', first=True).text)
    # print(search_results)
    # print(filename)
    results_map = {}
    
    click.echo()

    with click.progressbar(search_results) as bar:
        for i, result in enumerate(bar):
            # find titles and/or remix
            primary_title = result.find('.buk-track-primary-title', first=True).text
            secondary_title = result.find('.buk-track-remixed', first=True).text
            full_title = "{} ({})".format(primary_title, secondary_title)

            # find artists
            artists = result.find('.buk-track-artists')[0].text
            artist_list = artists.split(",")
            # for artist in artists:
            #     artist_list.append(artist.text)
            # artist_list_concat = ", ".join(artist_list)

            label = result.find('.buk-track-labels', first=True).text
            genre = result.find('.buk-track-genre', first=True).text
            release_date = result.find('.buk-track-released', first=True).text
            url = list(result.find('.buk-track-title', first=True).absolute_links)[0]
            # print(url)
            results_map[i] = Song(full_title, artists, url)

            # Get rid of any feat. artist in full title 
            match = re.search(r"(.*)\s(feat\.|ft\.).*(\(.*)", full_title)
            if match:
                stripped_full_title = "{} {}".format(match.group(1), match.group(3))
            else:
                stripped_full_title = full_title

            # import pdb
            # pdb.set_trace()

            def artist_match(song_artist, artist_list):
                """
                quick function to check if any of the artist (if multiple) match with the search result
                """

                for artist in song_artist:
                    if artist.lower() in (x.lower() for x in artist_list):
                        return True

                return False

            # Check to see if song exact match, if so then break from results and automatically choose number
            if song_title.lower() == stripped_full_title.lower() and artist_match(song_artist, artist_list):
                print("*** Song automatically chosen ***")
                song_choice = i
                click.echo()
                click.echo("{}. Title: {} | Artist: {} | Label: {} | Genre: {} | Released: {}".format(i, full_title, artists, label, genre, release_date))
                click.echo()
                break

            click.echo("{}. Title: {} | Artist: {} | Label: {} | Genre: {} | Released: {}".format(i, full_title, artists, label, genre, release_date))
    
    # pdb.set_trace()
    if song_choice is None:
        click.echo()
        song_choice = click.prompt("Please enter the song number that looks correct or enter 's' to skip")
        click.echo()

    if song_choice == 's':
        click.echo("Skipping this song")
        return

    song_choice = int(song_choice)
    if song_choice not in results_map:
        click.echo("Sorry that's not a choice")
        return

    # print("Title: {} Artist: {}".format(results_map[song_choice].title, results_map[song_choice].artist_list))

    # if click.confirm('Open webpage first?'):
    #     webbrowser.open(results_map[song_choice].url)

    # Only ask about tagging file if no_confirmation is not set (default behavior)
    if not no_confirmation:
        if click.confirm('Do you want to tag the file?'):
            song_to_tag = get_song_info(results_map[song_choice])
            #song_to_tag.print_song_info()
            tag_song(song_to_tag, filename)
    else:
        song_to_tag = get_song_info(results_map[song_choice])
        #song_to_tag.print_song_info()
        tag_song(song_to_tag, filename)

def get_song_info(song):
    session = HTMLSession()
    # import pdb
    # pdb.set_trace()
    r = session.get(song.url)
    
    info_items = r.html.find('.interior-track-content-list')[0]
    
    length = info_items.find('.interior-track-length', first=True).find('.value', first=True).text
    released_date = info_items.find('.interior-track-released', first=True).find('.value', first=True).text
    match = re.match(r"(\d+)-(\d+)-(\d+)", released_date)
    if match:
        year = match.group(1)
    bpm = info_items.find('.interior-track-bpm', first=True).find('.value', first=True).text
    genre = info_items.find('.interior-track-genre', first=True).find('.value', first=True).text
    labels_element = info_items.find('.interior-track-labels', first=True).find('.value')
    labels_list = []

    for l in labels_element:
        labels_list.append(l.text)

    labels = ", ".join(labels_list)

    # if theres an album
    album_url = list(r.html.find('.interior-track-releases', first=True).find('.interior-track-release-artwork-link',first=True).absolute_links)[0]
    album_page = session.get(album_url)
    album_page_info = album_page.html.find('.interior-release-chart-content', first=True)
    album_name = album_page_info.find('h1', first=True).text
    # Gets album art
    album_artwork_url = album_page.html.find('.interior-release-chart-artwork-parent', first=True).find('img')[0].attrs['src']
    response = requests.get(album_artwork_url)
    album_artwork = response.content

    # If there are mulitple songs, need to match to right one to get track number / total tracks
    # pdb.set_trace()
    album_tracks = album_page.html.find(".bucket-items", first=True).find(".bucket-item")
    for track in album_tracks:
        # Frist need to compare full title to see which track it is
        primary_title = track.find(".buk-track-title", first=True).find(".buk-track-primary-title", first=True).text
        secondary_title = track.find(".buk-track-title", first=True).find(".buk-track-remixed", first=True).text
        full_title = "{} ({})".format(primary_title, secondary_title)
        if song.title.lower() == full_title.lower():
            track_number = track.find(".bucket-item", first=True).attrs['data-ec-position'] # gets the track number
            break
    track_number = "{}/{}".format(track_number, str(len(album_tracks)))

    song_to_tag = Song(song.title, song.artist_list, song.url)
    song_to_tag.labels = labels
    song_to_tag.genre = genre
    song_to_tag.release_date = released_date
    song_to_tag.bpm = int(bpm)
    song_to_tag.length = length
    song_to_tag.album_name = album_name
    song_to_tag.album_artwork = album_artwork
    song_to_tag.track_number = track_number
    song_to_tag.year = year

    return song_to_tag

def tag_song(song_to_tag, song_file_path):
    # import pdb
    # pdb.set_trace()
    audiofile = EasyID3(song_file_path)
    EasyID3.RegisterTextKey("contentgroupdescription", "GRP1")
    EasyID3.RegisterTextKey("year", "TYER")

    audiofile["title"] = song_to_tag.title
    audiofile["artist"] = song_to_tag.artist_list
    audiofile["genre"] = [song_to_tag.genre]
    audiofile["bpm"] = [song_to_tag.bpm]
    audiofile["album"] = [song_to_tag.album_name]
    audiofile["year"] = song_to_tag.year
    audiofile["tracknumber"] = song_to_tag.track_number
    audiofile["contentgroupdescription"] = [song_to_tag.labels]

    audiofile.save()
    # pdb.set_trace()
    # Need to use ID3 and APIC for saving artwork
    audiofile = ID3(song_file_path)
    # with open('img.jpg', 'rb') as albumart:
    # For artwork you need to restart iTunes (annoying I know) for it to show up
    audiofile.delall("APIC") # Delete every APIC tag (Cover art)
    audiofile.add(APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,
                        desc=u'Cover',
                        data=song_to_tag.album_artwork
                    ))
    audiofile.save()
    # pdb.set_trace()
    # click.clear()
    click.echo("\nNew song data:\n")
    click.echo(audiofile.pprint())
    click.echo("\nTagged from: {}".format(song_to_tag.url))

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
        self.album_artwork = None
        self.track_number = ""
        self.year = ""
    
    def print_song_info(self):
        click.echo("Title: {} | Artist: {} | Label: {} | BPM: {} | Genre: {} | Released: {} | Album: {}".format(self.title, self.artist_list, self.labels, self.bpm, self.genre, self.release_date, self.album_name))
