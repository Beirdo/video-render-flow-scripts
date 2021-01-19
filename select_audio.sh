AUDIO=${DEFAULTAUDIO}
if [ "$1" == "--webcam" ]; then
    AUDIO="webcam"
    shift 1
elif [ "$1" == "--headset" ]; then
    AUDIO="headset"
    shift 1
elif [ "$1" == "--builtin" ]; then
    AUDIO="builtin"
    shift 1
elif [ "$1" == "--microphone" ]; then
    AUDIO="microphone"
    shift 1
fi

# This microphone in the microscope doesn't seem to do squat
#AUDDEVICE="alsa_input.usb-Etron_Technology__Inc._USB2.0_Camera-02.analog-mono"

case $AUDIO in
    microphone )
        AUDDEVICE="alsa_input.usb-C-Media_Electronics_Inc._USB_Audio_Device-00.analog-mono"
	;;

    webcam )
        AUDDEVICE="alsa_input.usb-046d_HD_Pro_Webcam_C920_4BB47EAF-02.analog-stereo"
	;;

    headset )
        AUDDEVICE="alsa_input.usb-Logitech_Inc_Logitech_USB_Headset_H540_00000000-00.analog-stereo"
	;;

    builtin )
        AUDDEVICE="alsa_input.pci-0000_00_1b.0.analog-stereo"
	;;

    * )
        echo "No audio device!"
	exit 1
	;;
esac

