declare -A pm;
pm[/etc/redhat-release]=yum
pm[/etc/arch-release]=pacman
pm[/etc/gentoo-release]=emerge
pm[/etc/SuSE-release]=zypp
pm[/etc/debian_version]=apt-get
pm[/etc/alpine-release]=apk

if [ $(echo $PREFIX | grep -o 'com.termux') ];then
    on_termux=True
else
    on_termux=False  
fi

install_package () {
    if [ "$on_termux" == "False" ]; then
        { for f in ${!pm[@]}  
            do
                if [[ -f $f ]];then
                    echo "Using : [${pm[$f]}] to install packages"
                    sudo ${pm[$f]} install "$1" -y || ${pm[$f]} install "$1" -y
                    fi
            done    }
    else
        echo "Using : [pkg] to install packages"
        pkg install "$1" -y 
fi
}

package_check () {
if [ $(dpkg-query -W -f='${Status}' $1 2>/dev/null | grep -c "ok installed") -eq 0 ];
then
  echo "Package $1 not found. Installing package $1"
  install_package "$1"   
fi
}

install_all_packages () {
    echo "Checking and installing Required packages...."
    package_check 'python3'
    package_check 'ffmpeg'
    if [ "$on_termux" == "False" ]; then
        package_check 'python3-venv'
    fi
}

activate_venv_and_install_pip_packages () {
    sudo python3 -m venv venv || python3 -m venv venv
    source venv/bin/activate
    if [ "$on_termux" == "True" ]; then
        pip install wheel && pkg install libjpeg-turbo && LDFLAGS="-L/system/lib/" CFLAGS="-I/data/data/com.termux/files/usr/include/" pip install Pillow
    fi
    sudo pip3 install --upgrade pip || pip3 install --upgrade pip
    sudo pip3 install -r requirements.txt || pip3 install -r requirements.txt
    sudo python3 -m Main || python3 -m Main
}

run () {
    install_all_packages
    activate_venv_and_install_pip_packages
}

run
