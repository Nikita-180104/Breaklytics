import sys

from break_service import run_cli, run_server


def main():
    if "--serve" in sys.argv:
        run_server()
        return

    run_cli()


if __name__ == "__main__":
    main()
