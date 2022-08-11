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
        # Apt
        if package_check "apt" -v; then
            echo " >> Using: [apt] to install $1"
            apt install "$1" || sudo apt install "$1"
        # Apt-get
        elif package_check "apt-get" -v; then
            echo " >> Using: [apt-get] to install $1"
            apt-get install "$1" || sudo apt-get install "$1"
        # Pacman
        elif package_check "pacman" -v; then
            echo " >> Using: [pacman] to install $1"
            pacman -S "$1" || sudo pacman -S "$1"
        # Yum
        elif package_check "yum" -v; then
            echo " >> Using: [yum] to install $1"
            yum install "$1" || sudo yum install "$1"
        # Apk
        elif package_check "apk" -v; then
            echo " >> Using: [apk] to install $1"
            apk add "$1" || sudo apk add "$1"
        # Zypper
        elif package_check "zypper" -v; then
            echo " >> Using: [zypper] to install $1"
            zypper install "$1" || sudo zypper install "$1"
        else
            echo "ERROR: Unable to install $1. No compatible package manager found!"
            exit 1
        fi
    else
        echo "Using: [pkg] to install $1"
        pkg install "$1" -y 
    fi
}

package_check () {
    if [ "$2" == -v ]; then
        PACK=$(command -v "$1")
    else
        PACK=$(command -v "$1" &> /dev/null)
    fi
    if ! $PACK; then
        echo "INFO: Package $1 not found"
        install_package "$1"   
    fi
}

install_all_packages () {
    echo -e "[+] Checking and installing Required packages... \n"
    package_check 'python3'
    package_check 'ffmpeg'
    if [ "$on_termux" == "True" ]; then
        package_check 'python3-venv'
    fi
}

activate_venv_and_install_pip_packages () {
    echo -e "[+] Activating python virtual environment... \n"
    python3 -m venv $ALTRUIX_VENV || sudo python3 -m venv $ALTRUIX_VENV
    source $ALTRUIX_VENV/bin/activate
    if [ "$on_termux" == "True" ]; then
        pip install wheel && pkg install libjpeg-turbo && LDFLAGS="-L/system/lib/" CFLAGS="-I/data/data/com.termux/files/usr/include/" pip install Pillow
    fi
    echo -e "[+] Installing python dependencies using pip... \n"
    pip3 install --upgrade pip || sudo pip3 install --upgrade pip
    pip3 install -U -r requirements.txt || sudo pip3 install -U -r requirements.txt
}

run_altruix() {
    python3 -m Main || sudo python3 -m Main
}


main () {
    # Install packages
    install_all_packages
    # Activate python venv and instlall pip packages
    activate_venv_and_install_pip_packages
    # Check if config file exists
    if [ -f ".env" ]; then
        run_altruix
    else
        echo -e "ERROR: .env file not found! After creating .env file start the userbot with, \n python3 -m Main"
        exit 1
    fi
}

main
