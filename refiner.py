import sys

def main(argv=None):
    from refiner_core.cli import main as core_main
    return core_main(argv)


if __name__ == '__main__':
    sys.exit(main())
