"""khetGame

Just the core classes for implementing the game mechanics; doesn't include any
representation (graphical or textual), nor any player control.

--TJW 2008"""


import copy
import datetime


# Player constants
PLAYER_SILVER = 0
PLAYER_RED = 1
PLAYER_NONE = -1

players = [PLAYER_SILVER, PLAYER_RED]

colorName = ["Silver", "Red"]

# Board constants
numRows = 8
numCols = 10
allRows = range(0, numRows)
allCols = range(0, numCols)


def allSquares(board):
    '''A generator for iterating through board squares, which are (currently) stored as a list of rows of squares.'''
    for row in board:
        for square in row:
            yield square
            
def allPieces(board):
    '''A similar generator for iterating through all pieces on the given board.'''
    for row in board:
        for square in row:
            if square.piece:
                yield square.piece

def IsLegalSquare(row, col):
    return row >= 0 and row < numRows and col >= 0 and col < numCols


def SwapPair(p):
    """Swaps the members of a binary tuple."""
    return (p[1], p[0])

def SwapAndNegate(p):
    """Swaps the members of a binary tuple, and negates them."""
    return (-p[1], -p[0])


class Piece:
    def __init__(self, color, rotation = 0):
        self.color = color
        self.canRotate = False  # By the player - all pieces can be rotated internally.
        self.square = None
        self.rotation = rotation  # Can be 0, 90, 180, or 270
        self.selected = False
        self.letterCode = '_'
        self.isMirrored = False

    def Duplicate(self):
        """Returns a copy of this piece that's NOT on the board."""
        dupe = copy.copy(self)
        dupe.square = None
        return dupe

    def SwapColor(self):
        """Changes this piece to the other color."""
        self.color = 1 - self.color

    def MoveTo(self, square):
        """Moves the piece from wherever it is to the specified square.

        If square is None, removes it from the board entirely."""
        if self.square:
            self.square.piece = None
            self.square = None

        if square:
            if square.piece:
                # Something's already there - let it know we're displacing it.
                square.piece.square = None
            square.piece = self
            self.square = square

    def Rotate(self, degrees):
        self.rotation += degrees
        self.rotation %= 360

    def CanMoveTo(self, square):
        """Returns true if this piece can be moved to the specified square.

        Implements some rules that are common to all pieces."""
        return square \
           and (square.color == PLAYER_NONE or square.color == self.color) \
           and square.IsAdjacentTo(self.square) \
           and (self.CanMoveToPiece(square.piece))

    def CanMoveToPiece(self, piece):
        """Returns true if you can move this piece onto the specified piece."""
        return piece == None

    def EnumerateMoves(self, board):
        """Enumerate all legal moves this piece can make from its current square on the given board.
        
        Returns a list of KhetMoves in undefined order.
        This default version returns all lateral moves this piece is allowed to make."""
        result = []
        for square in self.square.GetNeighbors(board):
            if self.CanMoveTo(square):
                result.append(Move(self, square))
        return result

    def FinishMakeMove(self, move):    
        """Does anything special to complete a Move.MovePiece."""
        0

    def FinishUndoMove(self, move):
        """Does anything special to complete a Move.UndoMove."""
        0

    def SaveHitInfo(self, move):
        """This piece is about to be hit.  Save any information we would need to restore it in move."""
        move.hitPiece = self
        move.hitPieceSquare = self.square

    def DoHit(self, parentGame):
        """Does whatever should happen when the piece is hit by a laser."""
        self.MoveTo(None)

    def UndoHit(self, move):
        """We just undid the given move, and this piece was hit.  Restore it."""
        self.MoveTo(move.hitPieceSquare)

    def Reflects(self, direction):
        """Reflects a laser off this piece, moving in the indicated direction.

        The direction is given as a tuple of the X- and Y-coordinates of the direction vector.
        Returns a new direction (as a tuple).
        If the laser does not reflect at all (is absorbed/hits), returns (0, 0)."""
        return (0, 0)

    
class Pharaoh(Piece):
    def __init__(self, color, rotation):
        Piece.__init__(self, color, rotation)
        self.letterCode = 'P'


