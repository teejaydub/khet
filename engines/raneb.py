from menes import *

class RanebEngine(MenesEngine):
    """Adds an adaptive search that explores the game tree for as long as it's allowed.

    Alternates between depth-first and breadth-first searching, widening and deepening the tree."""
    
    # Think for at most this many seconds after the opponent finishes his laser phase.
    MAX_ANALYSIS_BATCH_TIME = 4

    # Evaluating this many moves in one session results in a very large hunk of allocated memory.
    # That then slows things down... it's best to put an overall cap on it.
    MAX_MOVES_EVALUATED = 100000

    # When we're "deepening" the tree, only examine this fraction of the moves at any given level.
    DEEP_TREE_SLOPE = 0.3

    def __init__(self):
        MenesEngine.__init__(self)
        self.name = 'Raneb engine (in development)'
        self.deepening = False

    def StartAnalysis(self, game):
        MenesEngine.StartAnalysis(self, game)
        self.hintMove = None
        self.hintSquare = None

    def EnumerateMoves(self, game):
        result = MenesEngine.EnumerateMoves(self, game)
        for move in result:
            # Add our default properties.
            move.maxExploredDepth = 0
        return result

    def ContinueAnalysis(self, onOwnTime):
        if self.FinishedAnalyzing(onOwnTime):
            return False  # silently
        
        self.batchStartTime = time.clock()

        # Don't start deepening until we've examined at least 2 plies out.
        # Otherwise we commit suicide fairly often.
        if self.MinExploredDepth(self.moves) < 2:
            self.deepening = False
        else:
            self.deepening = not self.deepening

        if len(self.moves) > 0:
            if self.hintMove:
                # Just explore the hinted move.
                self.EvaluateObjective(self.game, self.hintMove, self.hintMove.exploredDepth + 1)
            elif self.hintSquare:
                # Just explore the moves originating from the hint square.
                minDepth = self.MinExploredDepth(self.moves)
                for move in self.moves:
                    if move.fromSquare == self.hintSquare and not self.IsBreakTime():
                        self.EvaluateObjective(self.game, move, minDepth + 1)
            elif self.deepening:
                # Explore the best move more deeply.
                self.EvaluateObjective(self.game, self.moves[0], self.moves[0].maxExploredDepth + 1)
            else:
                # Explore all moves in the list to the same level (widen the tree).
                minDepth = self.MinExploredDepth(self.moves)
                for move in self.moves:
                    if not self.IsBreakTime():
                        self.EvaluateObjective(self.game, move, minDepth + 1)
                
        self.SortForActivePlayer(self.game, self.moves)

        self.elapsedTime += (time.clock() - self.batchStartTime)

        if self.FinishedAnalyzing(onOwnTime):
            print "Final move list:"
            for move in self.moves:
                print move, move.oValue
            print "Analyzed %d moves to a depth of %d in %f seconds." % (self.moveCount, self.MinExploredDepth(self.moves), self.elapsedTime)
            print "Deepest analysis: %d plies." % (self.MaxExploredDepth(self.moves))
            return False
        else:
            return True  # Need more time.
        
    def SetHintSquare(self, square):
        if square == None:
            self.hintSquare = None
        else:
            self.hintSquare = self.game.board[square.row][square.col]
        pass

    def SetHintMove(self, move):
        if move == None:
            self.hintMove = None
        else:
            self.hintMove = self.FindMoveInList(move)

    def FinishedAnalyzing(self, onOwnTime):
        return onOwnTime and ( \
            (time.clock() - self.moveStart) >= RanebEngine.MAX_ANALYSIS_BATCH_TIME and self.MinExploredDepth(self.moves) >= 2 \
            ) or self.moveCount > RanebEngine.MAX_MOVES_EVALUATED

    def TakeNextMove(self, move):
        MenesEngine.TakeNextMove(self, move)
        self.hintMove = None
        self.hintSquare = None

    def MaxExploredDepth(self, moveList):
        """Returns the largest maxExploredDepth of any move in moveList."""
        return max(map(lambda x: x.maxExploredDepth, moveList))

    def BeforeEvaluateMoves(self, move):
        if self.deepening:
            # Prepare by narrowing the list of moves to evaluate, so it only includes a few of the best.

            # Duplicate nextMove's contents into oldMoves.
            move.oldMoves = []
            move.oldMoves[:] = move.nextMoves[:]

            # Split so nextMoves gets the first bunch, and oldMoves gets the rest.
            #print "Before:", [str(m) for m in move.nextMoves]
            del move.nextMoves[int(len(move.oldMoves) * RanebEngine.DEEP_TREE_SLOPE):]
            del move.oldMoves[0:len(move.nextMoves)]
            move.oldExploredDepth = move.exploredDepth

    def AfterEvaluateMoves(self, move):
        # Restore the moves from the original move list.
        if self.deepening:
            move.nextMoves.extend(move.oldMoves)
            move.oldMoves[:] = []
            move.exploredDepth = move.oldExploredDepth
            #print "After:", [str(m) for m in move.nextMoves]

    def EvaluateObjective(self, game, move, depth = 0):
        MenesEngine.EvaluateObjective(self, game, move, depth)
        
        if hasattr(move, 'nextMoves'):
            move.maxExploredDepth = max(move.maxExploredDepth, 1 + self.MaxExploredDepth(move.nextMoves))
        else:
            move.maxExploredDepth = max(move.maxExploredDepth, move.exploredDepth)
