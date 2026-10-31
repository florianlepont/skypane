"""Landscape flight card renders natively at the profile's size."""
import dataclasses
from collections import Counter

import pytest
from PIL import ImageChops

from server import device_config, hardware
from server import panel_format as pf
from server.plane.render import landscape, landscape_card as lc

PROFILE = hardware.get_profile(hardware.SIM_LANDSCAPE_KEY, {hardware.SIM_ENV_VAR: "1"})
SIZE = (PROFILE.width, PROFILE.height)

FLIGHT = {"hex": "3985a7", "callsign": "AF1380", "aircraft_type": "B738"}
PREVIOUS_FLIGHT = {"hex": "4a1b02", "callsign": "VLG6PD", "aircraft_type": "A320"}
ROUTE = {
    "airline_name": "Transavia France",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "PMI",
    "destination_city": "Palma de Mallorca",
    "callsign_iata": "TO16VB",
}
PREVIOUS_ROUTE = {
    "airline_name": "Vueling Airlines",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "BCN",
    "destination_city": "Barcelona",
    "callsign_iata": "VY8163",
}
LONG_ROUTE = {
    "airline_name": "Compagnie Nationale Royale Air Maroc Express",
    "origin_iata": "SCQ",
    "origin_city": "Santiago de Compostela–Rosalía de Castro",
    "destination_iata": "ORY",
    "destination_city": "Paris",
    "callsign_iata": "AT9051",
}
THEMES = sorted(device_config.THEMES)
BAND_THEMES = [t for t in THEMES if device_config.theme_is_band(t)]


def card(state="departing", size=SIZE, **kwargs):
    kwargs.setdefault("route", ROUTE)
    return lc.build_card_canvas(size, FLIGHT, state, **kwargs)


@pytest.mark.parametrize("state", ["departing", "arriving"])
def test_size_packing_and_palette(state):
    canvas = card(state)
    assert canvas.size == SIZE
    assert len(pf.pack_panel(canvas)) == 192000
    assert set(canvas.tobytes()) <= set(pf.INDEX_TO_NIBBLE)


def test_deterministic():
    assert card().tobytes() == card().tobytes()


def test_unknown_state_rejected():
    with pytest.raises(ValueError):
        card("empty")


@pytest.mark.parametrize("theme_id", THEMES)
@pytest.mark.parametrize("state", ["departing", "arriving"])
def test_every_theme_renders_with_state_background(theme_id, state):
    canvas = card(state, theme_id=theme_id)
    bg = device_config.theme_background_index(state, theme_id)
    counts = Counter(canvas.tobytes())
    assert counts[bg] >= max(c for v, c in counts.items() if v != bg)




def band_columns(canvas, theme_id):
    """Columns of the canvas that hold band-coloured pixels in row `y`."""
    band = device_config.theme_band_index(theme_id)
    width, height = canvas.size
    data = canvas.tobytes()
    return [[x for x in range(width) if data[y * width + x] == band] for y in range(height)]


