#!/bin/bash
#
SCRIPTDIR=$(cd $(dirname $0) && pwd)
YUM_PKGS="python39 openssl-devel packer terraform"
APT_PKGS="python3.9 python3.9-venv packer terraform"
MAC_PKGS="python@3.9 openssl@1.1 terraform packer"
MAJOR_REV=3
MINOR_REV=9
VENV_NAME=venv
PYTHON_BIN=python3.9

err_exit () {
   if [ -n "$1" ]; then
      echo "[!] Error: $1"
   fi
   exit 1
}

install_pkg () {
  case $PKGMGR in
  yum)
    sudo yum install -q -y "$@"
    ;;
  apt)
    sudo apt-get update
    sudo apt-get install -q -y "$@"
    ;;
  brew)
    brew install "$@"
    ;;
  *)
    err_exit "Unknown package manager $PKGMGR"
    ;;
  esac
}

install_packer_yum () {
  sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
}

install_packer_apt () {
  curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
  sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
}

install_tf_yum () {
  sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
}

install_tf_apt () {
  curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
  sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
}

check_yum () {
  for package in $YUM_PKGS
  do
    yum list installed $package >/dev/null 2>&1
    if [ $? -ne 0 ]; then
      echo -n "Install dependency ${package}? (y/n) [y]:"
      read INPUT
      if [ "$INPUT" == "y" -o -z "$INPUT" ]; then
        if [ "$package" = "packer" ]; then
          install_packer_yum
        fi
        if [ "$package" = "terraform" ]; then
          install_tf_yum
        fi
        install_pkg $package
      else
        echo "Please install $package"
        exit 1
      fi
    fi
  done
}

check_apt () {
  for package in $APT_PKGS
  do
    dpkg -s $package >/dev/null 2>&1
    if [ $? -ne 0 ]; then
      echo -n "Install dependency ${package}? (y/n) [y]:"
      read INPUT
      if [ "$INPUT" == "y" -o -z "$INPUT" ]; then
        if [ "$package" = "packer" ]; then
          install_packer_apt
        fi
        if [ "$package" = "terraform" ]; then
          install_tf_apt
        fi
        install_pkg $package
      else
        echo "Please install $package"
        exit 1
      fi
    fi
  done
}

check_macos () {
  PKGMGR="brew"
  which brew >/dev/null 2>&1
  if [ $? -ne 0 ]; then
    echo "Please install homebrew"
    exit 1
  fi
  for package in $MAC_PKGS
  do
    brew list $package >/dev/null 2>&1
    if [ $? -ne 0 ]; then
      echo -n "Install dependency ${package}? (y/n/s) [y]:"
      read INPUT
      if [ "$INPUT" == "s" ]; then
        continue
      fi
      if [ "$INPUT" == "y" -o -z "$INPUT" ]; then
        install_pkg $package
      else
        echo "Please install $package"
        exit 1
      fi
    fi
  done
}

check_linux_by_type () {
  . /etc/os-release
  export LINUXTYPE=$ID
  case $ID in
  centos|rhel)
    PKGMGR="yum"
    check_yum
    ;;
  ubuntu)
    PKGMGR="apt"
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

while getopts "p:" opt
do
  case $opt in
    p)
      PYTHON_BIN=$OPTARG
      ;;
    \?)
      echo "Invalid Argument"
      exit 1
      ;;
  esac
done

which $PYTHON_BIN >/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Python 3 is required and $PYTHON_BIN should be in the execution search PATH."
  exit 1
fi

if [ ! -f requirements.txt ]; then
  echo "Missing requirements.txt"
  exit 1
fi

PY_MAJOR=$($PYTHON_BIN --version | awk '{print $NF}' | cut -d. -f1)
PY_MINOR=$($PYTHON_BIN --version | awk '{print $NF}' | cut -d. -f2)

if [ "$PY_MAJOR" -lt "$MAJOR_REV" ] || [ "$PY_MINOR" -lt "$MINOR_REV" ]; then
  echo "Python ${MAJOR_REV}.${MINOR_REV} or higher is required."
  exit 1
fi

if [ -d $SCRIPTDIR/$VENV_NAME ]; then
  echo "Virtual environment $SCRIPTDIR/$VENV_NAME already exists."
  echo -n "Remove the existing directory? (y/n) [y]:"
  read INPUT
  if [ "$INPUT" == "y" -o -z "$INPUT" ]; then
    [ -n "$SCRIPTDIR" ] && [ -n "$VENV_NAME" ] && rm -rf $SCRIPTDIR/$VENV_NAME
  else
    echo "Setup cancelled. No changes were made."
    exit 1
  fi
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