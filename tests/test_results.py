import pandas as pd
from views.results import needs_legend


def test_needs_legend():
    df_false = pd.DataFrame([[False, False], [False, False]])
    assert needs_legend(df_false) is False

    df_true = pd.DataFrame([[False, False], [False, True]])
    assert needs_legend(df_true) is True
