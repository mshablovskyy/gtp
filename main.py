"""
GTP Desktop — Google Takeout Processor with GUI.

Launch modes:
  - No arguments: opens the CustomTkinter desktop app
  - With -p/--path: runs the original CLI (backward compatible)
"""

import sys


def main():
    # If CLI arguments are provided, delegate to original gtp.py
    if len(sys.argv) > 1 and any(
        arg in sys.argv for arg in ("-p", "--path", "-h", "--help", "-d", "--destination", "-s", "--suffix")
    ):
        import gtp
        gtp.parse(gtp.description)
    else:
        # Register HEIC support before any image loading
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            pass

        from ui.app import GTPApp
        app = GTPApp()
        app.mainloop()


if __name__ == "__main__":
    main()
