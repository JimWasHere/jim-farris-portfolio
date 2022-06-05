class Seconds:
    """Converts given amount of seconds into minutes and seconds"""
    def __init__(self, seconds):
        self.seconds = seconds

    def convert_seconds(self):
        self.seconds = self.seconds % (24 * 3600)
        self.seconds %= 3600
        minutes = self.seconds // 60
        self.seconds %= 60
        return "%02d:%02d" % (minutes, self.seconds)


x = Seconds(90).convert_seconds()
print(x)
