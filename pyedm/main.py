from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
import os 
import click
from requests_html import AsyncHTMLSession
import re
import time
import datetime
import requests
import json
import asyncio

SKIP_FOLDER = ["Music", "iTunes", "AAnster"]

lookback_description = """amount of days to cover tagging from current time. pyedm looks back exactly that many days (at most),
and stops if it goes past that number or if it reaches MAX_SONGS, whichever comes first. Default is 1 day"""

@click.command()
@click.option("-L", "--lookback", default=1, type=int, help=lookback_description)
@click.option("-N", "--no_confirmation", is_flag=True, help="if this option is set, then there is no confirmation on tagging a song")
@click.argument("max_songs")
@click.argument("music_library_path", envvar='PYEDM_LIB_PATH')
def cli(lookback, no_confirmation, max_songs, music_library_path):
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

    # If there is no lookback set to default of 1 day
    if not lookback:
        lookback = 1
    else:
        lookback = int(lookback)
        print("lookback: {}".format(str(lookback)))
    # In order to get the proper lookback in epoch we need to calculate from current time to however many days back
    today = time.time()
    orig = datetime.datetime.fromtimestamp(today)
    lookback = orig - datetime.timedelta(days=lookback)
    lookback = lookback.timestamp()
    click.echo()
    click.echo("lookback: {} to {}".format(pretty_time(today), pretty_time(lookback)))
    click.echo("music_library_path: {}".format(music_library_path))
    click.echo("max_songs: {}".format(max_songs))
    click.echo()
    max_songs = int(max_songs)

    list_of_tracks = []
    list_of_tracks, _ = search_latest(music_library_path, max_songs, lookback, list_of_tracks)
    total_tracks = "\n".join(list_of_tracks)
    click.echo("List of {} tracks to be tagged:".format(len(list_of_tracks)))
    click.echo(total_tracks)
    # Check to make sure you want to proceed on given songs
    if not click.confirm('Do you want to proceed?'):
        return 0 # exit
    for track in list_of_tracks:
        audiofile = {}
        match = re.search(r"([^/]*) - (.*)\.mp3", track)
        if match:
            audiofile['artist'] = [match.group(1)]
            audiofile['title'] = [match.group(2)]
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
    results_map = {}
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
    
    
    async def scrape_beatport():
        # start async html session
        session = AsyncHTMLSession()
        click.echo('https://www.beatport.com/search/tracks?q={}&per-page=25'.format(song_info.replace(" ", "%20").replace("&", "")))
        r = await session.get('https://www.beatport.com/search/tracks?q={}&per-page=25'.format(song_info.replace(" ", "%20").replace("&", "")))
         # Wait for JavaScript to render
        await r.html.arender()

        # returns the html elements of all the track lists
        tracks = r.html.find('[data-testid="tracks-list-item"]')

        # Extract the JSON data from the HTML
        json_data = None
        json_text = r.html.find('#__NEXT_DATA__', first=True).text
        json_data = json.loads(json_text)

        # Check if JSON data is found
        if json_data is None:
            click.echo("JSON data not found")
            return

         # this returns the list of results (150) we only need first 25
        json_track_results = json_data['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']['data'][0:25]
        click.echo()

        for i, track in enumerate(tracks):
            # Return track url reference
            url_ref = track.find('.Lists-shared-style__MetaRow-sc-b8c20e45-4.bWa-dwr', first=True).find('a', first=True).attrs['href']
            # Create the full url to the track (we will call this later to get more info)
            track_url = "https://www.beatport.com{}".format(url_ref)
            # print(f"Track URL: {track_url}")

            # This gets both the track name as well as the mix name for a full title
            track_name = json_track_results[i]['track_name']
            mix_name = json_track_results[i]['mix_name']
            full_title = "{} ({})".format(track_name, mix_name)

            # This returns a list of the artists
            artist_list = [artist['artist_name'] for artist in json_track_results[i]['artists']]
            # This combines the artist into a string that can be entered when tagging the track later
            artists = ', '.join(artist_list)

            # return the label name
            label = json_track_results[i]['label']['label_name']
            # return just the first genre
            genre = json_track_results[i]['genre'][0]['genre_name']
            release_date = json_track_results[i]['release_date']
            match = re.search(r"(.*)T", release_date)
            if match:
                release_date = match.group(1)
            else:
                click.echo(f"ERROR: Need to fix the regex for release_date: {release_date}")
 
            results_map[i] = Song(full_title, artists, track_url)

            # Get rid of any feat. artist in full title 
            match = re.search(r"(.*)\s(feat\.|ft\.).*(\(.*)", full_title)
            if match:
                stripped_full_title = "{} {}".format(match.group(1), match.group(3))
            else:
                stripped_full_title = full_title

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
                click.echo("*** Song automatically chosen ***")
                nonlocal song_choice
                song_choice = i
                click.echo()
                click.echo("{}. Title: {} | Artist: {} | Label: {} | Genre: {} | Released: {}".format(i, full_title, artists, label, genre, release_date))
                click.echo()
                break

            click.echo("{}. Title: {} | Artist: {} | Label: {} | Genre: {} | Released: {}".format(i, full_title, artists, label, genre, release_date))

        # this closes the session
        await session.close()

    # get the search results
    asyncio.run(scrape_beatport())

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

    # Only ask about tagging file if no_confirmation is not set (default behavior)
    if not no_confirmation:
        if click.confirm('Do you want to tag the file?'):
            try:
                song_to_tag = get_song_info(results_map[song_choice])
                tag_song(song_to_tag, filename)
            except:
                print("Wasn't able to tag this song")
    else:
        try:
            song_to_tag = get_song_info(results_map[song_choice])
            tag_song(song_to_tag, filename)
        except:
            print("Wasn't able to tag this song")


def get_song_info(song):
    song_to_tag = Song(song.title, song.artist_list, song.url)

    async def scrape_beatport():
        session = AsyncHTMLSession()

        r = await session.get(song.url)

        await r.html.arender()

         # Extract the JSON data from the HTML
        json_data = None
        json_text = r.html.find('#__NEXT_DATA__', first=True).text
        json_data = json.loads(json_text)

        # Check if JSON data is found
        if json_data is None:
            click.echo("JSON data not found")
            return

        json_track_data = json_data['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']

        # tags all the necessary metadata
        bpm = json_track_data['bpm']
        genre = json_track_data['genre']['name']
        labels = json_track_data['release']['label']['name']
        album_name = json_track_data['release']['name']
        # Gets album art
        album_artwork_url = json_track_data['release']['image']['uri']
        response = requests.get(album_artwork_url)
        album_artwork = response.content

        # gets track number
        track_number = json_track_data['number']
        # extracts the year from the publish date
        match = re.search(r"(\d\d\d\d)", json_track_data['publish_date'])
        if match:
            year = match.group(1)
        else:
           click.echo(f"ERROR: Need to fix the regex for release_date: {year}")

        song_to_tag.labels = labels
        song_to_tag.genre = genre
        song_to_tag.bpm = int(bpm)
        song_to_tag.album_name = album_name
        song_to_tag.album_artwork = album_artwork
        song_to_tag.track_number = str(track_number)
        song_to_tag.year = year

        await session.close()

    asyncio.run(scrape_beatport())
    return song_to_tag

def tag_song(song_to_tag, song_file_path):
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
    # Need to use ID3 and APIC for saving artwork
    audiofile = ID3(song_file_path)
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
