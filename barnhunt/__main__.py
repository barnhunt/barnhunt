from .cli import main

if __name__ == "__main__":
    # NB: Specify explicit prog_name to work around the fact that pyoxidize build
    # seem to end up with sys.argv[0] = None which screws up click's program name
    # auto-detectiong.
    main(prog_name=__package__)
