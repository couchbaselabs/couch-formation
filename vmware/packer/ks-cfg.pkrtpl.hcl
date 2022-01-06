# Install a fresh new system (optional)
text

# Specify installation method to use for installation
# To use a different one comment out the 'url' one below, update
# the selected choice with proper options & un-comment it
cdrom

# Set language to use during installation and the default language to use on the installed system (required)
lang en_US.UTF-8

# Set system keyboard type / layout (required)
keyboard us

# Configure network information for target system and activate network devices in the installer environment (optional)
# --onboot	enable device at a boot time
# --device	device to be activated and / or configured with the network command
# --bootproto	method to obtain networking configuration for device (default dhcp)
# --noipv6	disable IPv6 on this device
# To use static IP configuration,
# network --bootproto=static --ip=10.0.2.15 --netmask=255.255.255.0 --gateway=10.0.2.254 --nameserver 192.168.2.1,192.168.3.1
network --onboot yes --device ens192 --bootproto dhcp --noipv6 --hostname couchbase-server

# Set the system's root password (required)
# Plaintext password is: server
rootpw --iscrypted ${build_password_encrypted}

user --name=${build_username} --groups=wheel --iscrypted --password=${build_password_encrypted}

# Configure firewall settings for the system (optional)
# --enabled	reject incoming connections that are not in response to outbound requests
# --ssh		allow sshd service through the firewall
# firewall --enabled --ssh
firewall --disabled

# Set up the authentication options for the system (required)
# --enableshadow	enable shadowed passwords by default
# --passalgo		hash / crypt algorithm for new passwords
# See the manual page for authconfig for a complete list of possible options.
authselect --kickstart --passalgo=sha512 --usecache --useshadow

# State of SELinux on the installed system (optional)
# Defaults to enforcing
selinux --disabled

# Set the system time zone (required)
timezone --utc ${vm_guest_os_timezone}

# Specify how the bootloader should be installed (required)
# Plaintext password is: password
bootloader --location=mbr --append="rhgb quiet"
autopart --type=lvm
# Initialize all disks

clearpart --linux --initlabel

# Packages selection
%packages
@base
%end
# End of %packages section

%post
sudo yum update -y
sudo yum -y install epel-release open-vm-tools perl python python3-pip openssh-server curl cloud-init git wget sudo
echo '${build_username} ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/${build_username}
chmod 440 /etc/sudoers.d/${build_username}
sed -i "s/.*PermitRootLogin.*/PermitRootLogin yes/g" /etc/ssh/sshd_config
mkdir -m0700 /home/${build_username}/.ssh/
cat <<EOF > /home/${build_username}/.ssh/authorized_keys
${build_key}
EOF
chmod 0600 /home/${build_username}/.ssh/authorized_keys
grub2-mkconfig -o /boot/grub2/grub.cfg
%end

# Reboot after the installation is complete (optional)
# --eject	attempt to eject CD or DVD media before rebooting
reboot --eject
