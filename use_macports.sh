#!/bin/sh

## Wrap Macports command (any executables installed by Macports).
## Originally from http://www.topbug.net/blog/2013/10/23/use-both-homebrew-and-macports-on-your-os-x/

if [ "$#" -le 0 ]; then
  echo "Usage: $0 command [arg1, arg2, ...]" >&2
  exit 1
fi
 
if [[ -z $MACPORTS_PREFIX ]]; then
  MACPORTS_PREFIX='/opt/local'
fi
 
 
export PATH="$MACPORTS_PREFIX/bin:$MACPORTS_PREFIX/sbin:$PATH"
export CPATH="$MACPORTS_PREFIX/include:$CPATH"
export MANPATH="$MACPORTS_PREFIX/share/man:$MANPATH"
export CMAKE_PREFIX_PATH="$MACPORTS_PREFIX"
export PYTHONPATH="$MACPORTS_PREFIX/lib/python2.7/site-packages/:$PYTHONPATH"

command=$1

shift
 
exec $command $*