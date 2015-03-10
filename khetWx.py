"""Khet
Implements the lasers-and-mirrors game of the same name,
which undoubtedly is protected in some way.

This is the main module for the wxWindows implementation of the game.
Core game classes are in khetGame.py.

--TJW 2008"""

import wx

from khetGame import *
from engines.raneb import *
import simpleSound

# Singleton variables used for drawing - all initialized later.
heavyBlackPen = None
stackedObeliskBrush = None
highlightingPen = None
selectedPen = None
laserMiddlePen = None
laserOutsidePen = None
laserHitMiddleBrush = None
laserHitOutsideBrush = None

# Turn phases.
PIECE_PHASE = 0
TARGET_PHASE = 1
CONFIRM_PHASE = 2  # While holding down the mouse (= keeping your fingers on the piece)
LASER_PHASE = 3
GAME_OVER_PHASE = 4
ENGINE_PHASE = 5  # Replaces Piece, Target, and Confirm phase when an engine is searching.


def GetPlayerBrush(color):
    if color == PLAYER_SILVER:
        return wx.LIGHT_GREY_BRUSH
    elif color == PLAYER_RED:
        return wx.RED_BRUSH
    else:
        return wx.GREY_BRUSH


class KhetWnd(wx.Window):
    def __init__(self, parent, id, pos=wx.DefaultPosition, size=wx.DefaultSize):
        wx.Window.__init__(self, parent, id, pos, size)
        self.SetBackgroundColour(wx.NamedColour('white'))
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)  # For use by BufferedPaintDC
        if wx.Platform == '__WXGTK__':
            self.font = wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL)
        else:
            self.font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL)
        self.SetFocus()
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouse)
        self.Bind(wx.EVT_CHAR, self.OnChar)

        self.highlightedSquare = None
        self.selectedPiece = None
        self.phase = None

        self.game = Game()
        self.ResetGame()

        self.engine = RanebEngine()        

    # Overall game state

    def ResetGame(self):
        self.phase = PIECE_PHASE
        self.hitPiece = None
        self.drawRotators = False
        self.overRotator = False
        self.HighlightSquare(None)
        self.SelectPiece(None)
        self.playerEngine = [None, None]
        self.filename = ""

        self.game.ResetToClassic()

        self.Refresh()

    def OnGameNew(self, event):
        self.filename = ""
        self.ResetGame()

    def OnSave(self, event):
        if self.filename == "":
            self.OnSaveAs(event)
        else:
            f = open(self.filename, 'w')
            f.write(str(self.game))

    def OnSaveAs(self, event):
        dlg = wx.FileDialog(self, "Save As", "", str(datetime.date.today()) + ".khet", "Khet saved games (*.khet)|*.khet",
                            wx.FD_SAVE or wx.FD_OVERWRITE_PROMPT or wx.FD_CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetPath()
            self.OnSave(None)
        dlg.Destroy()

    def OnOpen(self, event):
        dlg = wx.FileDialog(self, "Open Game", "", "", "Khet saved games (*.khet)|*.khet",
                            wx.FD_OPEN or wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetPath()
            f = open(self.filename, 'r')
            
            self.ResetGame()
            self.game.Load(f.read())
            self.Refresh()
        dlg.Destroy()

    # Input handlers

    def OnChar(self, event):
        key = event.GetKeyCode()
        if self.phase == CONFIRM_PHASE or self.phase == TARGET_PHASE:
            if key == wx.WXK_ESCAPE:
                self.Cancel()
        elif self.phase == LASER_PHASE:
            self.FinishLaserPhase()

    def OnMouse(self, event):
        square = self.FindSquareAt(event.m_x, event.m_y)
        
        if self.phase == PIECE_PHASE:
            # Mousing over squares to pick a piece to move.
            # So, find the square hit, and highlight it - but only if it's a legally movable piece.
            if square and not square.CanMovePiece(self.game.activePlayer):
                square = None
            self.HighlightSquare(square)

            # Now, if we've clicked on a highlighted square, select it and move to the next turn phase.
            if event.ButtonDown():
                if square:
                    self.SelectPiece(square.piece)
                    self.phase = TARGET_PHASE
                    self.HighlightSquare(None)
                    if self.UsingEngine():
                        self.engine.SetHintSquare(square)

        elif self.phase == TARGET_PHASE:
            # Mousing over the piece itself turns on the turning arrows.
            if square == self.selectedPiece.square:
                self.drawRotators = True
                self.HighlightSquare(None)
                self.overRotator = self.HitTestRotator(square, event.m_x, event.m_y)
                self.Refresh()
                
            # Mousing over target squares to move the piece to, OR turn handles to turn the piece.
            # So, highlight the hit square if it's a legal destination for the selected piece.
            else:
                self.drawRotators = False
                self.overRotator = False
                if not self.selectedPiece.CanMoveTo(square):
                    square = None
                self.HighlightSquare(square)

            # Now, if we've clicked on a highlighted square, select it and move to the next turn phase.
            if event.ButtonDown():
                if self.overRotator:
                    self.game.MakeAndPushMove(Move(self.selectedPiece, self.selectedPiece.square, self.overRotator))
                    self.phase = CONFIRM_PHASE
                elif square and square != self.selectedPiece.square:
                    self.game.MakeAndPushMove(Move(self.selectedPiece, square))
                    self.phase = CONFIRM_PHASE
                else:
                    # We've clicked somewhere else: cancel the move.
                    self.Cancel()

                if self.phase == CONFIRM_PHASE:
                    # Finish up
                    self.drawRotators = False
                    self.overRotator = False
                    if self.UsingEngine():
                        self.engine.SetHintMove(self.game.moveStack[-1])

                self.Refresh()

        elif self.phase == CONFIRM_PHASE:
            # Highlight the move's target square while over it.
            if square != self.game.moveStack[-1].toSquare:
                square = None
            self.HighlightSquare(square)

            # And when we release, make the move if we're still over the square.
            if event.ButtonUp():
                if square:
                    if not self.FinishConfirmMove(self.game.moveStack[-1]):
                        self.Cancel()
                    else:
                        self.SelectPiece(None)
                        self.GiveLastMoveToEngine()
                        self.phase = LASER_PHASE
                        self.Refresh()
                else:
                    # If we're not, cancel back to the start of the move.
                    self.Cancel()

        elif self.phase == LASER_PHASE:
            # Reset to next move on any click.
            if event.ButtonDown() or event.LeftDClick():  # DClick so we can rapidly progress through an engine/engine game.
                self.FinishLaserPhase()

    # Engine stuff

    def UsingEngine(self):
        return self.playerEngine[0] or self.playerEngine[1]

    def OnEngineSuggest(self, event):
        self.engine.Analyze(self.game)
        self.game.MakeAndPreConfirmMove(self.engine.GetMove())

    def OnEngineTakeOver(self, event):
        if self.playerEngine[self.game.activePlayer] == None:
            self.playerEngine[self.game.activePlayer] = self.engine
            self.game.playerNames[self.game.activePlayer] = self.engine.name
            self.StartAnalysis()

    def OnIdle(self, event):
        if self.UsingEngine():
            if self.engine.ContinueAnalysis(self.phase == ENGINE_PHASE):
                event.RequestMore()
                if self.phase == ENGINE_PHASE:
                    self.HighlightSquare(self.engine.GetMove().fromSquare)
            else:
                # Done analyzing.
                if self.phase == ENGINE_PHASE:
                    newMove = self.engine.GetMove()
                    print "Chose", newMove, newMove.oValue
                    self.MakeAndConfirmMove(newMove)
                    self.GiveLastMoveToEngine()  # So it knows we took it.
                    self.SetCursor(wx.STANDARD_CURSOR)
 
    # Highlighting

    def HighlightSquare(self, square):
        if square != self.highlightedSquare:
            if self.highlightedSquare:
                self.highlightedSquare.highlighted = False
            self.highlightedSquare = square
            if square:
                square.highlighted = True
            self.Refresh()
        
    def SelectPiece(self, piece):
        if piece != self.selectedPiece:
            if self.selectedPiece:
                self.selectedPiece.selected = False
            self.selectedPiece = piece
            if piece:
                piece.selected = True
            self.Refresh()

    # Move states

    def MakeAndPreConfirmMove(self, move):
        self.game.MakeAndPushMove(move)
        self.SelectPiece(move.piece)
        self.HighlightSquare(move.toSquare)
        self.phase = CONFIRM_PHASE

    def MakeAndConfirmMove(self, move):
        self.game.MakeAndPushMove(move)
        self.SelectPiece(move.piece)
        self.HighlightSquare(move.fromSquare)
        self.phase = LASER_PHASE

    def StartNextMove(self):
        self.game.PassToNextPlayer()
        self.HighlightSquare(None)
        self.SelectPiece(None)
        self.phase = PIECE_PHASE
        
    def FinishConfirmMove(self, move):
        """Does anything special to finish after the user has confirmed the move.

        Returns False if the move must be canceled."""
        if isinstance(move.piece, Obelisk):
            if move.oldPiece == None and move.piece.stacked:
                # Moving a stack to an empty square.
                # See if we already know what to do.
                if not hasattr(move, "unstackObelisk"):
                    # Not yet; ask the user if she wants to unstack.
                    dlg = wx.MessageDialog(self, "Do you want to unstack to the target square (No = move the stack)?",
                                           "Obelisk Move", wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION)
                    choice = dlg.ShowModal()
                    dlg.Destroy()
                    
                    if choice == wx.ID_YES:
                        # Unstack.
                        move.unstackObelisk = True
                        # The move has already been made, so we have to do the unstacking here.
                        move.piece.stacked = False
                        Obelisk(move.piece.color, False).MoveTo(move.fromSquare)
                    elif choice == wx.ID_NO:
                        move.unstackObelisk = False
                    elif choice == wx.ID_CANCEL:
                        return False
        return True

    def FinishLaserPhase(self):
        self.game.FireLaser(self.game.moveStack[-1])
        self.HighlightSquare(None)
        self.Refresh()

        # Is the game over?
        hitPiece = self.game.moveStack[-1].hitPiece
        if hitPiece and isinstance(hitPiece, Pharaoh):
            dlg = wx.MessageDialog(self, "%s wins!" % (colorName[1 - hitPiece.color]), "Game Over", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()

            self.phase = GAME_OVER_PHASE
            self.Refresh()

        else:
            self.StartNextMove()
            self.MaybeStartAnalysisPhase()

    def StartAnalysis(self):
        engine = self.playerEngine[self.game.activePlayer]
        self.SetCursor(wx.HOURGLASS_CURSOR)
        self.Update()
        self.phase = ENGINE_PHASE
        engine.StartApparentTime()
        engine.StartAnalysis(self.game)

    def GiveLastMoveToEngine(self):
        simpleSound.Play('laser.wav')
        if self.UsingEngine():
            self.engine.TakeNextMove(self.game.moveStack[-1])

    def MaybeStartAnalysisPhase(self):
        engine = self.playerEngine[self.game.activePlayer]
        if engine:
            engine.StartApparentTime()
            self.SetCursor(wx.HOURGLASS_CURSOR)
            self.Update()
            self.phase = ENGINE_PHASE

    def Cancel(self):
        if self.phase == CONFIRM_PHASE:
            # Undo...
            self.game.moveStack.pop().UndoMove()
            self.phase = TARGET_PHASE  # ...And drop further back in the next block.
            self.engine.SetHintMove(None)
            
        if self.phase == TARGET_PHASE:
            self.HighlightSquare(None)
            self.SelectPiece(None)
            self.drawRotators = False
            self.overRotator = False
            self.phase = PIECE_PHASE
            self.engine.SetHintSquare(None)

    # Drawing

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)
        dc.SetFont(self.font)

        for square in allSquares(self.game.board):
            self.DrawSquare(dc, square)

        if self.drawRotators and self.selectedPiece and self.selectedPiece.canRotate:
            self.DrawRotators(dc)

        if self.phase == LASER_PHASE:
            self.DrawLaser(dc)

    def SetPiecePenAndBrush(self, dc, piece):
        global heavyBlackPen
        dc.SetPen(heavyBlackPen)
        dc.SetBrush(GetPlayerBrush(piece.color))

    def DrawSquareBase(self, dc, piece, rect):
        """Draws a rectangular outline for the given piece, slightly inside the given rect.

        Takes the rect of the enclosing square.
        Returns the rect used to draw the piece rectangle."""
        self.SetPiecePenAndBrush(dc, piece)
        rect.Inflate(-5, -5)
        dc.DrawRectangle(rect.x, rect.y, rect.width, rect.height)
        return rect

    def TransformPoint(self, rect, piece, p):
        """Transform the given RealPoint (p) according to the piece's rotation, and map it from [-1, 1] to rect.

        piece must be a KhetRotatablePiece.
        Simplified for the four possible rotations used.
        Rotation is around (0, 0)."""
        if piece.rotation == 180:
            p.x, p.y = -p.x, -p.y
        elif piece.rotation == 90:
            p.x, p.y = -p.y, p.x
        elif piece.rotation == 270:
            p.x, p.y = p.y, -p.x

        p.x = (p.x / 2 + 0.5) * rect.width + rect.x
        p.y = (p.y / 2 + 0.5) * rect.height + rect.y
            
        return p
        
    def DrawTransformedLine(self, dc, rect, piece, p0, p1):
        p0 = self.TransformPoint(rect, piece, p0)
        p1 = self.TransformPoint(rect, piece, p1)
        dc.DrawLine(p0.x, p0.y, p1.x, p1.y)

    def DrawPiece(self, dc, piece, rect):
        """Draws the piece on the given DC, in a square that occupies the given rect."""
        rect = self.DrawSquareBase(dc, piece, rect)
        if isinstance(piece, Pharaoh):
            startAngle, endAngle = 0 + piece.rotation, 180 + piece.rotation
            rect.Inflate(-5, -5)
            dc.DrawEllipticArc(rect.x + 5, rect.y+ 5, rect.width - 10, rect.height - 10, startAngle, endAngle)
            dc.DrawLine(rect.x, rect.y + rect.height / 2, rect.x + rect.width, rect.y + rect.height / 2)
        if isinstance(piece, Obelisk):
            rect.Inflate(-5, -5)

            # Inner box
            dc.DrawRectangle(rect.x, rect.y, rect.width, rect.height)

            # Draw even smaller box.
            if piece.stacked:
                dc.SetBrush(stackedObeliskBrush)
            rect.Inflate(-10, -10)
            dc.DrawRectangle(rect.x, rect.y, rect.width, rect.height)
            rect.Inflate(10, 10)
        
            # X
            dc.DrawLine(rect.x, rect.y, rect.x + rect.width - 1, rect.y + rect.height - 1)
            dc.DrawLine(rect.x + rect.width - 1, rect.y, rect.x, rect.y + rect.height - 1)
        if isinstance(piece, Pyramid):
            rect.Inflate(-1, -1)

            self.DrawTransformedLine(dc, rect, piece, wx.RealPoint(-1, 1), wx.RealPoint(1, -1))
            self.DrawTransformedLine(dc, rect, piece, wx.RealPoint(0, 0), wx.RealPoint(1, 1))
        if isinstance(piece, Djed):
            rect.Inflate(-1, -1)

            m = 0.75
            self.DrawTransformedLine(dc, rect, piece, wx.RealPoint(-1, m), wx.RealPoint(m, -1))
            self.DrawTransformedLine(dc, rect, piece, wx.RealPoint(1, -m), wx.RealPoint(-m, 1))

    def DrawSquare(self, dc, square):
        rect = self.FindSquareRect(square.row, square.col)
        
        # Draw background.
        dc.SetBrush(GetPlayerBrush(square.color))
        if square.highlighted:
            dc.SetPen(highlightingPen)
        elif square.piece and square.piece.selected:
            dc.SetPen(selectedPen)
        else:
            dc.SetPen(wx.BLACK_PEN)
        dc.DrawRectangle(rect.x, rect.y, rect.width, rect.height)

        # Draw piece, if any.
        if square.piece:
            self.DrawPiece(dc, square.piece, rect)

        # Draw coordinates, for development and debugging.
        #dc.DrawText("(%d, %d)" % (square.row, square.col), rect.x, rect.y)
        
    def DrawRotators(self, dc):
        for direction in (-1, 1):
            rect = self.FindRotatorRect(self.selectedPiece.square, direction)

            # Draw the highglighting.
            if self.overRotator == direction:
                dc.SetPen(highlightingPen)
            else:
                dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetBrush(wx.LIGHT_GREY_BRUSH)
            dc.DrawRectangle(rect.x, rect.y, rect.width, rect.height)

            # Draw the arrow.
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.SetPen(wx.BLACK_PEN)
            if direction == -1:
                dc.DrawEllipticArc(rect.x, rect.y + rect.height * 0.3, rect.width, rect.height * 1.2, 45, 135)
                dc.DrawLine(rect.x + 2, rect.y + rect.height * 0.2, rect.x + 2, rect.y + rect.height / 2)
                dc.DrawLine(rect.x + 2, rect.y + rect.height / 2, rect.x + rect.width * 0.5, rect.y + rect.height / 2)
            else:
                dc.DrawEllipticArc(rect.x, rect.y - rect.height * 0.3 - 1, rect.width, rect.height * 1.2 - 1, 225, 315)
                dc.DrawLine(rect.x + 2, rect.y + rect.height * 0.8, rect.x + 2, rect.y + rect.height / 2)
                dc.DrawLine(rect.x + 2, rect.y + rect.height / 2, rect.x + rect.width * 0.5, rect.y + rect.height / 2)

    def DrawLaser(self, dc):
        """Graphically draws the laser path for the active player."""
        laserPath = self.game.FindLaserPath(self.game.activePlayer)
        hitPiece = self.game.FindLaserPathEnd(laserPath)
        (currX, currY) = self.FindSquareMiddle(laserPath.pop(0))
        for s in laserPath:
            (nextX, nextY) = self.FindSquareMiddle(s)

            # Draw the laser to the middle of that square.
            dc.SetPen(laserOutsidePen)
            dc.DrawLine(currX, currY, nextX, nextY)
            dc.SetPen(laserMiddlePen)
            dc.DrawLine(currX, currY, nextX, nextY)

            (currX, currY) = (nextX, nextY)            

        # See if it hit a piece.
        if hitPiece:
            # Draw a blob of fire on it.
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetBrush(laserHitOutsideBrush)
            dc.DrawEllipse(nextX - 10, nextY - 10, 22, 22)
            dc.SetBrush(laserHitMiddleBrush)
            dc.DrawEllipse(nextX - 8, nextY - 8, 19, 19)

    # Board display and geometry

    def FindSquareSize(self):
        """Returns the size of any board square, as a wx.Size."""
        (w, h) = self.GetSizeTuple()
        return wx.Size(w / numCols, h / numRows)
    
    def FindSquareAt(self, x, y):
        """Returns a reference to the square at the given pixel coordinates, or None if it's off the board."""
        squareSize = self.FindSquareSize()
        row = y / squareSize.height
        col = x / squareSize.width

        return self.game.FindSquareInGrid(row, col)

    def FindSquareRect(self, row, col):
        """Returns a wx.Rect bounding the square at the given row and column.

        If it's off the board, return a rect that's outside the board."""
        size = self.FindSquareSize()
        result = wx.Rect(col * size.width, row * size.height, size.width, size.height)
        return result

    def FindSquareMiddle(self, rowCol):
        """Returns the pixel coordinates of the middle of the square at the given row and column, as a tuple.

        If it's off the board, just return coordinates that are outside of the board."""
        rect = self.FindSquareRect(rowCol[0], rowCol[1])
        return (rect.x + rect.width / 2, rect.y + rect.width / 2)

    def FindRotatorRect(self, square, direction):
        """Returns the bounds of the rotator widget for the given square and direction, as a wx.Rect."""
        rect = self.FindSquareRect(square.row, square.col)
        if direction == -1:
            rect.Offset((2, 2))
        elif direction == 1:
            rect.Offset((rect.width - 2 - rect.width / 4, rect.height - 2 - rect.height / 4))
        rect.width /= 4
        rect.height /= 4
        return rect

    def HitTestRotator(self, square, x, y):
        """Checks to see if the point (x, y) is over a rotation widget in the given square.

        Returns -1 if (x, y) is over the counter-clockwise rotator in the specified square,
        1 if it's over the clockwise one, or 0 if it's not over either (or not over the square at all).
        Hack: Maps CCW to CW for Djeds, because the engines only think about CW rotations for Djeds."""
        for direction in (-1, 1):
            if self.FindRotatorRect(square, direction).Contains((x, y)):
                if isinstance(square.piece, Djed):
                    return 1
                else:
                    return direction
        return 0        


class AboutBox(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "About Khet", wx.DefaultPosition, (340,450))
        self.static = wx.StaticText(self, -1, __doc__, (1,160), (350, 250))
        self.button = wx.Button(self, 2001, "OK", (150,420), (50,-1))
        self.Fit()
        self.button.Bind(wx.EVT_BUTTON, self.OnOK)

    def OnOK(self, event):
        self.EndModal(wx.ID_OK)


class MyFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "Khet", wx.DefaultPosition, (650, 600))
        self.wnd = KhetWnd(self, -1)
        menu = wx.Menu()
        menu.Append(1001, "&New\tCtrl+N")
        menu.Append(1004, "&Open\tCtrl+O")
        menu.Append(1002, "&Save\tCtrl+S")
        menu.Append(1003, "Save &As...")
        menu.AppendSeparator()
        menu.Append(1005, "E&xit\tCtrl+X")
        menubar = wx.MenuBar()
        menubar.Append(menu, "&Game")

        menu = wx.Menu()
        menu.Append(1090, "&About...")
        menubar.Append(menu, "&Help")

        menu = wx.Menu()
        menu.Append(2000, "&Suggest")
        menu.Append(2001, "&Take Over\tCtrl+T")
        menubar.Append(menu, "&Engine")
        
        self.SetMenuBar(menubar)
        self.CreateStatusBar(2)
        self.Bind(wx.EVT_MENU, self.wnd.OnGameNew, id=1001)
        self.Bind(wx.EVT_MENU, self.wnd.OnSave, id=1002)
        self.Bind(wx.EVT_MENU, self.wnd.OnSaveAs, id=1003)
        self.Bind(wx.EVT_MENU, self.wnd.OnOpen, id=1004)
        self.Bind(wx.EVT_MENU, self.OnWindowClose, id=1005)
        self.Bind(wx.EVT_MENU, self.OnHelpAbout, id=1090)
        self.Bind(wx.EVT_MENU, self.wnd.OnEngineSuggest, id=2000)
        self.Bind(wx.EVT_MENU, self.wnd.OnEngineTakeOver, id=2001)

        self.Bind(wx.EVT_IDLE, self.wnd.OnIdle)
        
        self.wnd.OnGameNew(None)

    def OnHelpAbout(self, event):
        about = AboutBox(self)
        about.ShowModal()

    def OnWindowClose(self, event):
        self.Destroy()



class MyApp(wx.App):
    def OnInit(self):
        global heavyBlackPen, stackedObeliskBrush, highlightingPen, selectedPen, \
            laserMiddlePen, laserOutsidePen, laserHitMiddleBrush, laserHitOutsideBrush
        
        heavyBlackPen = wx.Pen(wx.BLACK, 3)
        stackedObeliskBrush = wx.Brush("YELLOW")
        highlightingPen = wx.Pen("YELLOW", 2, wx.SOLID)
        selectedPen = wx.Pen(wx.GREEN, 2)
        laserMiddlePen = wx.Pen(wx.Color(133, 6, 0), 1, wx.SOLID)
        laserOutsidePen = wx.Pen(wx.Color(173, 11, 4), 3, wx.SOLID)
        laserHitMiddleBrush = wx.Brush(wx.Color(133, 6, 0))
        laserHitOutsideBrush = wx.Brush(wx.Color(252, 99, 91))
        
        frame = MyFrame(None)
        self.SetTopWindow(frame)
        frame.Show(True)
        return True



if __name__ == '__main__':
    app = MyApp(0)
    app.MainLoop()

overview = __doc__
