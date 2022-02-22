from pydub import AudioSegment
def Mixer(filepath1,filepath2,filename):
    sound1=AudioSegment.from_wav(filepath1)
    sound2=AudioSegment.from_wav(filepath2)
    soundOutput=sound1.overlay(sound2)
    soundOutput.export(filename,format="wav")