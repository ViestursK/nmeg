#!/usr/bin/env python3
"""
Trustpilot Executive Dashboard Header
UX-optimized, warning-free, production-safe
"""

from sheets_base import SheetsBase
import json


class TrustpilotDashboard(SheetsBase):

    # ==================================================
    # SETUP
    # ==================================================
    def setup_dashboard(self, ws):
        sheet_id = ws.id

        row_heights = {
            0: 72,
            1: 36,
            2: 36,
            3: 12,
            4: 28,
            5: 96,
            6: 12,
        }

        column_widths = {
            0: 130,
            1: 260,
            2: 130,
            3: 130,
            4: 130,
            5: 130,
            6: 130,
            7: 130,
        }

        self._set_dimensions(sheet_id, row_heights, column_widths)

        ws.merge_cells("A1:A3")
        ws.merge_cells("B1:B3")
        ws.merge_cells("A5:H5")
        ws.merge_cells("A6:H6")

        self._apply_base_format(ws)

    # ==================================================
    # DATA POPULATION
    # ==================================================
    def update_dashboard(self, ws, data):
        c = data["company"]
        w = data["week_stats"]
        rm = data["report_metadata"]

        # ------------------
        # LOGO (FIXED)
        # ------------------
        logo_url = c.get("logo_url", "")
        if logo_url.startswith("//"):
            logo_url = "https:" + logo_url

        ws.update(
            values=[[f'=IFERROR(IMAGE("{logo_url}",1),"")']],
            range_name="A1"
        )

        # ------------------
        # BRAND BLOCK
        # ------------------
        ws.update([[c["brand_name"]]], "B1")
        ws.update([[c["website"]]], "B2")
        ws.update([[" • ".join(c.get("categories", [])[:3])]], "B3")

        # ------------------
        # KPI VALUES (NUMERIC)
        # ------------------
        ws.update([[c["trust_score"]]], "C1")
        ws.update([[c["total_reviews_all_time"]]], "D1")
        ws.update([[w["review_volume"]["wow_change"]]], "E1")
        ws.update([[w["rating_performance"]["avg_rating_this_week"]]], "F1")
        ws.update([[w["sentiment"]["negative"]["percentage"]]], "G1")
        ws.update([[w["response_performance"]["response_rate_pct"]]], "H1")

        # ------------------
        # KPI LABELS
        # ------------------
        ws.update([["Trust score"]], "C2")
        ws.update([["Total reviews"]], "D2")
        ws.update([["WoW review change"]], "E2")
        ws.update([["Avg rating (week)"]], "F2")
        ws.update([["Negative reviews %"]], "G2")
        ws.update([["Response rate %"]], "H2")

        # ------------------
        # STARS SVG (FIXED)
        # ------------------
        stars_svg = c.get("star_rating_svg")
        if stars_svg:
            ws.update(
                values=[[f'=IFERROR(IMAGE("{stars_svg}",4,18,90),"")']],
                range_name="C3"
            )

        # ------------------
        # AI SUMMARY
        # ------------------
        ws.update([[" AI SUMMARY"]], "A5")

        summary = c.get("ai_summary", {}).get("summary_text", "")
        if len(summary) > 900:
            summary = summary[:897] + "..."

        ws.update([[summary]], "A6")

        # ------------------
        # LAST UPDATED
        # ------------------
        generated_at = rm.get("generated_at")
        if generated_at:
            ws.update([[f"Updated {generated_at[:10]}"]], "H3")

        self._apply_dynamic_format(ws, c["trust_score"])

    # ==================================================
    # FORMATTING
    # ==================================================
    def _set_dimensions(self, sheet_id, rows, cols):
        requests = []

        for r, h in rows.items():
            requests.append({
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": r,
                        "endIndex": r + 1,
                    },
                    "properties": {"pixelSize": h},
                    "fields": "pixelSize",
                }
            })

        for c, w in cols.items():
            requests.append({
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": c,
                        "endIndex": c + 1,
                    },
                    "properties": {"pixelSize": w},
                    "fields": "pixelSize",
                }
            })

        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=self.gc.open_by_key(self.find_master_sheet()).id,
            body={"requests": requests},
        ).execute()

    def _apply_base_format(self, ws):
        ws.format("A1:H6", {
            "backgroundColor": {"red": 1, "green": 1, "blue": 1},
            "textFormat": {"fontFamily": "Inter"},
        })

        ws.format("B1", {"textFormat": {"fontSize": 20, "bold": True}})
        ws.format("B2:B3", {"textFormat": {"fontSize": 9, "foregroundColor": {"red": .45, "green": .45, "blue": .45}}})

        ws.format("C1:H1", {"textFormat": {"fontSize": 16, "bold": True}, "horizontalAlignment": "CENTER"})
        ws.format("C2:H2", {"textFormat": {"fontSize": 9, "foregroundColor": {"red": .5, "green": .5, "blue": .5}}, "horizontalAlignment": "CENTER"})

        ws.format("A5:H5", {
            "backgroundColor": {"red": .26, "green": .52, "blue": .96},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
        })

        ws.format("A6:H6", {
            "backgroundColor": {"red": 1, "green": .99, "blue": .96},
            "wrapStrategy": "WRAP",
            "verticalAlignment": "TOP",
        })

    def _apply_dynamic_format(self, ws, trust_score):
        if trust_score >= 4:
            color = {"red": .85, "green": .95, "blue": .85}
        elif trust_score >= 3:
            color = {"red": 1, "green": .95, "blue": .8}
        else:
            color = {"red": 1, "green": .9, "blue": .9}

        ws.format("C1", {"backgroundColor": color})


# ======================================================
# ENTRYPOINT
# ======================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python sheets_metadata.py <tab_name> <report.json>")
        sys.exit(1)

    with open(sys.argv[2], "r") as f:
        data = json.load(f)

    uploader = TrustpilotDashboard()
    workbook, spreadsheet_id = uploader.get_workbook()
    ws = uploader.get_or_create_tab(workbook, sys.argv[1])

    uploader.setup_dashboard(ws)
    uploader.update_dashboard(ws, data)

    print("✅ Dashboard ready")
    print(f"🔗 https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
