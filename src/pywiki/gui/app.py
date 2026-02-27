"""
PyQt6 应用程序入口
"""

import sys
import traceback
from typing import Optional

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from pywiki.config.settings import Settings
from pywiki.gui.main_window import MainWindow
from pywiki.monitor.logger import logger


class Application:
    """Python Wiki GUI 应用程序"""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self._qt_app: Optional[QApplication] = None
        self._main_window: Optional[MainWindow] = None

    def run(self) -> int:
        """运行应用程序"""
        logger.info("=" * 50)
        logger.info("Python Wiki 应用启动")
        logger.info(f"日志文件: {logger.log_file}")
        logger.info("=" * 50)

        self._qt_app = QApplication(sys.argv)
        self._qt_app.setApplicationName("Python Wiki")
        self._qt_app.setApplicationVersion("0.1.0")
        self._qt_app.setStyle("Fusion")

        self._setup_exception_handler()

        try:
            self._main_window = MainWindow(self.settings)
            self._main_window.show()
            logger.info("主窗口初始化完成，应用开始运行")
            return self._qt_app.exec()
        except Exception as e:
            logger.log_exception("应用启动失败", e)
            QMessageBox.critical(
                None,
                "启动错误",
                f"应用程序启动失败:\n{str(e)}\n\n详细信息请查看日志文件:\n{logger.log_file}"
            )
            return 1

    def _setup_exception_handler(self) -> None:
        """设置全局异常处理器"""
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return

            logger.log_exception(
                "未捕获的异常",
                exc_value if exc_value else exc_type()
            )

            error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.error(f"完整堆栈:\n{error_msg}")

            if self._qt_app:
                QMessageBox.critical(
                    None,
                    "程序错误",
                    f"发生未预期的错误:\n{str(exc_value)}\n\n详细信息请查看日志文件:\n{logger.log_file}"
                )

        sys.excepthook = handle_exception

    def quit(self) -> None:
        """退出应用程序"""
        logger.info("Python Wiki 应用退出")
        if self._qt_app:
            self._qt_app.quit()


def main() -> int:
    """主入口函数"""
    try:
        app = Application()
        return app.run()
    except Exception as e:
        logger.log_exception("主函数执行失败", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
