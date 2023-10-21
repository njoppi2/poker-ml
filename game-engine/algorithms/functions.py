
import os
import logging

def color_print(value):
    r, g, b = (255, 255, 255)
    if 0 <= value <= 1:
        color_map = [
            (255, 0, 0),     # 0
            (255, 50, 0),    # 0.1
            (255, 100, 0),   # 0.2
            (255, 150, 0),   # 0.3
            (255, 200, 0),   # 0.4
            (100, 255, 0),   # 0.5
            (0, 255, 0),   # 0.6
            (0, 255, 50),   # 0.7
            (0, 255, 150),   # 0.8
            (0, 255, 255),    # 0.9
            (0, 205, 255)      # 1
        ]

        interval = int((value) * (len(color_map) - 1))
        r, g, b = color_map[interval]

    # ANSI escape sequence for color formatting
    return f"\033[38;2;{r};{g};{b}m{value:.10f}\033[0m "