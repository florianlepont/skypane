"""Manual-QA preview CLI: `python3 -m server.plane.render --state ... --out
... --preview ...`. No live enrichment lookup of its own - that is
poll_loop.py's job - so `build_parser()`'s route-shaping flags hand-build
a synthetic `_PREVIEW_ROUTE`/`_PREVIEW_PREVIOUS_ROUTE` dict instead.
"""
import argparse
import hashlib
import sys

from server import device_config
from server import panel_format as pf
from server.plane import dither, enrich, runway_config
from server.plane.render import layout

# Manual-QA-only sample routes - this CLI has no live enrichment lookup of
# its own (that's poll_loop.py's job); these are plausible-looking hits so
# `--preview` without `--no-route` shows the resolved-route text layout
# rather than always previewing the fallback. `callsign_iata` is a
# synthetic sample value in both dicts, in each route's own airline's
# real IATA prefix - not a real adsbdb-resolved identifier - so a plain
# preview exercises tier 1 end to end.
_PREVIEW_ROUTE = {
    "airline_name": "Air France",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "JFK",
    "destination_city": "New York",
    "callsign_iata": "AF1006",
}
_PREVIEW_PREVIOUS_ROUTE = {
    "airline_name": "Vueling Airlines",
    "origin_iata": "ORY",
    "origin_city": "Paris",
    "destination_iata": "BCN",
    "destination_city": "Barcelona",
    "callsign_iata": "VY1234",
}


def _add_flight_arguments(parser):
    """--state and the fake-callsign/hex flags for both cards."""
    parser.add_argument(
        "--state",
        choices=["departing", "arriving", "empty", "quiet_hours", "display_off", "battery_empty"],
        default="empty",
    )
    parser.add_argument("--callsign", default=None, help="Manual QA only: fake callsign for a departing/arriving preview.")
    parser.add_argument("--hex", default="000000", help="Manual QA only: fake ICAO hex (used if --callsign is omitted).")
    parser.add_argument(
        "--previous-callsign",
        default=None,
        help="Manual QA only (D-26): fake callsign for the previous-flight card. Omit to preview a single-flight panel.",
    )
    parser.add_argument(
        "--previous-hex", default="111111", help="Manual QA only: fake ICAO hex for the previous flight."
    )


def _add_output_arguments(parser):
    """Where the render goes: the packed .bin and/or a viewable PNG preview."""
    parser.add_argument("--out", help="Write the packed 960,000-byte .bin to this path.")
    parser.add_argument(
        "--preview",
        metavar="PATH",
        help="Also write a viewable PNG preview. WARNING (D-P2-03): preview colours "
             "are nominal render-internal RGB triples, not a colour-accurate panel preview.",
    )


def _add_route_shaping_arguments(parser):
    """Flags that reshape the synthetic preview route (or skip route
    enrichment entirely) for a departing/arriving preview, plus the
    standalone calibration-preview diagnostic.
    """
    parser.add_argument(
        "--no-route",
        action="store_true",
        help="Manual QA only (02-04): preview the enrichment-miss fallback ('Route unavailable') "
             "instead of the default sample resolved-route preview.",
    )
    parser.add_argument(
        "--airline",
        metavar="NAME",
        default=None,
        help="Manual QA only (D-04, Phase 7 07-01): override _PREVIEW_ROUTE's airline_name for a "
             "departing/arriving preview, so a long/real airline name is a flag rather than a "
             "hand-built dict. Ignored when --no-route is also given.",
    )
    parser.add_argument(
        "--city",
        metavar="NAME",
        default=None,
        help="Manual QA only (D-04, Phase 7 07-01): override the state-appropriate city in "
             "_PREVIEW_ROUTE (destination_city for --state departing, origin_city for --state "
             "arriving) for a departing/arriving preview. Ignored when --no-route is also given.",
    )
    parser.add_argument(
        "--calibration-preview",
        metavar="DIR",
        default=None,
        help="D-13 (Phase 7 07-01): write dither.write_calibration_preview(DIR)'s single "
             "palette-swatches.png monitor-side calibration artifact into DIR, print its path, and "
             "exit - no panel is rendered when this flag is given.",
    )
    parser.add_argument(
        "--preview-airline-only",
        action="store_true",
        help="Manual QA only (D-06, quick task 260827-hyy; tier updated Phase 8 08-04 D-10): preview "
             "the airline-only intermediate render state (airline known via the callsign's ICAO "
             "prefix, destination genuinely unknown - line 1 is omitted entirely (D-10 tier 3), only "
             "'{airline} · {type}' is drawn, at the airline's own illustration). Takes precedence "
             "over --no-route when both are given.",
    )
    parser.add_argument(
        "--no-identifier",
        action="store_true",
        help="Manual QA only (D-10 tier 2, Phase 8 08-04): strip the preview route's callsign_iata "
             "identifier so a departing/arriving preview forces tier 2 (title-case direction word + "
             "city, no identifier) instead of the default tier 1. No effect when the route is "
             "already None (--no-route won) or when --preview-airline-only is also given (that route "
             "has no cities and lands on tier 3 regardless) - both combinations are harmless no-ops.",
    )


