import warnings


class DataTypeMismatchWarning(Warning):
    pass


class ElementNotFoundWarning(Warning):
    pass


# --- Set the warning filter to always show the warning ---
warnings.simplefilter("always", DataTypeMismatchWarning)
warnings.simplefilter("always", ElementNotFoundWarning)
