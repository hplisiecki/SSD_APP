"""PyInstaller runtime hook — set EDITION to 'full' for the Asian-language build."""
import ssdiff_gui
ssdiff_gui.EDITION = "full"
