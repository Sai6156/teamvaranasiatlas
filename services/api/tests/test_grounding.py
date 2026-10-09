from atlas.grounding import citation_support, abstention


def test_production_claim_cannot_cite_onboarding_heading():
    answer = "**Production access requirements:**\n\nMultifactor authentication and team lead approval are required [2]."
    sources = [
        {"number": 2, "content": "Fictional Example: Onboarding"},
        {
            "number": 5,
            "content": "# Engineering setup\n# Install dependencies and run tests.\n# Production access requires multifactor authentication and team lead approval.\n# Never commit secrets to the repository.",
        },
    ]
    repaired, valid = citation_support(answer, sources)
    assert valid
    assert "[5]" in repaired
    assert "[2]" not in repaired


def test_heading_only_support_abstains_instead_of_accepting_bad_citation():
    repaired, valid = citation_support(
        "Production access needs multifactor authentication and team lead approval [2].",
        [{"number": 2, "content": "Fictional Example: Onboarding"}],
    )
    assert not valid


def test_grounded_short_factual_source_is_preserved():
    answer = "Employees get 18 annual leave days per calendar year [1]."
    repaired, valid = citation_support(
        answer,
        [
            {
                "number": 1,
                "content": "Employees receive 18 days of annual leave each calendar year.",
            }
        ],
    )
    assert valid and repaired == answer


def test_abstention_does_not_attach_irrelevant_document_inventory():
    answer = "I couldn't find the company's growth rate in this workspace. The documents cover expense limits [1] and leave [2]."
    assert (
        abstention(answer)
        == "I couldn't find the company's growth rate in this workspace."
    )
