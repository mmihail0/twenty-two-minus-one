from menu import run_menu
from pygamevl import run

if __name__ == "__main__":
    result = run_menu()
    if result == "play":
        run()