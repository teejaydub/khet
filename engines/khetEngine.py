from khetGame import *
import random
import time

class KhetEngine:
    """An engine to analyze Khet game positions and come up with move suggestions."""
    def __init__(self):
        self.name = 'Unnamed engine'

    def Analyze(self, game):
        """Analyzes the given game position entirely."""
        self.StartAnalysis(game)
        while (self.ContinueAnalysis(true)):
            pass

    def StartAnalysis(self, game):
        """Begins analysis on the given position, and returns quickly."""
        pass

    def StartApparentTime(self):
        """The opponent has finished his move, so it's as though he's punched his clock now.

        Of course, we could have been analyzing for this move already."""
        self.moveStart = time.clock()

    def ContinueAnalysis(self, onOwnTime):
        """Continues analysis on the same game most recently Started.

        Returns False when finished, True when there's more analysis needed.
        Assumes the game position hasn't changed at all since StartAnalysis() was last called.
        onOwnTime is false if the other player is currently thinking - it's not on the engine's clock."""
        return False

    def TakeNextMove(self, move):
        """The given move has been added to the previously-analyzed game.  Prepare for the next round of analysis."""
        pass

    def SetHintSquare(self, square):
        """Focus analysis on responses to a move from the given square.

        Pass None for square to cancel the hint.
        All hints are canceled at the next TakeNextMove call."""
        pass

    def SetHintMove(self, move):
        """Focus analysis on responses to the given move.  It's not committed yet, though.

        Pass None for move to cancel the hint.
        All hints are canceled at the next TakeNextMove call."""
        pass

    def GetMove(self):
        """Returns the best move generated for the most recent analysis.

        Returns None if, for some reason, no move could be generated."""
        return None

    # Functions for use by derived classes.

    def EnumerateMoves(self, game):
        """Returns a list of KhetMoves, including all legal moves for the current player.

        Returns an empty list if there are no legal moves."""
        result = []
        for piece in allPieces(game.board):
            if piece.color == game.activePlayer:
                result.extend(piece.EnumerateMoves(game.board))
        random.shuffle(result)
        return result
