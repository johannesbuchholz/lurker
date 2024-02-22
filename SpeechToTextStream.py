import sounddevice as sd
import collections
from time import time_ns, sleep
from deepspeech import Model
from numpy import ndarray


class SpeechToTextStream:

    byte_queue = collections.deque(maxlen=50000)

    def __init__(self, ):
        self.model = Model("deepspeech-0.9.3-models.pbmm")
        self.model.enableExternalScorer("deepspeech-0.9.3-models.scorer")
        print("Expected sample rate:", self.model.sampleRate())

    def callback(self, indata: ndarray, frames: int, time, status: sd.CallbackFlags) -> None:
        if status:
            print(status)
        self.byte_queue.extend(indata[:, 0])

    def begin_recording(self) -> None:
        # TODO 1: Add a separate thread performing the reads on teh queue
        # TODO 2. Add two "listeners", one for listening for a keyword which upon success starts a second one for a
        #  definite period which determines the actual task to to.
        with sd.InputStream(device=None, channels=1, dtype='int16', callback=self.callback, samplerate=16000):
            print("Start recording")
            while True:
                sleep(0.5)
                print(self.model.stt(self.byte_queue))


SpeechToTextStream().begin_recording()