def _add_state_arguments(parser):
    """Theme/runway registry ids plus the device/server-health indicator
    flags and the quiet-hours end-time preview flag.
    """
    parser.add_argument(
        "--theme", choices=device_config.THEME_IDS, default=device_config.DEFAULT_THEME_ID,
        help="CFG-01: theme id from server/device_config.py's THEMES registry.",
    )
    parser.add_argument(
        "--runway", choices=device_config.RUNWAY_IDS, default=device_config.DEFAULT_RUNWAY_ID,
        help="CFG-12: tracked-runway id from server/device_config.py's RUNWAYS registry.",
    )
    parser.add_argument(
        "--source-fault", action="store_true",
        help="Manual QA only (CFG-05): preview the source-fault alert badge, as if every ADS-B "
             "provider had failed.",
    )
    parser.add_argument(
        "--battery-low",
        action="store_true",
        help="Manual QA only (D-04/D-06): preview the low-battery icon in the panel's bottom-left corner.",
    )
    parser.add_argument(
        "--quiet-hours-until",
        default=device_config.DEFAULT_QUIET_HOURS_END,
        help="Manual QA only (D-05/D-06): the local Europe/Paris wall-clock end time the "
             "--state quiet_hours preview's 'Back at' line shows. Ignored for every other --state, "
             "including --state display_off, which never shows a return-time value (D-03/D-04).",
    )


