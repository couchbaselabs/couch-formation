#cloud-config
autoinstall:
  version: 1
  early-commands:
    - sudo systemctl stop ssh
  locale: ${vm_guest_os_language}
  keyboard:
    layout: ${vm_guest_os_keyboard}
  storage:
    layout:
      name: direct
  identity:
    hostname: kubernetes-server
    username: ${build_username}
    password: ${build_password_encrypted}
  ssh:
    install-server: true
    allow-pw: true
    authorized-keys:
      - ${build_key}
  packages:
    - openssh-server
    - open-vm-tools
    - net-tools
  user-data:
    disable_root: false
  late-commands:
    - echo '${build_username} ALL=(ALL) NOPASSWD:ALL' > /target/etc/sudoers.d/${build_username}
    - chmod 440 /target/etc/sudoers.d/${build_username}
    - sed -i "s/.*PermitRootLogin.*/PermitRootLogin yes/g" /target/etc/ssh/sshd_config
  timezone: ${vm_guest_os_timezone}
