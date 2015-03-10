from khetEngine import *

class TiuEngine(KhetEngine):
    """A very simplistic engine - not really useful for play, just for testing the framework."""
    def __init__(self):
        KhetEngine.__init__(self)
        self.name = 'Tiu engine'

    def StartAnalysis(self, game):
        self.game = game
        self.moves = self.EnumerateMoves(game)

    def TakeNextMove(self, move):
        self.StartAnalysis(self.game)

    def GetMove(self):
        return random.choice(self.moves)
