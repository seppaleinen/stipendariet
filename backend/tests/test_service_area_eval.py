"""Phase 0 eval harness for the service-area extraction pipeline.

Runs 40 labelled cases end-to-end against `extract_service_area` with the LLM
mocked (chat_completion). The real `_map_location_to_codes` and
`_check_service_area_status` run for real. Prints a summary of metrics.

Run offline with: pytest backend/tests/test_service_area_eval.py -v -s
"""

import json

import pytest

from app.pipeline.service_area import extract_service_area


def _mo(location_name=None, detail=None):
    """Municipality-granularity gold LLM return."""
    return {
        "location_name": location_name,
        "granularity": "municipality",
        "service_area_detail": detail,
    }


def _co(location_name=None):
    """County-granularity gold LLM return."""
    return {
        "location_name": location_name,
        "granularity": "county",
        "service_area_detail": None,
    }


# (case_name, foundation_name, purpose, gold_llm_return, expected, extra)
EVAL_CASES = [
    # ── CLEAR KOMMUN (8) ──────────────────────────────────────────────────────
    ("kommun_kalmar", "Stiftelsen för personer bosatta i Kalmar", "Att stödja personer bosatta i Kalmar kommun",
     _mo("Kalmar"), {"municipality_code": "0880", "county_code": "08", "municipality_name": "Kalmar", "confidence": "high"}, {}),
    ("kommun_stockholm", "Stiftelsen Stockholm", "För personer i Stockholms kommun",
     _mo("Stockholm"), {"municipality_code": "0180", "county_code": "01", "municipality_name": "Stockholm", "confidence": "high"}, {}),
    ("kommun_goteborg", "Göteborgsstiftelsen", "Boende i Göteborgs kommun",
     _mo("Göteborg"), {"municipality_code": "1480", "county_code": "14", "municipality_name": "Göteborg", "confidence": "high"}, {}),
    ("kommun_lund", "Stiftelsen för Lund", "Stöd till studerande i Lund",
     _mo("Lund"), {"municipality_code": "1281", "county_code": "12", "municipality_name": "Lund", "confidence": "high"}, {}),
    ("kommun_uppsala", "Uppsalastiftelsen", "För invånare i Uppsala kommun",
     _mo("Uppsala"), {"municipality_code": "0380", "county_code": "03", "municipality_name": "Uppsala", "confidence": "high"}, {}),
    ("kommun_malmo", "Malmöstödet", "Personer bosatta i Malmö",
     _mo("Malmö"), {"municipality_code": "1280", "county_code": "12", "municipality_name": "Malmö", "confidence": "high"}, {}),
    ("kommun_orebro", "Örebrostiftelsen", "Stöd till ungdomar i Örebro kommun",
     _mo("Örebro"), {"municipality_code": "1880", "county_code": "18", "municipality_name": "Örebro", "confidence": "high"}, {}),
    ("kommun_vasteras", "Stiftelsen Västerås", "För boende i Västerås",
     _mo("Västerås"), {"municipality_code": "1980", "county_code": "19", "municipality_name": "Västerås", "confidence": "high"}, {}),

    # ── CLEAR LÄN (4) ─────────────────────────────────────────────────────────
    ("lan_uppsala", "Stiftelsen för Uppsala län", "Boende i Uppsala län",
     _co("Uppsala"), {"county_code": "03", "county_name": "Uppsala län", "municipality_code": None, "confidence": "medium"}, {}),
    ("lan_skane", "Skånestiftelsen", "Födda i Skåne",
     _co("Skåne"), {"county_code": "12", "county_name": "Skåne län", "municipality_code": None, "confidence": "medium"}, {}),
    ("lan_vast_gotaland", "Stiftelsen Västra Götaland", "Invånare i Västra Götalands län",
     _co("Västra Götalands"), {"county_code": "14", "county_name": "Västra Götalands län", "municipality_code": None, "confidence": "medium"}, {}),
    ("lan_norrbotten", "Norrbottens stiftelse", "För personer i Norrbotten",
     _co("Norrbotten"), {"county_code": "25", "county_name": "Norrbottens län", "municipality_code": None, "confidence": "medium"}, {}),

    # ── SUB-KOMMUN/PARISH (6) ─────────────────────────────────────────────────
    ("subkommun_parish_stockholm", "Stockholms domkyrkoförsamling", "Stöd till medlemmar i Stockholms domkyrkoförsamling",
     _mo("Stockholm", "Stockholms domkyrkoförsamling"), {"municipality_code": "0180", "county_code": "01"}, {"detail_substring": "domkyrkoförsamling"}),
    ("subkommun_parish_goteborg", "Gustavi församling", "Medlemmar i Gustavi församling i Göteborg",
     _mo("Göteborg", "Gustavi församling"), {"municipality_code": "1480", "county_code": "14"}, {"detail_substring": "Gustavi"}),
    ("subkommun_parish_lund", "Domkyrkokörsföreningen i Lund", "Stöd till körmedlemmar i Lunds domkyrkoförsamling",
     _mo("Lund", "Lunds domkyrkoförsamling"), {"municipality_code": "1281", "county_code": "12"}, {"detail_substring": "domkyrkoförsamling"}),
    ("subkommun_parish_linkoping", "Linköpings domkyrkoförsamling", "För medlemmar i Linköpings domkyrkoförsamling",
     _mo("Linköping", "Linköpings domkyrkoförsamling"), {"municipality_code": "0580", "county_code": "05"}, {"detail_substring": "domkyrkoförsamling"}),
    ("subkommun_parish_uppsala", "Sankt Olofs församling", "Medlemmar i Sankt Olofs församling i Uppsala",
     _mo("Uppsala", "Sankt Olofs församling"), {"municipality_code": "0380", "county_code": "03"}, {"detail_substring": "Sankt Olofs"}),
    ("subkommun_parish_malmo", "Sankt Petri församling", "För medlemmar i Sankt Petri församling i Malmö",
     _mo("Malmö", "Sankt Petri församling"), {"municipality_code": "1280", "county_code": "12"}, {"detail_substring": "Sankt Petri"}),

    # ── SUB-KOMMUN/STREET (4) ─────────────────────────────────────────────────
    ("subkommun_street_norr_malarstrand", "Norr Mälarstrand i Stockholm", "Endast boende på Norr Mälarstrand i Stockholm",
     _mo("Stockholm", "Norr Mälarstrand"), {"municipality_code": "0180", "county_code": "01"}, {"detail_substring": "Norr Mälarstrand"}),
    ("subkommun_street_kungsportsavenyn", "Stiftelsen Kungsportsavenyn", "Boende vid Kungsportsavenyn i Göteborg",
     _mo("Göteborg", "Kungsportsavenyn"), {"municipality_code": "1480", "county_code": "14"}, {"detail_substring": "Kungsportsavenyn"}),
    ("subkommun_stadsdel_sodermalm", "Södermalms stiftelse", "För boende i Södermalm, Stockholm",
     _mo("Stockholm", "Södermalm"), {"municipality_code": "0180", "county_code": "01"}, {"detail_substring": "Södermalm"}),
    ("subkommun_stadsdel_haga", "Stiftelsen Haga", "För boende i stadsdelen Haga i Göteborg",
     _mo("Göteborg", "Haga"), {"municipality_code": "1480", "county_code": "14"}, {"detail_substring": "Haga"}),

    # ── NATIONWIDE (6) ────────────────────────────────────────────────────────
    ("nationwide_generic", "Allmän stiftelse", "Att hjälpa folk i behov",
     _mo(None), None, {}),
    ("nationwide_sverige", "Stiftelsen för Sverige", "Stödja forskning i hela Sverige",
     _mo(None), None, {}),
    ("nationwide_utan_geo", "Utbildningsstiftelsen", "Främja utbildning utan geografisk begränsning",
     _mo(None), None, {}),
    ("nationwide_kultur", "Kulturstiftelsen", "Stödja kulturverksamhet i Sverige",
     _mo(None), None, {}),
    ("nationwide_forskning", "Vetenskapsstiftelsen", "Främja forskning och vetenskap",
     _mo(None), None, {}),
    ("nationwide_fattiga", "Stiftelsen för fattiga", "Hjälpa fattiga i Sverige",
     _mo(None), None, {}),

    # ── CONTRADICTION (4) ─────────────────────────────────────────────────────
    ("contradiction_stockholm_registered_gotland", "Stiftelsen Gotland", "För personer bosatta på Gotland",
     _mo("Gotland"), {"municipality_code": "0980", "county_code": "09"}, {"registered_county_code": "01", "expect_status": "REVIEW"}),
    ("contradiction_uppsala_registered_skane", "Stiftelsen för Skåneboende", "Personer i Skåne",
     _co("Skåne"), {"county_code": "12"}, {"registered_county_code": "03", "expect_status": "REVIEW"}),
    ("contradiction_goteborg_registered_kalmar", "Kalmar-Göteborg stiftelsen", "Stöd till boende i Göteborg",
     _mo("Göteborg"), {"municipality_code": "1480", "county_code": "14"}, {"registered_county_code": "08", "expect_status": "REVIEW"}),
    ("contradiction_malmo_registered_norrbotten", "Norrbotten-Malmö stiftelsen", "För boende i Malmö",
     _mo("Malmö"), {"municipality_code": "1280", "county_code": "12"}, {"registered_county_code": "25", "expect_status": "REVIEW"}),

    # ── MULTI-PLACE (3) ───────────────────────────────────────────────────────
    ("multiplace_kalmar_vastervik", "Stiftelsen Kalmar och Västervik", "För personer i Kalmar och Västervik",
     _mo("Kalmar"), {"municipality_code": "0880", "county_code": "08"}, {"assert_non_null": True}),
    ("multiplace_stockholm_goteborg", "Stockholm-Göteborg stiftelsen", "Stödja ungdomar i Stockholm och Göteborg",
     _mo("Stockholm"), {"municipality_code": "0180", "county_code": "01"}, {"assert_non_null": True}),
    ("multiplace_lund_trelleborg", "Lund och Trelleborg stiftelsen", "För boende i Lund och Trelleborg",
     _mo("Lund"), {"municipality_code": "1281", "county_code": "12"}, {"assert_non_null": True}),

    # ── EDGE (5) ──────────────────────────────────────────────────────────────
    ("edge_empty_name", "", "Stöd till personer i Kalmar",
     _mo("Kalmar"), {"municipality_code": "0880", "county_code": "08"}, {"expect_not_none": True}),
    ("edge_very_long_text", "Stiftelsen Kalmar", "x" * 2500,
     _mo("Kalmar"), {"municipality_code": "0880", "county_code": "08"}, {"expect_not_none": True}),
    ("edge_llm_empty_response", "Stiftelsen Kalmar", "För Kalmar",
     None, None, {}),
    ("edge_llm_error_response", "Stiftelsen Kalmar", "För Kalmar",
     "ERROR: service unavailable", None, {}),
    ("edge_llm_invalid_json", "Stiftelsen Kalmar", "För Kalmar",
     "not json at all", None, {}),
]


