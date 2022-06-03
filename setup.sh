#!/bin/sh
#
SCRIPTDIR=$(cd $(dirname $0) && pwd)
YUM_PKGS=""
APT_PKGS="python3-venv"
MAC_PKGS="terraform packer"
MAJOR_REV=3
MINOR_REV=9
VENV_NAME=venv
PYTHON_BIN=python3.9

check_yum () {
  for package in $YUM_PKGS
  do
    yum list installed $package >/dev/null 2>&1
    if [ $? -ne 0 ]; then
      echo "Please install $package"
      exit 1
    fi
  done
}

check_apt () {
  for package in $APT_PKGS
  do
    dpkg -l $package >/dev/null 2>&1
    if [ $? -ne 0 ]; then
      echo "Please install $package"
      exit 1
    fi
  done
}

check_macos () {
  which brew >/dev/null 2>&1
  if [ $? -ne 0 ]; then
    echo "Please install brew, then install openssl."
    exit 1
  fi
  for package in $MAC_PKGS
  do
    brew list $package >/dev/null 2>&1
    if [ $? -ne 0 ]; then
      echo "Please install brew package $package"
      exit 1
    fi
  done
}

check_linux_by_type () {
  . /etc/os-release
  export LINUXTYPE=$ID
  case $ID in
  centos|rhel)
    check_yum
    ;;
  ubuntu)
    check_apt
    ;;
  *)
    echo "Unknown Linux distribution $ID"
    exit 1
    ;;
  esac
}

SYSTEM_UNAME=$(uname -s)
case "$SYSTEM_UNAME" in
    Linux*)
      machine=Linux
      check_linux_by_type
      ;;
    Darwin*)
      machine=MacOS
      check_macos
      ;;
    CYGWIN*)
      machine=Cygwin
      echo "Windows is not currently supported."
      exit 1
      ;;
    *)
      echo "Unsupported system type: $SYSTEM_UNAME"
      exit 1
      ;;
esac

which $PYTHON_BIN >/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Python 3 is required and $PYTHON_BIN should be in the execution search PATH."
  exit 1
fi

if [ ! -f requirements.txt ]; then
  echo "Missing requirements.txt"
  exit 1
fi

PY_MAJOR=$(python3 --version | awk '{print $NF}' | cut -d. -f1)
PY_MINOR=$(python3 --version | awk '{print $NF}' | cut -d. -f2)

if [ "$PY_MAJOR" -lt "$MAJOR_REV" ] || [ "$PY_MINOR" -lt "$MINOR_REV" ]; then
  echo "Python ${MAJOR_REV}.${MINOR_REV} or higher is required."
  exit 1
fi

if [ -d $SCRIPTDIR/$VENV_NAME ]; then
  echo "Virtual environment $SCRIPTDIR/$VENV_NAME already exists."
  exit 1
fi

printf "Creating virtual environment... "
$PYTHON_BIN -m venv $SCRIPTDIR/$VENV_NAME
if [ $? -ne 0 ]; then
  echo "Virtual environment setup failed."
  exit 1
fi
echo "Done."

printf "Activating virtual environment... "
. ${SCRIPTDIR:?}/${VENV_NAME:?}/bin/activate
echo "Done."

printf "Installing dependencies... "
$PYTHON_BIN -m pip install --upgrade pip > setup.log 2>&1
pip3 install -r requirements.txt > setup.log 2>&1
if [ $? -ne 0 ]; then
  echo "Setup failed."
  rm -rf ${SCRIPTDIR:?}/${VENV_NAME:?}
  exit 1
else
  echo "Done."
  echo "Setup successful."
fi

##