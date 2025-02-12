import warnings


class DataTypeMismatchWarning(Warning):
    pass


class ElementNotFoundWarning(Warning):
    pass


warnings.simplefilter("always", DataTypeMismatchWarning)
