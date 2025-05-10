#! /bin/bash

set -e
source "$1/bin/activate"
shift
"$@"
