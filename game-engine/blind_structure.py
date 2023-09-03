class BlindStructure:
    def __init__(self):
        self.blinds = [(10, 20), (15, 30), (25, 50), (50, 100), (75, 150),
                       (100, 200), (150, 300), (200, 400), (300, 600), (400, 800)]
        self.current_level = 0

    def increase_blind(self):
        if self.current_level < len(self.blinds) - 1:
            self.current_level += 1

    def get_blinds(self):
        return self.blinds[self.current_level]
