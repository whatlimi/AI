"""
俄罗斯方块 — 使用 tkinter（标准库，无需额外 wheel）。
操作：← → 移动，↑ 旋转，↓ 加速下落，空格硬降，P 暂停，R 结束后重开。
"""
from __future__ import annotations

import random
import tkinter as tk
from tkinter import font as tkfont
from typing import List, Sequence, Tuple

COLS, ROWS = 10, 20
CELL = 28
SIDEBAR = 160
WIDTH = COLS * CELL + SIDEBAR + 16
HEIGHT = ROWS * CELL + 16

COLORS = {
    "I": "#50dcff",
    "O": "#ffe650",
    "T": "#c864ff",
    "S": "#50dc78",
    "Z": "#ff6464",
    "J": "#6496ff",
    "L": "#ffa050",
}

SHAPES: dict[str, List[Tuple[int, int]]] = {
    "I": [(0, 1), (1, 1), (2, 1), (3, 1)],
    "O": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "T": [(1, 0), (0, 1), (1, 1), (2, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
}


def cells_to_offsets(cells: Sequence[Tuple[int, int]]) -> List[Tuple[int, int]]:
    min_x = min(c[0] for c in cells)
    min_y = min(c[1] for c in cells)
    return [(x - min_x, y - min_y) for x, y in cells]


class Piece:
    def __init__(self, name: str) -> None:
        self.name = name
        self.offsets = cells_to_offsets(SHAPES[name])
        self.x = COLS // 2 - 2
        self.y = 0

    def cells(self) -> List[Tuple[int, int]]:
        return [(self.x + dx, self.y + dy) for dx, dy in self.offsets]

    def rotate(self, board: List[List[str | None]]) -> None:
        if self.name == "O":
            return
        new_offsets = cells_to_offsets([(dy, -dx) for dx, dy in self.offsets])
        old = self.offsets
        self.offsets = new_offsets
        if not valid_position(self, board):
            for kx, ky in ((-1, 0), (1, 0), (0, -1), (-1, -1), (1, -1), (-2, 0), (2, 0)):
                self.x += kx
                self.y += ky
                if valid_position(self, board):
                    return
                self.x -= kx
                self.y -= ky
            self.offsets = old


def valid_position(piece: Piece, board: List[List[str | None]]) -> bool:
    for x, y in piece.cells():
        if x < 0 or x >= COLS or y >= ROWS:
            return False
        if y >= 0 and board[y][x] is not None:
            return False
    return True


def merge_piece(piece: Piece, board: List[List[str | None]]) -> None:
    for x, y in piece.cells():
        if y >= 0:
            board[y][x] = piece.name


def clear_lines(board: List[List[str | None]]) -> int:
    kept = [row for row in board if any(c is None for c in row)]
    cleared = ROWS - len(kept)
    while len(kept) < ROWS:
        kept.insert(0, [None] * COLS)
    board[:] = kept
    return cleared


def new_bag() -> List[str]:
    names = list(SHAPES.keys())
    random.shuffle(names)
    return names


class TetrisApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("俄罗斯方块")
        self.root.resizable(False, False)
        ox, oy = 8, 8
        self._ox, self._oy = ox, oy
        self.canvas = tk.Canvas(
            self.root,
            width=WIDTH,
            height=HEIGHT,
            bg="#121218",
            highlightthickness=0,
        )
        self.canvas.pack()
        self.board: List[List[str | None]] = [[None] * COLS for _ in range(ROWS)]
        self.queue: List[str] = new_bag() + new_bag()
        self.piece = self._spawn()
        self.score = 0
        self.level = 1
        self.paused = False
        self.game_over = False
        self._fall_ms = 800
        self._after_id: str | None = None
        self._soft_drop = False
        self._root_binds()

        self.body_font = tkfont.Font(family="Segoe UI", size=11)
        self.title_font = tkfont.Font(family="Segoe UI", size=13, weight="bold")

        self._schedule_fall()
        self._draw()

    def _ensure_queue(self) -> None:
        while len(self.queue) < 8:
            self.queue.extend(new_bag())

    def _take_name(self) -> str:
        self._ensure_queue()
        return self.queue.pop(0)

    def _peek_name(self) -> str:
        self._ensure_queue()
        return self.queue[0]

    def _spawn(self) -> Piece:
        return Piece(self._take_name())

    def _root_binds(self) -> None:
        self.root.bind("<Left>", self._on_left)
        self.root.bind("<Right>", self._on_right)
        self.root.bind("<Up>", self._on_up)
        self.root.bind("<Down>", self._on_down_press)
        self.root.bind("<KeyRelease-Down>", self._on_down_release)
        self.root.bind("<space>", self._on_hard_drop)
        self.root.bind("<p>", self._on_pause)
        self.root.bind("<P>", self._on_pause)
        self.root.bind("<r>", self._on_restart)
        self.root.bind("<R>", self._on_restart)

    def _cancel_fall(self) -> None:
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None

    def _schedule_fall(self) -> None:
        self._cancel_fall()
        self._after_id = self.root.after(self._fall_ms, self._tick_fall)

    def _set_speed(self) -> None:
        self._fall_ms = max(120, 800 - (self.level - 1) * 60)
        if not self.paused and not self.game_over:
            self._schedule_fall()

    def _tick_fall(self) -> None:
        if self.paused or self.game_over:
            self._schedule_fall()
            return
        self.piece.y += 1
        if not valid_position(self.piece, self.board):
            self.piece.y -= 1
            self._lock_and_spawn()
        else:
            self._draw()
        self._schedule_fall()

    def _lock_and_spawn(self) -> None:
        merge_piece(self.piece, self.board)
        n = clear_lines(self.board)
        self.score += (100 * n * n) + (50 * n)
        if n:
            self.level = min(10, 1 + self.score // 1000)
            self._set_speed()
        self.piece = self._spawn()
        if not valid_position(self.piece, self.board):
            self.game_over = True
            self._cancel_fall()
        self._draw()

    def _move(self, dx: int) -> None:
        if self.paused or self.game_over:
            return
        self.piece.x += dx
        if not valid_position(self.piece, self.board):
            self.piece.x -= dx
        self._draw()

    def _on_left(self, _e: tk.Event | None = None) -> None:
        self._move(-1)

    def _on_right(self, _e: tk.Event | None = None) -> None:
        self._move(1)

    def _on_up(self, _e: tk.Event | None = None) -> None:
        if self.paused or self.game_over:
            return
        self.piece.rotate(self.board)
        self._draw()

    def _on_down_press(self, _e: tk.Event | None = None) -> None:
        if self.paused or self.game_over:
            return
        self._soft_drop = True
        self._cancel_fall()
        self._after_id = self.root.after(50, self._soft_repeat)

    def _soft_repeat(self) -> None:
        if not self._soft_drop or self.paused or self.game_over:
            self._soft_drop = False
            self._schedule_fall()
            return
        self.piece.y += 1
        if not valid_position(self.piece, self.board):
            self.piece.y -= 1
            self._lock_and_spawn()
        else:
            self._draw()
        self._after_id = self.root.after(50, self._soft_repeat)

    def _on_down_release(self, _e: tk.Event | None = None) -> None:
        self._soft_drop = False
        self._cancel_fall()
        self._schedule_fall()

    def _on_hard_drop(self, _e: tk.Event | None = None) -> None:
        if self.paused or self.game_over:
            return
        while valid_position(self.piece, self.board):
            self.piece.y += 1
        self.piece.y -= 1
        self._lock_and_spawn()

    def _on_pause(self, _e: tk.Event | None = None) -> None:
        if self.game_over:
            return
        self.paused = not self.paused
        if self.paused:
            self._cancel_fall()
        else:
            self._schedule_fall()
        self._draw()

    def _on_restart(self, _e: tk.Event | None = None) -> None:
        if not self.game_over:
            return
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.queue = new_bag() + new_bag()
        self.piece = self._spawn()
        self.score = 0
        self.level = 1
        self.game_over = False
        self.paused = False
        self._set_speed()
        self._draw()

    def _cell_rect(self, gx: int, gy: int) -> Tuple[int, int, int, int]:
        x1 = self._ox + gx * CELL
        y1 = self._oy + gy * CELL
        return x1 + 1, y1 + 1, x1 + CELL - 1, y1 + CELL - 1

    def _draw(self) -> None:
        self.canvas.delete("all")
        ox, oy = self._ox, self._oy
        self.canvas.create_rectangle(
            ox, oy, ox + COLS * CELL, oy + ROWS * CELL, fill="#282a3a", outline=""
        )
        for y in range(ROWS):
            for x in range(COLS):
                name = self.board[y][x]
                if name:
                    self.canvas.create_rectangle(
                        *self._cell_rect(x, y), fill=COLORS[name], outline="#1a1a22"
                    )
        if not self.game_over:
            for x, y in self.piece.cells():
                if y >= 0:
                    self.canvas.create_rectangle(
                        *self._cell_rect(x, y), fill=COLORS[self.piece.name], outline="#1a1a22"
                    )
        for gx in range(COLS + 1):
            self.canvas.create_line(ox + gx * CELL, oy, ox + gx * CELL, oy + ROWS * CELL, fill="#1e2030")
        for gy in range(ROWS + 1):
            self.canvas.create_line(ox, oy + gy * CELL, ox + COLS * CELL, oy + gy * CELL, fill="#1e2030")

        sx = ox + COLS * CELL + 12
        self.canvas.create_text(sx, oy + 8, anchor="nw", text="俄罗斯方块", fill="#e8e8f0", font=self.title_font)
        self.canvas.create_text(sx, oy + 40, anchor="nw", text=f"分数: {self.score}", fill="#c8cad8", font=self.body_font)
        self.canvas.create_text(sx, oy + 64, anchor="nw", text=f"等级: {self.level}", fill="#c8cad8", font=self.body_font)
        self.canvas.create_text(sx, oy + 110, anchor="nw", text="下一方块", fill="#c8cad8", font=self.body_font)
        nn = self._peek_name()
        py = oy + 138
        for dx, dy in cells_to_offsets(SHAPES[nn]):
            self.canvas.create_rectangle(
                sx + dx * 22,
                py + dy * 22,
                sx + dx * 22 + 20,
                py + dy * 22 + 20,
                fill=COLORS[nn],
                outline="#1a1a22",
            )
        hints = ["← → 移动", "↑ 旋转", "↓ 加速", "空格 硬降", "P 暂停"]
        hy = oy + 240
        for line in hints:
            self.canvas.create_text(sx, hy, anchor="nw", text=line, fill="#8a8fa0", font=self.body_font)
            hy += 22

        if self.paused:
            self.canvas.create_rectangle(ox, oy, ox + COLS * CELL, oy + ROWS * CELL, fill="#000000", stipple="gray50")
            self.canvas.create_text(
                ox + COLS * CELL // 2,
                oy + ROWS * CELL // 2,
                text="暂停\n按 P 继续",
                fill="#ffffff",
                font=self.title_font,
                justify="center",
            )
        if self.game_over:
            self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#000000", stipple="gray25")
            self.canvas.create_text(
                WIDTH // 2,
                HEIGHT // 2 - 24,
                text="游戏结束",
                fill="#ff6464",
                font=self.title_font,
            )
            self.canvas.create_text(
                WIDTH // 2,
                HEIGHT // 2 + 8,
                text=f"最终分数: {self.score}",
                fill="#ffffff",
                font=self.body_font,
            )
            self.canvas.create_text(
                WIDTH // 2,
                HEIGHT // 2 + 40,
                text="按 R 重新开始",
                fill="#b0b4c8",
                font=self.body_font,
            )

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    TetrisApp().run()


if __name__ == "__main__":
    main()
