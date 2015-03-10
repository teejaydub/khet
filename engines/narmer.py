from tiu import *

class NarmerEngine(TiuEngine):
    """An engine that uses a simple objective function to choose from the avialable moves, with no lookahead."""
    def __init__(self):
        TiuEngine.__init__(self)
        self.name = 'Narmer engine'

    def StartAnalysis(self, game):
        TiuEngine.StartAnalysis(self, game)
        for move in self.moves:
            move.exploredDepth = 0
            self.EvaluateObjective(game, move)
                
        #print "Unsorted move list:"
        #for move in self.moves:
        #    print move, move.oValue
            
        self.SortForActivePlayer(game, self.moves)
        
        print "Final move list:"
        for move in self.moves:
            print move, move.oValue

    def SortForActivePlayer(self, game, moves):
        moves.sort(key=lambda m: m.oValue, reverse=(game.activePlayer == PLAYER_SILVER))

    def EvaluateObjective(self, game, move):
        """Computes the objective function for the given move, and stores it in move's oValue.

        Values are positive for Silver, negative for Red."""
        self.laserPyramids = [0, 0]
        self.hasGuard = [0, 0]
        game.MakeAndPushMove(move)
        try:
            game.FireLaser(move)
            move.oValue = self.EvaluatePosition(game)
            print move, move.oValue
        finally:
            game.UndoAndPopLastMove()

    def EvaluatePosition(self, game):
        result = 0
        # Run through all the pieces.
        for piece in allPieces(game.board):
            result += self.EvaluatePiece(game, piece)
                    
        # Give a bonus for having laser-guiding pyramids (up to 2).
        result += min((self.laserPyramids[PLAYER_SILVER], 2)) * 3
        result -= min((self.laserPyramids[PLAYER_RED], 2)) * 3

        # Give a bonus for having a guard piece.
        # (Particularly useful for keeping the "guard pyramid" in place, but tolerates other pieces playing that role.)
        result += self.hasGuard[PLAYER_SILVER] * 4
        result -= self.hasGuard[PLAYER_RED] * 4

        # Give a bonus for pieces around the Pharaoh of own color, negative for opponent's.
        result += self.PharaohAdjacentFriends(game, PLAYER_SILVER) * 3
        result -= self.PharaohAdjacentFriends(game, PLAYER_RED) * 3
                
        # See if the opponent's laser will immediately hit anything.
        hitPiece = game.FindLaserPathEnd(game.FindLaserPath(1 - game.activePlayer))
        if hitPiece:
            hitValue = self.EvaluateMaterial(hitPiece) * self.GetColorFactor(hitPiece.color)
            if hitPiece.color != game.activePlayer:
                # Lost one of theirs - it's annoying, so that's good, but not worth full value,
                # because they'll probably avoid it.
                hitValue *= 0.45
                # Capping the total value seems to make sense in practice - it's not worth hundreds of points
                # to force the opponent to avoid hitting their own Pharaoh, even if it will win a game
                # against a novice.
                hitValue = min(hitValue, 1.5)
            result -= hitValue
        return result

    def GetColorFactor(self, color):
        """Returns 1 for Silver, -1 for Red."""
        if color == PLAYER_RED:
            return -1
        else:
            return 1

    def EvaluatePiece(self, game, piece):
        # Count laser-guiding pyramids - those in or adjacent to the laser column.
        # If you have none, your laser is non-functional.
        if isinstance(piece, Pyramid) and piece.square.IsNearLaser(piece.color):
            self.laserPyramids[piece.color] += 1
        # Note if there is at least one guard piece.
        if self.PieceIsGuard(game, piece):
            self.hasGuard[piece.color] = True
        # Count material.
        return self.EvaluateMaterial(piece) * self.GetColorFactor(piece.color)

    def PieceIsGuard(self, game, piece):
        """Returns true if this piece is a 'guard' piece - serving the purpose of the 'guard pyramid.'"""
        phar = game.Pharaoh(piece.color)
        if phar:
            pSquare = phar.square
            if pSquare == None or piece.square.row != pSquare.row or not piece.isMirrored:
                return False
            if piece.color == PLAYER_SILVER:
                return piece.square.col < pSquare.col
            else:
                return piece.square.col > pSquare.col
        else:
            return False

    def PharaohAdjacentFriends(self, game, color):
        """Returns the count of friendly pieces adjacent to this one; enemies are negative friends.

        For this purpose, diagonals only count 1/3,
        and friendlies only count if they're oriented away from the opponent's laser row."""
        result = 0
        phar = game.Pharaoh(color)
        if phar and phar.square:
            pSquare = phar.square
            for square in pSquare.GetNeighbors(game.board):
                if square.piece:
                    if square.row == pSquare.row or square.col == pSquare.col:
                        weight = 1
                    else:
                        # Diagonal.
                        weight = 0.33
                        
                    if square.piece.color == color:
                        # Friendly piece.
                        if color == PLAYER_SILVER:
                            deflection = [0]
                        else:
                            deflection = [180]
                        if isinstance(square.piece, Djed):
                            deflection.append((deflection[0] + 180) % 360)
                        if square.piece.rotation == deflection:
                            result += weight
                            #print "+", weight
                    else:
                        # Enemy piece.
                        result -= weight
                        #print "-", weight
        return result
        
    def EvaluateMaterial(self, piece):
        """Return the value of this piece to its owner."""
        if isinstance(piece, Obelisk):
            if piece.stacked:
                return 4
            else:
                return 2
        elif isinstance(piece, Pyramid):
            return 4
        elif isinstance(piece, Pharaoh):
            return 1000
        else:
            return 0

    def GetMove(self):
        return self.moves[0]
