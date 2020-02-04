#!/usr/bin/env python3
import logging
import requests
from sys import exit
from json import load

import dbus
from dbus.exceptions import DBusException
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib


class SpotifyTitle:
    def __init__(self):
        self.logger = logging.getLogger('SpotifyTitle')
        self.has_found_spotify = False
        self.current_song = {'trackId': 'None', 'playback_status': 'None'}
        self.prepare_bot()
        self.setup_dbus()

    def setup_dbus(self):
        self.logger.info('Setting up DBus...')
        bus_loop = DBusGMainLoop(set_as_default=True)
        self.session_bus = dbus.SessionBus(mainloop=bus_loop)

        bus = self.session_bus.get_object(
                'org.freedesktop.DBus',
                '/org/freedesktop/DBus')
        bus.connect_to_signal(
                'NameOwnerChanged',
                self.spotify_state_changed,
                arg0='org.mpris.MediaPlayer2.spotify')

        self.logger.info('Check if spotify is already running...')
        if self.is_spotify_running():
            self.logger.info('Found a running instance of spotify!')
            self.spotify_state_changed(None, None, True)
            self.trigger_song_update()
        else:
            self.logger.info('Spotify does not seem to be running...')
            self.logger.info('Waiting for spotify to be started...')

        try:
            self.loop = GLib.MainLoop()
            self.loop.run()
        except KeyboardInterrupt:
            self.logger.info('User requested a shutdown')
            self.spotify_state_changed(None, None, None)

    def is_spotify_running(self):
        try:
            self.session_bus.get_object(
                    'org.mpris.MediaPlayer2.spotify',
                    '/org/mpris/MediaPlayer2')
            return True
        except DBusException:
            return False

    def spotify_state_changed(self, name, before, after):
        if after and not self.has_found_spotify:
            self.logger.info('Found spotify on dbus!')
            self.spotify_bus = self.session_bus.get_object(
                    'org.mpris.MediaPlayer2.spotify',
                    '/org/mpris/MediaPlayer2')
            self.spotify_bus.connect_to_signal(
                    'PropertiesChanged',
                    self.update_current_song_info)
            self.has_found_spotify = True
        else:
            self.logger.info('Lost spotify on dbus, shutting down')
            self.loop.quit()
            self.logger.info('Finished shutting down')

    def trigger_song_update(self):
        changed_properties = {}
        interface = dbus.Interface(
                self.spotify_bus,
                'org.freedesktop.DBus.Properties')
        changed_properties['Metadata'] = interface.Get(
                'org.mpris.MediaPlayer2.Player',
                'Metadata')
        changed_properties['PlaybackStatus'] = interface.Get(
                'org.mpris.MediaPlayer2.Player',
                'PlaybackStatus')
        self.update_current_song_info(None, changed_properties, None)

    def update_current_song_info(
            self,
            interface_name,
            changed_properties,
            invalid_properties):

        if 'Metadata' not in changed_properties:
            self.logger.warning('Metadata not found in changed properties')
            return

        metadata = changed_properties['Metadata']
        try:
            # Somehow spotify sends the same properties a few times
            # this is needed so we don't spam the users
            if (self.current_song['trackId']
                    == str(metadata['mpris:trackid'])
                    and self.current_song['playback_status']
                    == 'Playing'):
                return
            self.current_song['trackId'] = str(metadata['mpris:trackid'])
            self.current_song['artists'] = []
            for artist in metadata['xesam:artist']:
                self.current_song['artists'].append(str(artist))
            self.current_song['album'] = str(metadata['xesam:album'])
            self.current_song['title'] = str(metadata['xesam:title'])
            self.current_song['albumArt'] = str(metadata['mpris:artUrl'])
            self.current_song['trackNumber'] = int(
                    metadata['xesam:trackNumber'])
            self.current_song['playback_status'] = str(
                    changed_properties['PlaybackStatus'])
        except KeyError as e:
            self.logger.warning('There was an error parsing the Metadata', e)

        self.current_song_changed()

    def prepare_bot(self):
        try:
            with open('config.json') as config:
                self.config = load(config)
        except (FileNotFoundError, PermissionError) as e:
            self.logger.fatal((
                f'Cannot open config.json file...\n'
                f'Please ensure it is there and readable\n'
                f'{e}'))
            exit(1)
        self.bot_base_url = (
                f'https://api.telegram.org/bot{self.config["bot_token"]}'
                f'/sendMessage?parse_mode=Markdown')

    def current_song_changed(self):
        self.logger.debug(
                'Current song has changed:'
                + self.current_song['title'])

        if self.current_song['playback_status'] == 'Paused':
            return

        bot_message = (
                f'{self.current_song["title"]} - '
                f'{", ".join(self.current_song["artists"])}')

        for chat_id in self.config['bot_chatIDs']:
            send_text = (
                    f'{self.bot_base_url}'
                    f'&chat_id={chat_id}'
                    f'&text={bot_message}')
            self.logger.debug(f'sending "{bot_message}" to {chat_id}')
            requests.get(send_text)


if __name__ == '__main__':
    LOGGER = logging.getLogger('SpotifyTitle')
    LOGGER.setLevel(logging.DEBUG)
    CH = logging.StreamHandler()
    CH.setLevel(logging.DEBUG)
    FORMATTER = logging.Formatter('%(asctime)s: [%(levelname)5s] %(message)s')
    CH.setFormatter(FORMATTER)
    LOGGER.addHandler(CH)
    SpotifyTitle()
