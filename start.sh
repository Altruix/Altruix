#! /usr/bin/bash

# Constants
ALTRUIX_VENV="Altruix"

# Termux check
if [ $(echo $PREFIX | grep -o 'com.termux') ];then
    on_termux=True
else
    on_termux=False  
fi

install_package () {
    if [ "$on_termux" == "False" ]; then
        if package_check "apt"; then
            apt install $1 || sudo apt install $1
        elif package_check "apt-get"; then
            apt-get install $1 || sudo apt-get install $1
        elif package_check "pacman"; then
            pacman -S $1 || sudo pacman -S $1
        elif package_check "yum"; then
            yum install $1 || sudo yum install $1
        elif package_check "apk"; then
            apk add $1 || sudo apk add $1
        elif package_check "zypper"; then
            zypper install $1 || sudo zypper install $1
        else
            echo "Unable to install $1. No compatible package manager found!"
            exit 1
        fi
    else
        echo "Using: [pkg] to install packages"
        pkg install "$1" -y 
fi
}

package_check () {
    PACK=$(command -v "$1" &> /dev/null)
    if ! $PACK;
    then
        echo "Package $1 not found"
    install_package "$1"   
    fi
}

install_all_packages () {
    echo "Checking and installing Required packages...."
    package_check 'python3'
    package_check 'ffmpeg'
    if [ "$on_termux" == "True" ]; then
        package_check 'python3-venv'
    fi
}

activate_venv_and_install_pip_packages () {
    python3 -m venv $ALTRUIX_VENV || sudo python3 -m venv $ALTRUIX_VENV
    source $ALTRUIX_VENV/bin/activate
    if [ "$on_termux" == "True" ]; then
        pip install wheel && pkg install libjpeg-turbo && LDFLAGS="-L/system/lib/" CFLAGS="-I/data/data/com.termux/files/usr/include/" pip install Pillow
    fi
    pip3 install --upgrade pip || sudo pip3 install --upgrade pip
    pip3 install -r -U requirements.txt || sudo pip3 install -r requirements.txt
    python3 -m Main || sudo python3 -m Main
}

run () {
    install_all_packages
    activate_venv_and_install_pip_packages
}

run