def right_corner(canvas):
    width, height = canvas.size
    margin = lc.common.margin_for(canvas.size)
    return canvas.crop((width - margin, 0, width, height // 4))


@pytest.mark.parametrize("theme_id", THEMES)
def test_band_only_for_band_themes(theme_id):
    colours = set(right_corner(card(theme_id=theme_id)).tobytes())
    if device_config.theme_is_band(theme_id):
        assert device_config.theme_band_index(theme_id) in colours
    else:
        bg = device_config.theme_background_index("departing", theme_id)
        assert colours <= {bg, pf.IDX_WHITE}


@pytest.mark.parametrize("size", [SIZE, (640, 384), (1024, 600)])
@pytest.mark.parametrize("theme_id", [t for t in BAND_THEMES if not device_config.theme_band_dithered(t) and not device_config.theme_dithered(t)])
def test_band_crosses_whole_canvas(theme_id, size):
    canvas = lc.build_card_canvas(size, FLIGHT, "departing", route=ROUTE, theme_id=theme_id)
    columns = band_columns(canvas, theme_id)
    width, height = size
    assert min(columns[0], default=width) > width * 0.5
    assert max(columns[0], default=0) > width * 0.9
    assert min(columns[-1], default=width) < width * 0.4
    assert max(columns[-1], default=0) > width * 0.6
    assert min(min(c, default=width) for c in columns) < width * 0.4
    assert max(max(c, default=0) for c in columns) > width * 0.9
    for y in range(0, height, 8):
        assert columns[y], "band missing on row %d" % y


@pytest.mark.parametrize("size", [SIZE, (640, 384), (1024, 600)])
def test_band_slants_down_left_like_portrait(size):
    centers = [lc.band_center(size, y) for y in (0, size[1] / 2, size[1])]
    assert centers[0] > centers[1] > centers[2]
    shift = (centers[0] - centers[2]) / size[1]
    portrait = (lc.style.BAND_TOP_LEFT_FRAC - lc.style.BAND_BOT_LEFT_FRAC) * pf.WIDTH / pf.HEIGHT
    assert shift == pytest.approx(portrait)


@pytest.mark.parametrize("size", [SIZE, (640, 384), (1024, 600)])
@pytest.mark.parametrize("theme_id", BAND_THEMES)
@pytest.mark.parametrize("state", ["departing", "arriving"])
def test_band_text_stays_inside_band(theme_id, state, size):
    base = lc.build_card_canvas(size, FLIGHT, state, route=ROUTE, theme_id=theme_id)
    other = lc.build_card_canvas(size, FLIGHT, state, route=LONG_ROUTE, theme_id=theme_id)
    with_prev = lc.build_card_canvas(
        size, FLIGHT, state, route=ROUTE, theme_id=theme_id,
        previous_flight=PREVIOUS_FLIGHT, previous_route=PREVIOUS_ROUTE, previous_state="arriving",
    )
    illustration_right = lc.card_geometry(size, True).illustration_right
    for changed, x_min in ((other, illustration_right), (with_prev, 0)):
        diff = ImageChops.difference(base.convert("RGB"), changed.convert("RGB")).convert("L").point(
            lambda v: 255 if v else 0
        )
        box = diff.getbbox()
        assert box is not None
        pixels = diff.load()
        for y in range(box[1], box[3]):
            left, right = lc.band_edges(size, y + 0.5)
            for x in range(max(box[0], x_min), box[2]):
                if pixels[x, y]:
                    assert left - 1 <= x <= right + 1, "changed text pixel off the band at (%d, %d)" % (x, y)


@pytest.mark.parametrize("theme_id", BAND_THEMES)
def test_band_never_white_so_white_text_reads(theme_id):
    assert device_config.theme_band_index(theme_id) != pf.IDX_WHITE


@pytest.mark.parametrize("theme_id", BAND_THEMES)
def test_text_column_fits_inside_band(theme_id):
    geom = lc.card_geometry(SIZE, True)
    mid = SIZE[1] / 2
    left, right = lc.band_edges(SIZE, mid)
    assert left < geom.text_left < geom.text_right < right
    assert geom.overlay_right < lc.band_edges(SIZE, SIZE[1])[0]


@pytest.mark.parametrize("theme_id", BAND_THEMES)
def test_band_overlays_stay_left_of_band(theme_id):
    base = card(theme_id=theme_id)
    box = ImageChops.difference(
        base.convert("RGB"), card(theme_id=theme_id, source_fault=True, battery_low=True).convert("RGB")
    ).getbbox()
    assert box is not None
    assert box[2] <= lc.band_edges(SIZE, SIZE[1])[0]


@pytest.mark.parametrize("theme_id", BAND_THEMES)
def test_band_card_is_deterministic(theme_id):
    assert card(theme_id=theme_id).tobytes() == card(theme_id=theme_id).tobytes()


@pytest.mark.parametrize("size", [(640, 384), (1024, 600)])
@pytest.mark.parametrize("theme_id", BAND_THEMES)
def test_band_size_sweep_renders(theme_id, size):
    canvas = lc.build_card_canvas(
        size, FLIGHT, "arriving", route=LONG_ROUTE, theme_id=theme_id,
        previous_flight=PREVIOUS_FLIGHT, previous_route=PREVIOUS_ROUTE, previous_state="departing",
        source_fault=True, battery_low=True,
    )
    assert canvas.size == size


def test_long_route_fits_every_theme_and_state():
    for state in ("departing", "arriving"):
        for theme_id in ("white", "band_red", "grey"):
            assert card(state, route=LONG_ROUTE, theme_id=theme_id).size == SIZE


def test_text_column_changes_with_route():
    assert card(route=ROUTE).tobytes() != card(route=LONG_ROUTE).tobytes()


def test_previous_strip_optional_and_confined_to_text_column():
    without = card()
    with_prev = card(
        previous_flight=PREVIOUS_FLIGHT, previous_route=PREVIOUS_ROUTE, previous_state="arriving"
    )
    assert without.tobytes() != with_prev.tobytes()
    box = ImageChops.difference(without.convert("RGB"), with_prev.convert("RGB")).getbbox()
    assert box is not None
    assert box[3] > SIZE[1] * 0.8


def overlay_box(**kwargs):
    base = card()
    over = card(**kwargs)
    return ImageChops.difference(base.convert("RGB"), over.convert("RGB")).getbbox()


@pytest.mark.parametrize("kwargs", [{"battery_low": True}, {"source_fault": True}])
def test_overlays_in_bottom_left_corner_clear_of_text(kwargs):
    box = overlay_box(**kwargs)
    assert box is not None
    geom = lc.card_geometry(SIZE, False)
    assert box[0] >= geom.margin
    assert box[2] <= geom.text_left
    assert box[1] >= SIZE[1] * 0.85


def test_overlays_scale_with_canvas():
    small = (640, 384)
    base = lc.build_card_canvas(small, FLIGHT, "departing", route=ROUTE)
    over = lc.build_card_canvas(small, FLIGHT, "departing", route=ROUTE, battery_low=True)
    box = ImageChops.difference(base.convert("RGB"), over.convert("RGB")).getbbox()
    assert box is not None and box[1] >= small[1] * 0.85 and box[2] <= small[0] * 0.5


def test_second_size_renders_natively():
    canvas = lc.build_card_canvas((640, 384), FLIGHT, "arriving", route=LONG_ROUTE)
    assert canvas.size == (640, 384)
    assert len(pf.pack_panel(canvas)) == 640 * 384 // 2


STATES = ["departing", "arriving", "empty", "quiet_hours", "display_off", "battery_empty"]


def entry(profile=PROFILE, state="departing", **kwargs):
    kwargs.setdefault("route", ROUTE)
    return landscape.build_landscape_canvas(profile, FLIGHT, state, **kwargs)


@pytest.mark.parametrize("state", STATES)
def test_entry_point_renders_every_state_natively(state):
    canvas = entry(state=state, quiet_hours_until="07:00")
    assert canvas.size == SIZE
    assert len(pf.pack_panel(canvas)) == 192000


def test_entry_point_missing_flight_is_empty_screen():
    canvas = landscape.build_landscape_canvas(PROFILE, None, "departing")
    assert canvas.tobytes() == entry(state="empty").tobytes()


def test_battery_empty_ignores_other_arguments():
    plain = entry(state="battery_empty")
    noisy = entry(state="battery_empty", theme_id="band_red", source_fault=True, battery_low=True)
    assert plain.tobytes() == noisy.tobytes()


def test_entry_point_unknown_state_rejected():
    with pytest.raises(ValueError):
        entry(state="landing")


def test_portrait_profile_rejected():
    portrait = hardware.get_profile(hardware.LEGACY_KEY)
    with pytest.raises(ValueError):
        entry(profile=portrait)


@pytest.mark.parametrize("size", [(640, 384), (1024, 600)])
@pytest.mark.parametrize("state", STATES)
def test_entry_point_follows_profile_size(size, state):
    profile = dataclasses.replace(PROFILE, width=size[0], height=size[1])
    canvas = entry(profile=profile, state=state, quiet_hours_until="07:00")
    assert canvas.size == size
    assert len(pf.pack_panel(canvas)) == size[0] * size[1] // 2