def _mock_return(gold):
    if gold is None:
        return None
    if isinstance(gold, str):
        return gold
    return json.dumps(gold)


def _safe_ratio(num, den):
    return round(num / den, 3) if den else 0.0


@pytest.mark.asyncio
async def test_service_area_eval_harness(monkeypatch):
    """Run all 40 eval cases and print a summary of metrics."""
    from app.pipeline import service_area as sa_module

    failures = []

    geo_non_null = 0
    geo_cases = 0
    nationwide_cases = 0
    false_places = 0
    code_accuracy_hits = 0
    resolvable_cases = 0
    subkommun_cases = 0
    detail_hits = 0
    multi_cases = 0
    multi_non_null = 0

    for case_name, fname, purpose, gold, expected, extra in EVAL_CASES:
        mock_return = _mock_return(gold)

        # chat_completion is synchronous (called without await) — use a sync mock.
        # Default-arg binding avoids B023 (loop variable captured by closure).
        def fake_chat(*args, _mock_return=mock_return, **kwargs):
            return _mock_return

        monkeypatch.setattr(sa_module, "chat_completion", fake_chat)

        try:
            result = await extract_service_area(
                fname,
                purpose=purpose,
                registered_county_code=extra.get("registered_county_code"),
                registered_municipality_code=extra.get("registered_municipality_code"),
            )
        except Exception as e:  # noqa: BLE001
            failures.append(f"{case_name}: raised {e!r}")
            continue

        is_multi = bool(extra.get("assert_non_null"))
        is_not_none_edge = bool(extra.get("expect_not_none"))

        if expected is None:
            # Nationwide / no-place edge: expect None
            nationwide_cases += 1
            if result is not None:
                false_places += 1
                failures.append(f"{case_name}: expected None but got {result!r}")
            continue

        # ── Geo-bearing case ──
        geo_cases += 1
        if result is not None:
            geo_non_null += 1
            if is_multi:
                multi_non_null += 1

            # Code / status / name checks (except multi-place where we only
            # assert non-null and do not pin a single code).
            if not is_multi:
                for key, val in expected.items():
                    if key in ("municipality_code", "county_code", "municipality_name", "county_name", "confidence"):
                        if result.get(key) != val:
                            failures.append(
                                f"{case_name}: expected {key}={val!r} got {result.get(key)!r}"
                            )
                        else:
                            code_accuracy_hits += 1
                            resolvable_cases += 1

                if "expect_status" in extra:
                    if result.get("service_area_status") != extra["expect_status"]:
                        failures.append(
                            f"{case_name}: expected status {extra['expect_status']} "
                            f"got {result.get('service_area_status')}"
                        )
            else:
                multi_cases += 1
                # Multi-place: verify any requested code fields if supplied
                for key, val in expected.items():
                    if key in ("municipality_code", "county_code") and result.get(key) == val:
                        code_accuracy_hits += 1
                        resolvable_cases += 1

            if "detail_substring" in extra:
                subkommun_cases += 1
                detail = result.get("service_area_detail")
                if detail and extra["detail_substring"].lower() in str(detail).lower():
                    detail_hits += 1
                else:
                    failures.append(
                        f"{case_name}: detail {detail!r} missing {extra['detail_substring']!r}"
                    )
        else:
            # Result is None on a geo-bearing case
            if is_multi or is_not_none_edge:
                failures.append(f"{case_name}: expected non-null result but got None")
            # else: not tracked as failure; it just misses place_recall
        # end geo-bearing handling
    # end for

    place_recall = _safe_ratio(geo_non_null, geo_cases)
    code_accuracy = _safe_ratio(code_accuracy_hits, resolvable_cases)
    detail_fidelity = _safe_ratio(detail_hits, subkommun_cases)
    no_false_place = f"{false_places}/{nationwide_cases}"
    multi_place_non_null = _safe_ratio(multi_non_null, multi_cases)

    summary = {
        "place_recall": place_recall,
        "code_accuracy": code_accuracy,
        "detail_fidelity": detail_fidelity,
        "no_false_place": no_false_place,
        "multi_place_non_null": multi_place_non_null,
    }

    print("\n=== SERVICE AREA EVAL SUMMARY ===")
    print(json.dumps(summary))
    print(f"no_false_place == 0: {'PASS' if false_places == 0 else 'FAIL'}")
    print(f"cases run: {len(EVAL_CASES)}, geo-bearing: {geo_cases}, failures: {len(failures)}")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
    print("=================================")

    assert false_places == 0, f"no_false_place must be 0, got {false_places}"
    assert not failures, "Eval failures:\n" + "\n".join(failures)
