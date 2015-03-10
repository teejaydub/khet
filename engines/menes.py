import time
from narmer import *

class MenesEngine(NarmerEngine):
    """Adds traversal of the game tree (lookahead), to a fixed number of plies that are exhaustively searched.

    Also supports incremental analysis with StartAnalysis/ContinueAnalysis/TakeNextMove."""

    # Does a full tree evaluation to this many levels, counting the current player's next move.
    MAX_DEPTH = 2

    # Analyze for only this many seconds before taking a break.
    MAX_ANALYSIS_BATCH_TIME = 0.2

    def __init__(self):
        NarmerEngine.__init__(self)
        self.name = 'Menes engine, %d-ply' % MenesEngine.MAX_DEPTH

    def EnumerateMoves(self, game):
        result = TiuEngine.EnumerateMoves(self, game)
        for move in result:
            move.exploredDepth = 0
            move.oValue = 0
        return result
    
    def StartAnalysis(self, game):
        # Work with a duplicate of the game, so we can analyze independent of the moves made
        # on the board - e.g., tentative moves that haven't been confirmed yet.
        self.mainGame = game
        game = copy.deepcopy(self.mainGame)

        self.StartMove()
        TiuEngine.StartAnalysis(self, game)  # Finds initial move list.

    def StartMove(self):
        self.moveCount = 0
        self.elapsedTime = 0

    def ContinueAnalysis(self, onOwnTime):
        if self.FinishedAnalyzing(onOwnTime):
            return False
        
        self.batchStartTime = time.clock()
        for move in self.moves:
            self.EvaluateObjective(self.game, move)
                
        self.SortForActivePlayer(self.game, self.moves)

        self.elapsedTime += (time.clock() - self.batchStartTime)

        if self.FinishedAnalyzing(onOwnTime):
            print "Final move list:"
            for move in self.moves:
                print move, move.oValue
            print "Analyzed %d moves to a depth of %d in %f seconds." % (self.moveCount, self.MinExploredDepth(self.moves), self.elapsedTime)
            return False
        else:
            return True  # Need more time.

    def TakeNextMove(self, move):
        move = self.FindMoveInList(move)
        print "Passing move to engine: ", move
        move.TakeCompleteTurn(self.game)
        # Now follow down that branch of the analysis tree.
        del self.moves[:]  # Makes it clearer to garbage collection that these are going away.
        if hasattr(move, 'nextMoves'):
            self.moves = move.nextMoves
        else:
            self.moves = self.EnumerateMoves(self.game)
        # And restart the timing.
        self.StartMove()

    def FinishedAnalyzing(self, onOwnTime):
        return self.MinExploredDepth(self.moves) == MenesEngine.MAX_DEPTH

    def GetMove(self):
        result = NarmerEngine.GetMove(self)
        # Make that refer to the 'main' game - the real one we've been asked to analyze.
        realResult = result.TransferToBoard(self.mainGame.board)
        realResult.oValue = result.oValue
        return realResult

    def MinExploredDepth(self, moveList):
        """Returns the smallest exploredDepth of any move in moveList."""
        return min(map(lambda x: x.exploredDepth, moveList))

    def IsBreakTime(self):
        elapsedTime = time.clock() - self.batchStartTime
        return elapsedTime > MenesEngine.MAX_ANALYSIS_BATCH_TIME

    def FindMoveInList(self, mainMove):
        """Looks for the given move, which is relative to the main game, in our current move list.

        If found, returns it; otherwise, translates the move to our local board.
        (Relies on comparison being defined for Move.)"""
        result = filter(mainMove.Matches, self.moves)
        if len(result) == 0:
            # Could be because the human player made a move faster than we could generate it??
            # Could also indicate a bug somewhere, though.
            return mainMove.TransferToBoard(self.game.board)
        else:
            return result[0]
    
    def EvaluateObjective(self, game, move, depth = 0):
        if depth == 0:
            depth = MenesEngine.MAX_DEPTH

        # Exit quickly (and don't count the move) if we've already fully explored this move.
        if move.exploredDepth >= depth:
            pass

        if self.IsBreakTime():
            return
            
        self.laserPyramids = [0, 0]
        self.hasGuard = [0, 0]
        self.moveCount += 1

        # Report some intermediate status to the console.
        if self.moveCount % 4000 == 0:
            print self.moveCount, "...",
            
        game.MakeAndPushMove(move)
        try:
            game.FireLaser(move)

            # Always evaluate the current move position first.
            if move.exploredDepth == 0:
                move.oValue = self.EvaluatePosition(game)
                move.exploredDepth = 1

            if move.exploredDepth >= depth:
                pass
            elif game.IsOver():
                # Can't go any deeper; just say we've gone to the desired depth.
                move.exploredDepth = depth
            else:
                # Now, evaluate all the moves that can be made from this position by the next player.
                game.PassToNextPlayer()
                try:
                    if not hasattr(move, 'nextMoves'):
                        move.nextMoves = self.EnumerateMoves(game)

                    self.BeforeEvaluateMoves(move)  # Hook
                    
                    for nm in move.nextMoves:
                        if not self.IsBreakTime():
                            self.EvaluateObjective(game, nm, depth - 1)

                    self.AfterEvaluateMoves(move)  # Hook
                            
                    self.SortForActivePlayer(game, move.nextMoves)
                    move.oValue = move.nextMoves[0].oValue  # This move's score is your opponent's best next move's score.
                    move.exploredDepth = 1 + self.MinExploredDepth(move.nextMoves)
                finally:
                    # Revert to the last player.
                    game.PassToNextPlayer()
            
            #print move, move.oValue
        finally:
            game.UndoAndPopLastMove()

    def BeforeEvaluateMoves(self, move):
        """Hook called during EvaluateObjective(), before evaluating the given move's nextMoves.

        move.nextMoves is populated with the candidate child moves."""
        pass

    def AfterEvaluateMoves(self, move):
        """Hook called during EvaluateObjective(), after evaluating the given move's nextMoves."""
        pass

    def EvaluatePosition(self, game):
        """Takes from the base version, but pares it down for speed."""
        result = 0
        # Run through all the pieces.
        for piece in allPieces(game.board):
            result += self.EvaluatePiece(game, piece)
                    
        # Give a bonus for having laser-guiding pyramids (up to 2).
        result += min((self.laserPyramids[PLAYER_SILVER], 2)) * 3
        result -= min((self.laserPyramids[PLAYER_RED], 2)) * 3
        return result

    def EvaluatePiece(self, game, piece):
        # Count laser-guiding pyramids - those in or adjacent to the laser column.
        # If you have none, your laser is non-functional.
        if isinstance(piece, Pyramid) and piece.square.IsNearLaser(piece.color):
            self.laserPyramids[piece.color] += 1

        # Count material.
        return self.EvaluateMaterial(piece) * self.GetColorFactor(piece.color)