class Obelisk(Piece):
    def __init__(self, color, stacked):
        Piece.__init__(self, color)
        self.stacked = stacked
        self.letterCode = 'O'

    def CanMoveToPiece(self, piece):
        return Piece.CanMoveToPiece(self, piece) \
               or (isinstance(piece, Obelisk) \
                   and piece.color == self.color \
                   and not self.stacked and not piece.stacked) \
    
    def FinishMakeMove(self, move):    
        if move.oldPiece:
            # If we're moving onto another obelisk, then we must stack.
            self.stacked = True
        elif self.stacked:
            # Moving a stack to an empty square.
            if hasattr(move, 'unstackObelisk') and move.unstackObelisk:
                self.stacked = False
                Obelisk(self.color, False).MoveTo(move.fromSquare)
            # Otherwise, move the whole stack (the default).

    def FinishUndoMove(self, move):
        if move.oldPiece:
            # We must have stacked onto that piece, so unstack now.
            self.stacked = False
            # The other piece will be restored by the Move.
        elif hasattr(move, 'unstackObelisk') and move.unstackObelisk:
            # We unstacked onto an empty square.  Stack again.
            self.stacked = True

    def SaveHitInfo(self, move):
        Piece.SaveHitInfo(self, move)
        move.hitPieceWasStacked = self.stacked

    def DoHit(self, parentGame):
        if self.stacked:
            self.stacked = False
        else:
            Piece.DoHit(self, parentGame)

    def UndoHit(self, move):
        Piece.UndoHit(self, move)
        self.stacked = move.hitPieceWasStacked

    def EnumerateMoves(self, board):
        # Start with the default set of moves.
        result = Piece.EnumerateMoves(self, board)

        if self.stacked:
            # Create duplicates that unstack.
            for i in range(len(result)):  # use range so we don't continue iterating over new additions
                result[i].unstackObelisk = False
                if result[i].oldPiece:
                    # This moves onto another piece.
                    # It must be an unstacked obelisk, so stack.
                    pass  # But that'll happen by default.
                elif self.stacked:
                    # Moving onto a blank square: We have the choice.
                    # Add another copy that does unstack.
                    unstackedMove = copy.copy(result[i])
                    unstackedMove.unstackObelisk = True
                    result.append(unstackedMove)
                
        return result


class RotatablePiece(Piece):
    """A piece that can rotate.

    Rotations are expressed in degrees, and can be 0, 90, 180, or 270."""    
    def __init__(self, color, rotation):
        Piece.__init__(self, color, rotation)
        self.canRotate = True
    

class Pyramid(RotatablePiece):
    """The Pyramid; rotation = 0 means the mirror faces the upper left corner."""
    def __init__(self, color, rotation = 0):
        RotatablePiece.__init__(self, color, rotation)
        self.letterCode = 'p'
        self.isMirrored = True

    def Reflects(self, direction):
        if self.rotation == 0:
            if direction == (0, 1) or direction == (1, 0):
                return SwapAndNegate(direction)
        elif self.rotation == 90:
            if direction == (0, 1) or direction == (-1, 0):
                return SwapPair(direction)
        elif self.rotation == 180:
            if direction == (-1, 0) or direction == (0, -1):
                return SwapAndNegate(direction)
        elif self.rotation == 270:
            if direction == (0, -1) or direction == (1, 0):
                return SwapPair(direction)
        return (0, 0)            
            
    def EnumerateMoves(self, board):
        # Start with the default set of moves.
        result = Piece.EnumerateMoves(self, board)

        # Add the two rotations.
        result.append(Move(self, self.square, -1))
        result.append(Move(self, self.square, 1))

        return result


