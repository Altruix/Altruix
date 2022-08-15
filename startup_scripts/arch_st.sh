#!/bin/bash

_isInstalled() {
    package="$1";
    check="$(sudo pacman -Qs --color always "${package}" | grep "local" | grep "${package} ")";
    if [ -n "${check}" ] ; then
        echo 0; 
        return;
    fi;
    echo 1;
    return
}


_installMany() {
    toInstall=();
    for pkg; do
        if [[ $(_isInstalled "${pkg}") == 0 ]]; then
            echo "${pkg} is already installed.";
            continue;
        fi;
        toInstall+=("${pkg}");
    done;
    if [[ "${toInstall[@]}" == "" ]] ; then
        echo "All packages are already installed.";
        return;
    fi;
    printf "Packages not installed:\n%s\n" "${toInstall[@]}";
    sudo pacman -S "${toInstall[@]}";
}

final_run () {
    _installMany python3 ffmpeg python-pip # install these arch packages.
    python3 -m venv venv
    source venv/bin/activate
    pip3 install --upgrade pip && pip3 install -r requirements.txt
    python3 -m Main
}


final_run