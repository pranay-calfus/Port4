from backend.services.theme_normalization import group_themes, normalize_theme


def test_normalize_lowercases_trims_and_collapses_whitespace():
    assert normalize_theme("  Login   Issues  ") == "login issue"


def test_normalize_strips_punctuation():
    assert normalize_theme("Billing Error!") == "billing error"
    assert normalize_theme("Can't Log In") == "cant log in"


def test_normalize_singularizes_plurals():
    assert normalize_theme("Billing Errors") == "billing error"
    assert normalize_theme("Delivery Delays") == "delivery delay"
    assert normalize_theme("Feature Requests") == "feature request"
    assert normalize_theme("App Crashes") == "app crash"
    assert normalize_theme("Categories") == "category"


def test_normalize_does_not_mangle_short_or_already_singular_words():
    assert normalize_theme("UI") == "ui"
    assert normalize_theme("Account Access") == "account access"


def test_group_themes_merges_case_and_plural_variants():
    items = [
        {"theme": "UI Improvement"},
        {"theme": "ui improvements"},
        {"theme": "UI Improvement"},
    ]
    labels = group_themes(items)
    assert len(set(labels.values())) == 1
    merged_label = next(iter(labels.values()))
    # No synonym entry for "UI Improvement(s)" - the most frequent original
    # raw variant wins as the display label.
    assert merged_label == "UI Improvement"


def test_group_themes_applies_synonym_mapping():
    items = [
        {"theme": "Billing Error"},
        {"theme": "Billing Errors"},
        {"theme": "Payment Issue"},
        {"theme": "payment error"},
    ]
    labels = group_themes(items)
    assert set(labels.values()) == {"Billing Issues"}


def test_group_themes_keeps_distinct_themes_separate():
    items = [{"theme": "Billing Error"}, {"theme": "Login Issues"}]
    labels = group_themes(items)
    assert labels["Billing Error"] == "Billing Issues"
    assert labels["Login Issues"] == "Login Issues"


def test_group_themes_most_frequent_variant_wins_display_label():
    items = [
        {"theme": "UI Improvements"},
        {"theme": "UI Improvements"},
        {"theme": "ui improvements!!"},
    ]
    labels = group_themes(items)
    assert labels["UI Improvements"] == "UI Improvements"
    assert labels["ui improvements!!"] == "UI Improvements"


def test_group_themes_ignores_none():
    items = [{"theme": "Login Issues"}, {"theme": None}]
    labels = group_themes(items)
    assert labels == {"Login Issues": "Login Issues"}


def test_group_themes_breaks_ties_by_first_seen_variant():
    # Both variants occur once (a tie), and neither has a synonym entry -
    # the first one encountered wins, rather than this being
    # nondeterministic across runs.
    items = [{"label": "Login Issues"}, {"label": "login issue"}]
    labels = group_themes(items, theme_key=lambda i: i["label"])
    assert labels == {"Login Issues": "Login Issues", "login issue": "Login Issues"}
