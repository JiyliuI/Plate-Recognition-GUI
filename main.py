import tkinter as tk
from gui_app import LicensePlateRecognitionSystem

def main():
    """程序主入口点"""
    root = tk.Tk()
    app = LicensePlateRecognitionSystem(root)
    root.mainloop()

if __name__ == "__main__":
    main()