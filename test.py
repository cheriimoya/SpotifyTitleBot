import requests

import dbus
from dbus.exceptions import DBusException

from pdb import set_trace


current_song = {'trackId': 'None'}


def send_song_to_bot():
    bot_message = f'{current_song["title"]} \
            - {current_song["artist"]}'

    bot_token = ''
    bot_chatID = ''
    send_text = (
            'https://api.telegram.org/bot'
            + bot_token
            + '/sendMessage?chat_id='
            + bot_chatID
            + '&parse_mode=Markdown&text='
            + bot_message)
    # requests.get(send_text)
    print(send_text)


try:
    session_bus = dbus.SessionBus()
    spotify_bus = session_bus.get_object(
            "org.mpris.MediaPlayer2.spotify", "/org/mpris/MediaPlayer2")

    interface = dbus.Interface(spotify_bus, "org.freedesktop.DBus.Properties")

    metadata = interface.Get("org.mpris.MediaPlayer2.Player", "Metadata")
except DBusException:
    set_trace()

for key, value in metadata.items():
    print(key, ' => ', value)
