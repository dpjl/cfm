import signal

from camerafile import Constants


# Faire une classe pour ça. Il faudrait en mode par défaut: afficher un message, et faire un exit
# Faire un exit direct ?? ça n'a pas l'air de marcher immédiatement avec multiprocessing, pourquoi ?
def default_handler(unused_signum, unused_frame):
    # print("Python (main process or one subprocess) is initializing, please wait a little and retry to interrupt")
    pass


Constants.original_sigint_handler = signal.getsignal(signal.SIGINT)
signal.signal(signal.SIGINT, default_handler) # mettre juste IGN à la place ?
