import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.app import App

def main():
    App().run()

if __name__ == "__main__":
    main()
