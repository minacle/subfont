# subfont

generate subsetted woff/woff2 font.

## requirements

- python 3.6 or newer with pip

## preparation

1. `git clone https://github.com/minacle/subfont.git`
2. `cd subfont`
3. `pip3.6 install -r requirements.txt`
4. `python3.6 subfont.py --help`

## usage

    usage: subfont.py [-F FILE...] [-T TAG...] [-I ID...] [-C CLASS...]
                      [-A ATTRIBUTE...] [-e EXTENSION...] [-i TEXT]
                      [-o DESTINATION] [-w] [-W] [-v] [-h]
                      -f FONT... -- FILE...

    required arguments:
       -f FONT...        --fonts FONT...
          set font(s) to make subsetted
       FILE...
          file(s) to get used characters

    ignoring arguments:
       -F FILE...        --ignore-files FILE...
          set file(s) to be ignored
       -T TAG...         --ignore-tags TAG...
          set tag(s) to be ignored
       -I ID...          --ignore-ids ID...
          set id(s) to be ignored
       -C CLASS...       --ignore-classes CLASS...
          set class(es) to be ignored
       -A ATTRIBUTE...   --ignore-attributes ATTRIBUTE...
          set attribute(s) to be ignored

    optional arguments:
       -e EXTENSION...   --extensions EXTENSION...
          set extension(s) of file(s) to get used characters
       -i TEXT           --include-characters TEXT
          include characters in text
       -o DESTINATION    --output-directory DESTINATION
          set output directory
       -w                --woff
          output as woff (optionally required 'zopfli' module)
       -W                --woff2
          output as woff2 (required 'brotli' module)
       -v                --verbose
          print a lot of logs to reassure you
       -h                --help
          print help message and exit

### example

    python3.6 subfont.py -f font.otf -- index.html
