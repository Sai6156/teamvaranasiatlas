from atlas.grounding import disclosed_column_totals


def test_category_sums_use_verified_cells_instead_of_geographic_row_totals():
    answer = "| Location | Machines | Offices | Total |\n|---|---|---|---|\n| National | 8 | 20 | 28 |\n| International | 1 | 3 | 4 |"
    sources = [
        {
            "number": 4,
            "content": "Location Machines Offices Total\nNational 8 20 28\nInternational 1 3 4",
        }
    ]
    corrected = disclosed_column_totals(answer, "Give their separate totals", sources)
    assert "Machines: 8 + 1 = 9" in corrected
    assert "Offices: 20 + 3 = 23" in corrected
    assert "[4]" in corrected
    assert (
        disclosed_column_totals(
            answer,
            "Give totals",
            [{"number": 4, "content": "Unrelated values 8 and 20"}],
        )
        == answer
    )


def test_years_and_percentage_columns_are_never_aggregated():
    answer = "| Location | FY 2024 | FY 2023 |\n|---|---|---|\n| National | 8 | 20 |\n| International | 1 | 3 |"
    assert disclosed_column_totals(answer, "Give totals", []) == answer
