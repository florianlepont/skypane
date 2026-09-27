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


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
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
    parser.add_argument("--out", help="Write the packed 960,000-byte .bin to this path.")
    parser.add_argument(
        "--preview",
        metavar="PATH",
        help="Also write a viewable PNG preview. WARNING (D-P2-03): preview colours "
             "are nominal render-internal RGB triples, not a colour-accurate panel preview.",
    )
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
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.calibration_preview:
        # A standalone diagnostic action, not mixed with a panel render -
        # no --state/--out/--preview handling below is reached.
        for path in dither.write_calibration_preview(args.calibration_preview):
            print("wrote %s" % path)
        return 0

    flight = None
    route = None
    previous_flight = None
    previous_route = None
    previous_state = None
    # The quiet-hours state has no flight to enrich, exactly like empty -
    # test membership against the two real aircraft states rather than a
    # second negative list (`!= "empty"`) that a future third non-flight
    # state would have to be remembered into.
    if args.state in (runway_config.STATE_DEPARTING, runway_config.STATE_ARRIVING):
        flight = {"hex": args.hex, "callsign": args.callsign}
        # --preview-airline-only takes precedence over --no-route when both
        # are given (documented in --preview-airline-only's own help text
        # above).
        if args.preview_airline_only:
            route = enrich.airline_only_route(_PREVIEW_ROUTE["airline_name"])
        elif args.no_route:
            route = None
        else:
            route = _PREVIEW_ROUTE
        # --no-identifier strips callsign_iata so a departing/arriving
        # preview forces tier 2. No-op when route is already None
        # (--no-route won, nothing to strip) or when it is the
        # airline-only route (--preview-airline-only won; that route's
        # callsign_iata is already None and it has no cities regardless, so
        # stripping it again changes nothing). Never mutates _PREVIEW_ROUTE
        # itself.
        if args.no_identifier and route is not None:
            route = dict(route)
            route["callsign_iata"] = None
        # --airline/--city override _PREVIEW_ROUTE's own fields so a
        # long/real name is a flag rather than a hand-built dict.
        # --no-route continues to win over both - route is already None above
        # and stays None here. Never mutates _PREVIEW_ROUTE itself.
        if route is not None and (args.airline or args.city):
            route = dict(route)
            if args.airline:
                route["airline_name"] = args.airline
            if args.city:
                city_field = (
                    "destination_city" if args.state == runway_config.STATE_DEPARTING
                    else "origin_city"
                )
                route[city_field] = args.city
        if args.previous_callsign:
            previous_flight = {"hex": args.previous_hex, "callsign": args.previous_callsign}
            if args.preview_airline_only:
                previous_route = enrich.airline_only_route(_PREVIEW_PREVIOUS_ROUTE["airline_name"])
            elif args.no_route:
                previous_route = None
            else:
                previous_route = _PREVIEW_PREVIOUS_ROUTE
            if args.no_identifier and previous_route is not None:
                previous_route = dict(previous_route)
                previous_route["callsign_iata"] = None
            previous_state = runway_config.STATE_ARRIVING if args.state == runway_config.STATE_DEPARTING else runway_config.STATE_DEPARTING

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

    return 0
