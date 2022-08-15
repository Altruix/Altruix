echo """
 _____ _   _                     
(  _  )_ )( )_            _      
| (_) || ||  _)_ __ _   _(_)     
(  _  )| || | (  __) ) ( ) | \/ )
| | | || || |_| |  | (_) | |)  ( 
(_) (_)___)\__)_)   \___/(_)_/\_)

StartUp Script V1
"""


detected_os () {
if [ $(echo $PREFIX | grep -o 'com.termux') ];then
    file='./startup_scripts/termux_st.sh'
    name='Termux'
elif [ -f /etc/redhat-release ]; then
    file='./startup_scripts/cent_st.sh'
    name='CentOS'
elif [ -f /etc/arch-release ] ; then
    file='./startup_scripts/arch_st.sh'
    name='Arch'
elif [ -f /etc/debian_version ]; then 
    file='./startup_scripts/debain_st.sh'
    name='Debain'
else
    file='./startup_scripts/basic_st.sh'
    name='Basic StartUP'
fi
}

run_scripts () {
    detected_os
    echo "OS [$name] Detected. Running $file script.."
    bash $file
}


run_scripts