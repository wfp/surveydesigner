class MockRequest:
    """
    Useful to test admin functionalities
    """

    def __init__(self, user=None, headers={}):
        self.user = user
        self.headers = headers
