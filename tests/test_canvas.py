import pytest

from henon2midi.output.canvas import AsciiCanvas, CanvasChanges


def test_palette_is_not_shuffled_for_every_canvas():
    before = list(AsciiCanvas.COLORS)
    AsciiCanvas(2, 2)
    AsciiCanvas(3, 3)
    assert list(AsciiCanvas.COLORS) == before
    assert list(AsciiCanvas.COLORS)[:3] == ["black", "red", "green"]


def test_draw_point_uses_the_current_color_and_joins_rows():
    canvas = AsciiCanvas(2, 2, color_order=["white", "red"])
    canvas.draw_point(0, 0, "X")
    canvas.set_color("red")
    canvas.draw_point(1, 1, "Y")

    assert canvas.generate_string() == (
        "\033[0m" "\033[0;37mX " "\n" " \033[0;31mY" "\033[0m"
    )


def test_next_color_walks_the_instance_order_and_wraps():
    canvas = AsciiCanvas(1, 1, color_order=["white", "red", "blue"])
    canvas.set_color("next")
    assert canvas.current_color == "red"
    canvas.set_color("next")
    assert canvas.current_color == "blue"
    canvas.set_color("next")
    assert canvas.current_color == "white"


def test_random_color_uses_the_supplied_choice(monkeypatch):
    monkeypatch.setattr(
        "henon2midi.output.canvas.random.choice", lambda _colors: "cyan"
    )
    canvas = AsciiCanvas(1, 1, color_order=["white", "cyan"])
    canvas.set_color("random")
    assert canvas.current_color == "cyan"


def test_unknown_color_and_empty_canvas_are_rejected():
    canvas = AsciiCanvas(1, 1, color_order=["white"])
    with pytest.raises(ValueError, match="not supported"):
        canvas.set_color("plaid")
    with pytest.raises(ValueError, match="at least 1"):
        AsciiCanvas(0, 4)


def test_changes_keep_the_latest_cell_until_they_are_consumed():
    canvas = AsciiCanvas(2, 2, color_order=["white", "red"])
    canvas.draw_point(0, 0, "X")
    canvas.set_color("red")
    canvas.draw_point(0, 0, "Y")
    assert "Y" in canvas.generate_string()
    assert canvas.consume_changes() == CanvasChanges(False, ((0, 0, "Y", "red"),))
    assert canvas.consume_changes() == CanvasChanges(False, ())


def test_clear_forgets_cells_drawn_before_it():
    canvas = AsciiCanvas(2, 1, color_order=["white", "red"])
    canvas.draw_point(0, 0, "X")
    canvas.clear()
    canvas.set_color("red")
    canvas.draw_point(1, 0, "Y")

    assert canvas.consume_changes() == CanvasChanges(True, ((1, 0, "Y", "red"),))
    assert canvas.painted_cells() == ((1, 0, "Y", "red"),)


def test_clear_erases_points_and_returns_to_white():
    canvas = AsciiCanvas(2, 1, color_order=["white", "red"])
    canvas.set_color("red")
    canvas.draw_point(0, 0, "█")
    canvas.clear()
    assert canvas.current_color == "white"
    assert canvas.generate_string() == "\033[0m  \033[0m"
    assert "█" not in canvas.generate_string()


def test_each_canvas_keeps_its_own_color_cycle(monkeypatch):
    orders = [["white", "red"], ["white", "blue"]]

    def use_next_order(values):
        values[:] = orders.pop(0)

    monkeypatch.setattr("henon2midi.output.canvas.random.shuffle", use_next_order)
    first = AsciiCanvas(1, 1)
    second = AsciiCanvas(1, 1)
    first.set_color("next")
    second.set_color("next")
    assert first.current_color == "red"
    assert second.current_color == "blue"
