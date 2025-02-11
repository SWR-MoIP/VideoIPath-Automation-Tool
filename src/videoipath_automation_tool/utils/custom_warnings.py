import warnings


class DataTypeMismatchWarning(Warning):
    pass


warnings.simplefilter("always", DataTypeMismatchWarning)
