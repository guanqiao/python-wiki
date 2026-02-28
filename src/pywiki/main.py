"""
Python Wiki 主入口
"""

import sys


def main() -> int:
    """GUI 主入口"""
    from pywiki.gui.app import Application
    app = Application()
    return app.run()


def cli_main() -> int:
    """CLI 主入口"""
    from pywiki.cli.main import main
    main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
