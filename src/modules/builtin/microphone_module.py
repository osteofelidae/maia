"""
Module to manage microphone
"""

# INTERNAL DEPENDENCIES
from src.modules.module import AsyncModule
from src.utils.config_utils import *
from src.utils.path_utils import path, Path


# DEPENDENCIES
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import io


# MICROPHONE MODULE
class MicrophoneAsyncModule(AsyncModule):

    def __init__(
            self,
            module_id: str = "microphone"
    ):
        # TODO docstring

        self._is_recording = False  # Is recording flag

        super().__init__(module_id)

    def _start_recording(self):
        # TODO docstring

        # If not recording, set flag
        if not self._is_recording:
            self._is_recording = True
        else:
            return  # TODO exception or something

        frames = []
        def append_callback(data_in, frames_in, time, status):
            frames.append(data_in.copy())

        with sd.InputStream(
                samplerate=16000,  # TODO change to params/config
                channels=1,
                dtype="int16",
                callback=append_callback
        ):

            # Record until stopped
            while self._is_recording:
                sd.sleep(100)  # TODO change to params/config

        # Combine and record audio
        audio = np.concatenate(frames, axis=0)

        # TODO maybe convert to wav?

        return audio


    def _stop_recording(self):
        # TODO docstring
        self._is_recording = False

    # TODO combined 'do_recording' function