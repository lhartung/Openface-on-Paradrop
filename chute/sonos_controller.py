import os
import threading
import time

from soco import SoCo, SoCoException


SONOS_ADDRESS = os.environ.get("SONOS_ADDRESS", "192.168.1.181")


ALARM_URL = 'http://soundbible.com/mp3/School_Fire_Alarm-Cullen_Card-202875844.mp3'
START_URL = 'http://soundbible.com/mp3/dixie-horn_daniel-simion.mp3'
END_URL = 'http://soundbible.com/mp3/Page_Turn-Mark_DiAngelo-1304638748.mp3'
U0 = 'http://fmn.rrimg.com/fmn059/audio/20140822/0210/m_mTCE_490d00001683125d.mp3'
U1 = 'http://ia801402.us.archive.org/20/items/TenD2005-07-16.flac16/TenD2005-07-16t10Wonderboy.mp3'


class SonosController(object):
    def __init__(self):
        self.desired_uri = None
        self.last_played = None

        self.thread = threading.Thread(target=self.worker)
        self.thread.start()

    def play_alarm(self):
        self.desired_uri = ALARM_URL

    def play_by_name(self, name):
        varname = "SONG_FOR_{}".format(name.upper())
        self.desired_uri = os.environ.get(varname, ALARM_URL)

    def worker(self):
        core = SoCo(SONOS_ADDRESS)
        while True:
            time.sleep(1)

            try:
                # Require coordinator status. This fails or returns False
                # during initialization or if the speaker is not connected.
                # Just waiting does not seem to fix it; it is necessary to
                # reconstruct the core object to try again.
                if not core.is_coordinator:
                    core = SoCo(SONOS_ADDRESS)
                    continue

                if self.desired_uri is None:
                    continue

                track = core.get_current_track_info()
                if track['uri'] != self.desired_uri and self.desired_uri != self.last_played:
                    core.clear_queue()
                    core.add_uri_to_queue(self.desired_uri)
                    core.add_uri_to_queue(END_URL)
                    core.play_from_queue(0, True)
                    self.last_played = self.desired_uri
            except SoCoException as error:
                print("SoCoException: {}".format(error))