class Djed(RotatablePiece):
    """The Djed; rotation = 0 means the mirrors face the upper left and lower right corners."""
    def __init__(self, color, rotation = 0):
        RotatablePiece.__init__(self, color, rotation)
        self.letterCode = 'D'
        self.isMirrored = True

    def CanMoveToPiece(self, piece):
        return Piece.CanMoveToPiece(self, piece) \
            or isinstance(piece, Obelisk) \
            or isinstance(piece, Pyramid)

    def Reflects(self, direction):
        if self.rotation == 0 or self.rotation == 180:
            return SwapAndNegate(direction)
        elif self.rotation == 90 or self.rotation == 270:
            return SwapPair(direction)
        else:
            # Should never occur...
            return (0, 0)

    def FinishMakeMove(self, move):
        if move.oldPiece:
            # If we're moving onto another piece, we swap.
            move.oldPiece.MoveTo(move.fromSquare)
           
    def EnumerateMoves(self, board):
        # Start with the default set of moves.
        result = Piece.EnumerateMoves(self, board)

        # Add the rotation.
        # (Rotation in the other direction is equivalent for Djeds.)
        result.append(Move(self, self.square, 1))

        return result


class Square:
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.piece = None
        self.highlighted = False
        self.SetColor()

    def SetColor(self):
        self.color = PLAYER_NONE
        
        if self.col == 0:
            self.color = PLAYER_RED
        elif self.col == 9:
            self.color = PLAYER_SILVER
        elif self.row == 0 or self.row == 7:
            if self.col == 1:
                self.color = PLAYER_SILVER
            elif self.col == 8:
                self.color = PLAYER_RED

    def __str__(self):
        return chr(ord('a') + self.col) + chr(ord('0') + numRows - self.row)

    @staticmethod
    def FromString(s, board):
        """Returns the square on the board that matches the coordinates put out by __str__.

        Assumes s is valid."""
        col = ord(s[0]) - ord('a')
        row = numRows - (ord(s[1]) - ord('0'))
        return board[row][col]

    def HasSameCoords(self, other):
        return other.row == self.row and other.col == self.col

    def CanMovePiece(self, player):
        return self.piece and self.piece.color == player

    def IsAdjacentTo(self, square):
        if square:
            rowDelta = abs(square.row - self.row)
            colDelta = abs(square.col - self.col)
            return rowDelta <= 1 and colDelta <= 1
        else:
            return False

    def IsNearLaser(self, color):
        """Returns true if this square is in or adjacent to the laser column of the specified color."""
        if color == PLAYER_SILVER:
            return self.col == 9 or self.col == 8
        else:
            return self.col == 0 or self.col == 1

    def GetNeighbor(self, board, rowDelta, colDelta):
        """Returns this square's neighbor with the given row and column delta, or None if it's off the board."""
        newRow = self.row + rowDelta
        newCol = self.col + colDelta
        if IsLegalSquare(newRow, newCol):
            return board[newRow][newCol]
        else:
            return None

    def GetNeighbors(self, board):
        result = []
        for rowDelta in range(-1, 2):
            for colDelta in range(-1, 2):
                if rowDelta != 0 or colDelta != 0:  # if both were 0, it's not a neighbor
                    square = self.GetNeighbor(board, rowDelta, colDelta)
                    if square:
                        result.append(square)
        return result


