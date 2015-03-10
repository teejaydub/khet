# simpleSound.py
# Plays audio files on Linux and Windows.
# Written Jan-2008 by Timothy Weber.
# Based on (reconstituted) code posted by Bill Dandreta at <http://www.velocityreviews.com/forums/t337346-how-to-play-sound-in-python.html>.

import platform

if platform.system().startswith('Win'):
    from winsound import PlaySound, SND_FILENAME, SND_ASYNC
elif platform.system().startswith('Linux'):
    from wave import open as waveOpen
    from ossaudiodev import open as ossOpen

    try:
        from ossaudiodev import AFMT_S16_NE
    except ImportError:
        if byteorder == "little":
            AFMT_S16_NE = ossaudiodev.AFMT_S16_LE
        else:
            AFMT_S16_NE = ossaudiodev.AFMT_S16_BE


def Play(filename):
    """Plays the sound in the given filename, asynchronously."""
    if platform.system().startswith('Win'):
        PlaySound(filename, SND_FILENAME|SND_ASYNC)
    elif platform.system().startswith('Linux'):
        s = waveOpen(filename,'rb')
        (nc,sw,fr,nf,comptype, compname) = s.getparams( )
        dsp = ossOpen('/dev/dsp','w')

        dsp.setparameters(AFMT_S16_NE, nc, fr)
        data = s.readframes(nf)
        s.close()
        dsp.write(data)
        dsp.close()