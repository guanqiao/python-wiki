"""
PyQt6 应用程序入口
"""

import sys
from typing import Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from pywiki.config.settings import Settings
from pywiki.gui.main_window import MainWindow


class Application:
    """Python Wiki GUI 应用程序"""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self._qt_app: Optional[QApplication] = None
        self._main_window: Optional[MainWindow] = None

    def run(self) -> int:
        """运行应用程序"""
        self._qt_app = QApplication(sys.argv)
        self._qt_app.setApplicationName("Python Wiki")
        self._qt_app.setApplicationVersion("0.1.0")
        self._qt_app.setStyle("Fusion")

        self._main_window = MainWindow(self.settings)
        self._main_window.show()

        return self._qt_app.exec()

    def quit(self) -> None:
        """退出应用程序"""
        if self._qt_app:
            self._qt_app.quit()


def main() -> int:
    """主入口函数"""
    app = Application()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