class Move:
    def __init__(self, piece, toSquare, rotateDir = 0):
        """Creates a new move; rotation is in the range [-1, +1]."""
        self.piece = piece
        self.fromSquare = piece.square
        self.toSquare = toSquare
        if toSquare:
            self.oldPiece = toSquare.piece
        else:
            self.oldPiece = None
        self.fromRotation = piece.rotation
        self.rotateDir = rotateDir
        if rotateDir:
            self.toRotation = (piece.rotation + 90 * rotateDir) % 360
        else:
            self.toRotation = piece.rotation
        self.hitPiece = None

    def __str__(self):
        if self.piece:
            result = self.piece.letterCode + str(self.fromSquare)
            if self.toSquare and (self.toSquare != self.fromSquare):
                result += str(self.toSquare)
                if hasattr(self, "unstackObelisk") and self.unstackObelisk:
                    result += '-'
            else:
                if self.rotateDir == -1:
                    result += '<'
                elif self.rotateDir == 1:
                    result += '>'

            if self.hitPiece:
                result += " x" + str(self.hitPieceSquare)
                    
            return result
        else:
            return "(empty move)"

    @staticmethod
    def FromString(s, board):
        """Constructs a new move from a string like that produced by __str__().

        Assumes the string contains a single legal move, and currently does no checking to confirm that.
        Ignores the hit-piece bit."""
        fromSquare = Square.FromString(s[1:3], board)
        if s[3] == '<':
            toSquare = fromSquare
            rotateDir = -1
        elif s[3] == '>':
            toSquare = fromSquare
            rotateDir = +1
        else:
            rotateDir = 0
            toSquare = Square.FromString(s[3:5], board)
        result = Move(fromSquare.piece, toSquare, rotateDir)
        result.unstackObelisk = (s[5:] == '-')
        return result

    def Matches(self, other):
        return other.fromSquare.HasSameCoords(self.fromSquare) and other.toSquare.HasSameCoords(self.toSquare) and other.rotateDir == self.rotateDir

    def TransferToBoard(self, board):
        """Returns a new Move that duplicates this one, but refers to the given board's squares and pieces.

        Assumes board is structurally identical (same types of pieces on same square positions) as the one on which
        this move was created."""
        return Move.FromString(str(self), board)

    def MovePiece(self):
        """Moves the given piece on the board.  Does not fire a laser."""
        self.piece.MoveTo(self.toSquare)
        self.piece.rotation = self.toRotation
        self.piece.FinishMakeMove(self)

    def TakeCompleteTurn(self, game):
        """Makes the move, fires the appropriate laser, and removes any hit piece."""
        game.MakeAndPushMove(self)
        game.FireLaser(self)
        game.PassToNextPlayer()

    def UndoMove(self):
        """Undoes all effects of a move, including a hit piece if one is noted."""
        # Add any extra behavior needed by a piece that was hit.
        if self.hitPiece:
            self.hitPiece.UndoHit(self)

        self.piece.MoveTo(self.fromSquare)
        self.piece.rotation = self.fromRotation
        if self.oldPiece:
            self.oldPiece.MoveTo(self.toSquare)

        # Add any extra behavior needed by the piece class.
        self.piece.FinishUndoMove(self)
        

