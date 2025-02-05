# window.py
#
# Copyright 2021 SeaDve
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import threading
import os
from time import strftime, localtime

from gettext import gettext as _
from gi.repository import Gtk, GLib, Handy

from .timers import Timer, DelayTimer
from .recorders import VideoRecorder, AudioRecorder


@Gtk.Template(resource_path='/io/github/seadve/Kooha/window.ui')
class KoohaWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'KoohaWindow'

    start_record_button = Gtk.Template.Child() # will be unused when DE check is removed
    stop_record_button = Gtk.Template.Child()
    cancel_delay_button = Gtk.Template.Child()
    start_record_button_box = Gtk.Template.Child()

    fullscreen_mode_toggle = Gtk.Template.Child()
    selection_mode_toggle = Gtk.Template.Child()

    title_stack = Gtk.Template.Child()
    fullscreen_mode_label = Gtk.Template.Child()
    selection_mode_label = Gtk.Template.Child()

    record_audio_toggle = Gtk.Template.Child()
    record_microphone_toggle = Gtk.Template.Child()
    show_pointer_toggle = Gtk.Template.Child()

    main_stack = Gtk.Template.Child()
    main_screen_box = Gtk.Template.Child()
    recording_label_box = Gtk.Template.Child()
    time_recording_label = Gtk.Template.Child()
    delay_label_box = Gtk.Template.Child()
    delay_label = Gtk.Template.Child()

    menu_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.application = kwargs["application"]

        self.record_audio_toggle.set_active(self.application.settings.get_boolean("record-audio"))
        self.record_microphone_toggle.set_active(self.application.settings.get_boolean("record-microphone"))
        self.show_pointer_toggle.set_active(self.application.settings.get_boolean("show-pointer"))

        self.timer = Timer(self.time_recording_label)
        self.delay_timer = DelayTimer(self.delay_label, self.start_recording)
        self.video_recorder = VideoRecorder(self.fullscreen_mode_toggle)

        desktop_environment = os.environ['XDG_CURRENT_DESKTOP']
        if "GNOME" not in desktop_environment:
            self.start_record_button.set_sensitive(False)
            self.start_record_button.set_label(f"{desktop_environment} is not yet supported")

    @Gtk.Template.Callback()
    def on_start_record_button_clicked(self, widget):
        if not self.fullscreen_mode_toggle.get_active():
            self.video_recorder.get_coordinates()

        video_directory = self.application.settings.get_string('saving-location')
        filename = f"/Kooha-{strftime('%Y-%m-%d-%H:%M:%S', localtime())}"
        video_format = f".{self.application.settings.get_string('video-format')}"
        if self.application.settings.get_string("saving-location") == "default":
            video_directory = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS)
            if not os.path.exists(video_directory):
                video_directory = os.getenv("HOME")
        self.directory = f"{video_directory}{filename}{video_format}"

        if os.path.exists(video_directory):
            delay = int(self.application.settings.get_string("record-delay"))
            self.delay_timer.start(delay)
            if delay > 0:
                self.main_stack.set_visible_child(self.delay_label_box)
        else:
            error = Gtk.MessageDialog(transient_for=self, type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.OK, text=_("Recording cannot start"))
            error.format_secondary_text(_("The saving location you have selected may have been deleted."))
            error.run()
            error.destroy()

    def start_recording(self):
        threading.Thread(target=self.application.playchime).start()

        record_audio = self.application.settings.get_boolean("record-audio")
        record_microphone = self.application.settings.get_boolean("record-microphone")

        self.audio_recorder = AudioRecorder(record_audio, record_microphone, self.directory)
        self.audio_recorder.start()

        if (record_audio and self.audio_recorder.default_audio_output) or (record_microphone and self.audio_recorder.default_audio_input):
            self.directory = self.audio_recorder.get_tmp_dir("video")

        framerate = 30
        show_pointer = self.application.settings.get_boolean("show-pointer")
        pipeline = "queue ! vp8enc min_quantizer=10 max_quantizer=10 cpu-used=3 cq_level=13 deadline=1 static-threshold=100 threads=3 ! queue ! matroskamux"

        self.video_recorder.start(self.directory, framerate, show_pointer, pipeline)

        self.main_stack.set_visible_child(self.recording_label_box)

        self.timer.start()

    @Gtk.Template.Callback()
    def on_stop_record_button_clicked(self, widget):
        self.main_stack.set_visible_child(self.main_screen_box)

        self.video_recorder.stop()
        self.audio_recorder.stop()
        self.timer.stop()

    @Gtk.Template.Callback()
    def on_cancel_delay_button_clicked(self, widget):
        self.main_stack.set_visible_child(self.main_screen_box)

        self.delay_timer.cancel()

    @Gtk.Template.Callback()
    def on_fullscreen_mode_clicked(self, widget):
        self.title_stack.set_visible_child(self.fullscreen_mode_label)

    @Gtk.Template.Callback()
    def on_selection_mode_clicked(self, widget):
        self.title_stack.set_visible_child(self.selection_mode_label)

    @Gtk.Template.Callback()
    def on_record_audio_toggled(self, widget):
        if self.record_audio_toggle.get_active():
            self.application.settings.set_boolean("record-audio", True)
        else:
            self.application.settings.set_boolean("record-audio", False)

    @Gtk.Template.Callback()
    def on_record_microphone_toggled(self, widget):
        if self.record_microphone_toggle.get_active():
            self.application.settings.set_boolean("record-microphone", True)
        else:
            self.application.settings.set_boolean("record-microphone", False)

    @Gtk.Template.Callback()
    def on_show_pointer_toggled(self, widget):
        if self.show_pointer_toggle.get_active():
            self.application.settings.set_boolean("show-pointer", True)
        else:
            self.application.settings.set_boolean("show-pointer", False)