def build_parser():
    """Assemble the CLI's option groups in their historical order, so
    `--help` output stays byte-identical to before the 39-08 split.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    _add_flight_arguments(parser)
    _add_output_arguments(parser)
    _add_route_shaping_arguments(parser)
    _add_state_arguments(parser)
    return parser


def _preview_route_for(args, preview_route, callsign_iata_owner):
    """Shape one card's route dict (main or previous) from `args`, mirroring
    the tier/override precedence documented on `--preview-airline-only`,
    `--no-route`, `--no-identifier`, `--airline` and `--city`: airline-only
    beats no-route, no-identifier strips callsign_iata, and airline/city
    only apply to the main card's own route dict (`callsign_iata_owner`
    distinguishes the main card, which honours them, from the previous
    card, which never took them historically).
    """
    if args.preview_airline_only:
        route = enrich.airline_only_route(preview_route["airline_name"])
    elif args.no_route:
        route = None
    else:
        route = preview_route
    if args.no_identifier and route is not None:
        route = dict(route)
        route["callsign_iata"] = None
    if callsign_iata_owner and route is not None and (args.airline or args.city):
        route = dict(route)
        if args.airline:
            route["airline_name"] = args.airline
        if args.city:
            city_field = "destination_city" if args.state == runway_config.STATE_DEPARTING else "origin_city"
            route[city_field] = args.city
    return route


def _preview_inputs(args):
    """Build the (flight, route, previous_flight, previous_route,
    previous_state) tuple `layout.build_canvas()` needs, from the CLI's
    fake-callsign/route-shaping flags. All five stay `None` for a
    non-aircraft `--state` (empty/quiet_hours/display_off/battery_empty) -
    the quiet-hours state has no flight to enrich, exactly like empty, so
    membership is tested against the two real aircraft states rather than
    a negative list a future third non-flight state would have to be
    remembered into.
    """
    if args.state not in (runway_config.STATE_DEPARTING, runway_config.STATE_ARRIVING):
        return None, None, None, None, None

    flight = {"hex": args.hex, "callsign": args.callsign}
    # --airline/--city (callsign_iata_owner=True) apply only to the main
    # card's route, matching the original single-function implementation.
    route = _preview_route_for(args, _PREVIEW_ROUTE, callsign_iata_owner=True)

    previous_flight = None
    previous_route = None
    previous_state = None
    if args.previous_callsign:
        previous_flight = {"hex": args.previous_hex, "callsign": args.previous_callsign}
        previous_route = _preview_route_for(args, _PREVIEW_PREVIOUS_ROUTE, callsign_iata_owner=False)
        previous_state = runway_config.STATE_ARRIVING if args.state == runway_config.STATE_DEPARTING else runway_config.STATE_DEPARTING

    return flight, route, previous_flight, previous_route, previous_state


def _render_preview(args, flight, route, previous_flight, previous_route, previous_state):
    """Build the canvas and pack it, exiting on an internal size mismatch."""
    canvas = layout.build_canvas(
        flight,
        args.state,
        route=route,
        previous_flight=previous_flight,
        previous_route=previous_route,
        previous_state=previous_state,
        theme_id=args.theme,
        runway_id=args.runway,
        source_fault=args.source_fault,
        battery_low=args.battery_low,
        quiet_hours_until=args.quiet_hours_until,
    )
    data = pf.pack_panel(canvas)
    if len(data) != pf.IMAGE_BYTES:
        sys.exit("internal error: generated %d bytes, expected %d" % (len(data), pf.IMAGE_BYTES))
    return canvas, data


def _write_outputs(args, canvas, data):
    """Write --out/--preview as requested, or print the render's sha256
    when neither was given. Prints the SYNTHETIC-panel reminder and the
    preview colour-accuracy warning at the same points as before the split.
    """
    if args.out:
        with open(args.out, "wb") as fh:
            fh.write(data)
        digest = hashlib.sha256(data).hexdigest()
        print("wrote %s (%d bytes, state=%s)" % (args.out, len(data), args.state))
        print("sha256 %s" % digest)
        # A forced render's most common failure is a human forgetting to
        # restart skypane-poll.timer afterward - the tool doing the
        # forcing is the right place to say so. The unit is
        # deploy/skypane-poll.timer.
        if args.airline or args.city or args.no_route:
            print(
                "REMINDER: this panel is SYNTHETIC (--airline/--city/--no-route was used) - "
                "restart skypane-poll.timer after testing, or the frame stays frozen on this "
                "test image indefinitely."
            )

    if args.preview:
        print(
            "WARNING: preview colours are nominal render-internal RGB triples "
            "(D-P2-03) - not a colour-accurate preview of the physical panel."
        )
        canvas.convert("RGB").save(args.preview)
        print("wrote preview %s" % args.preview)

    if not args.out and not args.preview:
        digest = hashlib.sha256(data).hexdigest()
        print("rendered %d bytes (state=%s), sha256 %s (pass --out/--preview to write a file)"
              % (len(data), args.state, digest))


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.calibration_preview:
        # A standalone diagnostic action, not mixed with a panel render -
        # no --state/--out/--preview handling below is reached.
        for path in dither.write_calibration_preview(args.calibration_preview):
            print("wrote %s" % path)
        return 0

    flight, route, previous_flight, previous_route, previous_state = _preview_inputs(args)
    canvas, data = _render_preview(args, flight, route, previous_flight, previous_route, previous_state)
    _write_outputs(args, canvas, data)
    return 0