class Game:
    def __init__(self):
        self.CreateBoard()
        self.activePlayer = None
        self.ResetToClassic()

    def CreateBoard(self):
        self.board = []
        for row in allRows:
            self.board.append([])
            for col in allCols:
                self.board[row].append(Square(row, col))

    def ResetGame(self):
        self.activePlayer = PLAYER_SILVER
        self.moveStack = []
        self.pharaohs = [None, None]
        self.playerNames = ['Human Player', 'Human Player']

        # Clear the board.
        for piece in allPieces(self.board):
            piece.MoveTo(None)

    def MoveTo(self, row, col, piece):
        piece.MoveTo(self.board[row][col])
        
    def ResetToClassic(self):
        self.ResetGame()
        self.MoveTo(0, 4, Obelisk(PLAYER_RED, True))
        self.MoveTo(0, 5, Pharaoh(PLAYER_RED, 180))
        self.MoveTo(0, 6, Obelisk(PLAYER_RED, True))
        self.MoveTo(0, 7, Pyramid(PLAYER_RED, 180))

        self.MoveTo(1, 2, Pyramid(PLAYER_RED, 270))

        self.MoveTo(2, 3, Pyramid(PLAYER_SILVER, 0))

        self.MoveTo(3, 0, Pyramid(PLAYER_RED, 90))
        self.MoveTo(3, 2, Pyramid(PLAYER_SILVER, 270))
        self.MoveTo(3, 4, Djed(PLAYER_RED, 90))
        self.MoveTo(3, 5, Djed(PLAYER_RED, 0))
        self.MoveTo(3, 7, Pyramid(PLAYER_RED, 180))
        self.MoveTo(3, 9, Pyramid(PLAYER_SILVER, 0))

        self.MirrorVertically()

        self.pharaohs[PLAYER_SILVER] = self.board[7][4].piece
        self.pharaohs[PLAYER_RED] = self.board[0][5].piece

    def Load(self, s):
        """Loads from the game in string s, in the same format produced by __str__()."""
        for line in s.splitlines():
            if line[0] == '[':
                pass  # Need to handle metadata later
            else:
                if line.find("1.") == 0:
                    # It's a list of moves.
                    for word in line.split():
                        print "'%s'" % word
                        if word[0].isdigit():
                            # It's a move number; skip it.
                            pass
                        elif word[0] == 'x':
                            # A piece was destroyed; we'll find that out automatically.
                            # A future implementation might like to validate that, though.
                            pass
                        else:
                            # An actual move; make a complete turn from it.
                            Move.FromString(word, self.board).TakeCompleteTurn(self)

    def __str__(self):
        # Metadata
        gameResult = str(int(self.pharaohs[PLAYER_RED].square == None)) + "-" + str(int(self.pharaohs[PLAYER_SILVER].square == None))
        result = '[Date "%s"]\n' % str(datetime.date.today())
        for p in players:
            result += '[%s "%s"]\n' % (colorName[p], self.playerNames[p])
                
        if self.IsOver():
            result += '[Result "%s"]\n' % gameResult

        # Moves
        moveNum = 1
        doingPlayer = PLAYER_SILVER
        for m in self.moveStack:
            if doingPlayer == PLAYER_SILVER:
                result += "%d. " % moveNum
                moveNum += 1
            result += str(m) + " "
            doingPlayer = 1 - doingPlayer

        # Result
        if self.IsOver():
            result += gameResult

        return result

    def MirrorVertically(self):
        """Creates pieces to duplicate the top half of the board to the bottom, swapping sides and rotations."""
        for row in range(0, numRows / 2):
            for col in allCols:
                thisPiece = self.board[row][col].piece
                if thisPiece:
                    newPiece = thisPiece.Duplicate()
                    newPiece.SwapColor()
                    newPiece.Rotate(180)
                    newPiece.MoveTo(self.board[numRows - 1 - row][numCols - 1 - col])

    def Pharaoh(self, color):
        return self.pharaohs[color]

    def IsOver(self):
        return self.pharaohs[PLAYER_SILVER].square == None or self.pharaohs[PLAYER_RED].square == None

    def FindLaserPath(self, color):
        """Simulates firing the laser of the indicated color.

        Returns a list of pairs of (row, col) indices for how the laser travels.
        If the last square is on the board, the piece at that location was hit.
        The first (row, col) will be off the board, indicating where the laser emanates from."""
        laserPositions = {PLAYER_SILVER: (8, 9), PLAYER_RED: (-1, 0)}
        laserDirections = {PLAYER_SILVER: (0, -1), PLAYER_RED: (0, 1)}

        (row, col) = laserPositions[color]
        (dirX, dirY) = laserDirections[color]

        result = [(row, col)]
        while True:
            # Move the laser in its indicated direction.
            row += dirY
            col += dirX

            # See if it went off the board.
            square = self.FindSquareInGrid(row, col)
            if square == None:
                result.append((row, col))
                return result

            # See if it hit a piece.
            elif square.piece:
                # Hits a piece.  See whether it reflects.
                result.append((row, col))
                (dirX, dirY) = square.piece.Reflects((dirX, dirY))
                if dirX == 0 and dirY == 0:
                    # No - it's hit!
                    return result

    def FindLaserPathEnd(self, laserPath):
        """Returns the piece hit by the laser, or None if none was hit."""
        square = self.FindSquareInGrid(laserPath[-1][0], laserPath[-1][1])
        if square:
            return square.piece
        else:
            return None

    def FindSquareInGrid(self, row, col):
        if IsLegalSquare(row, col):
            return self.board[row][col]
        else:
            return None

    def PassToNextPlayer(self):
        """Swaps the turn - sets the active player to the other one."""
        self.activePlayer = 1 - self.activePlayer

    def MakeAndPushMove(self, move):        
        move.MovePiece()
        self.moveStack.append(move)

    def UndoAndPopLastMove(self):
        self.moveStack.pop().UndoMove()

    def FireLaser(self, move):
        """Actually fires the laser; if a piece is hit, it's removed and placed in the move (for undoing)."""
        # Was anything hit?
        hitPiece = self.FindLaserPathEnd(self.FindLaserPath(self.activePlayer))
        if hitPiece:
            # Save it in the move, for later undoing.
            hitPiece.SaveHitInfo(move)
            # Delete it.
            hitPiece.DoHit(self)
            