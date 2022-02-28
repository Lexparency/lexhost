import sys
import os


def get_application():
    sys.path.insert(0, os.path.dirname(__file__))
    from app import create_app
    return create_app()


application = get_application()
