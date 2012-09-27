try:
    from japong.run import main
except ImportError:
    import os
    import sys


    sys.path.insert(0, os.path.realpath('.'))

    from japong.run import main


main()
